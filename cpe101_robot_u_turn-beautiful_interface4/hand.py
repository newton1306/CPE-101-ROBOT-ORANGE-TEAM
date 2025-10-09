# hand.py
import sys, asyncio, time
import cv2
import mediapipe as mp
import numpy as np

from gesture import classify_gesture, gesture_to_cmd, GestureStabilizer
from skeleton_draw import draw_skeleton
from ble_control import BleState, ble_worker, send_cmd

# ---- Async policy (Windows) ----
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ---- Tunables ----
SHARP_TURN_DURATION = 0.18     # <<< ลดเวลาหมุนคม (เดิมคุณว่า "นานไป")
RESEND_INTERVAL     = 0.50     # resend สำหรับคำสั่งค้าง (เดิน/ถอย/เลี้ยวค้าง)

# 3 ตัวนี้ Delay เกิ้น ใช้ 3 อันล่างจ่ะ 
"""STAB_WINDOW         = 6
STAB_MIN_CONSEC     = 4
STAB_COOLDOWN_MS    = 600"""

STAB_WINDOW         = 4
STAB_MIN_CONSEC     = 3
STAB_COOLDOWN_MS    = 250


PEACE_SET = {"PEACE_LEFT", "PEACE_RIGHT"}  # ท่าชูสองนิ้ว = trigger sharp (one-shot)

CMD_EMOJI = {
    "CMD:STOP": "⛔",
    "CMD:FWD": "⬆️",
    "CMD:BACK": "⬇️",
    "CMD:SMOOTH_LEFT": "↖️",
    "CMD:SMOOTH_RIGHT": "↗️",
    "CMD:SHARP_LEFT": "⤴️",
    "CMD:SHARP_RIGHT": "⤵️",
}

# ----------------- UI helpers (คงหน้าตาเดิม + เพิ่มบรรทัดข้อมูล) -----------------
def draw_rounded_rectangle(img, pt1, pt2, color, thickness, r):
    x1, y1 = pt1; x2, y2 = pt2
    if thickness < 0:
        cv2.rectangle(img, (x1+r, y1), (x2-r, y2), color, -1)
        cv2.rectangle(img, (x1, y1+r), (x2, y2-r), color, -1)
    else:
        cv2.line(img, (x1+r, y1), (x2-r, y1), color, thickness)
        cv2.line(img, (x1+r, y2), (x2-r, y2), color, thickness)
        cv2.line(img, (x1, y1+r), (x1, y2-r), color, thickness)
        cv2.line(img, (x2, y1+r), (x2, y2-r), color, thickness)
    cv2.ellipse(img, (x1+r, y1+r), (r, r), 180, 0, 90, color, thickness)
    cv2.ellipse(img, (x2-r, y1+r), (r, r), 270, 0, 90, color, thickness)
    cv2.ellipse(img, (x1+r, y2-r), (r, r), 90, 0, 90, color, thickness)
    cv2.ellipse(img, (x2-r, y2-r), (r, r), 0, 0, 90, color, thickness)

def draw_status_panel(frame, state, stable_gesture, last_cmd, sharp_on, fps):
    # กล่องสถานะ “แบบเดิม” + เพิ่ม MAC / FPS / Sharp
    overlay = frame.copy()
    panel_w, panel_h = 360, 180
    cv2.rectangle(overlay, (10, 10), (10 + panel_w, 10 + panel_h), (30, 30, 30), -1)
    draw_rounded_rectangle(frame, (10, 10), (10 + panel_w, 10 + panel_h), (100, 200, 255), 2, 12)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    y = 35
    # BLE
    ble_color = (0, 255, 0) if state.ready else (0, 165, 255)
    ble_text = "🟢 Connected" if state.ready else "🟡 Connecting..."
    cv2.putText(frame, "BLE:", (20, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180,180,180), 1)
    cv2.putText(frame, ble_text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, ble_color, 2)
    y += 28
    # MAC Bluetooth (เพิ่ม)
    mac = state.addr if getattr(state, "addr", "") else "—"
    cv2.putText(frame, f"MAC: {mac}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220,220,220), 1)
    y += 24
    # Gesture
    cv2.putText(frame, f"Gesture: {stable_gesture}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2)
    y += 26
    # Command
    cv2.putText(frame, f"Cmd: {CMD_EMOJI.get(last_cmd,'')} {last_cmd}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 2)
    y += 26
    # Sharp status (เพิ่ม)
    cv2.putText(frame, f"Sharp: {'ON' if sharp_on else 'off'} ({SHARP_TURN_DURATION:.2f}s)", (20, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,255,200) if sharp_on else (200,200,200), 1)
    y += 24
    # FPS (เพิ่ม)
    cv2.putText(frame, f"FPS: {fps:.1f}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,255), 1)

# ----------------- Camera helper -----------------
def open_camera():
    cap = cv2.VideoCapture(0)
    if cap and cap.isOpened():
        return cap
    return cv2.VideoCapture(0, cv2.CAP_DSHOW)

# ----------------- Sharp-turn (non-blocking) -----------------
async def execute_sharp_turn(state, cmd, duration):
    try:
        await send_cmd(state, cmd)
        await asyncio.sleep(duration)
    finally:
        await send_cmd(state, "CMD:STOP")

# ----------------- Main -----------------
async def main():
    state = BleState()
    asyncio.create_task(ble_worker(state))

    cap = open_camera()
    if not (cap and cap.isOpened()):
        print("❌ Cannot open camera")
        return

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                           min_detection_confidence=0.6, min_tracking_confidence=0.6, model_complexity=1)

    stabilizer = GestureStabilizer(
        window_size=STAB_WINDOW,
        min_consecutive=STAB_MIN_CONSEC,
        change_cooldown_ms=STAB_COOLDOWN_MS
    )

    prev_stable = "NONE"
    last_cmd = "CMD:STOP"
    last_send_time = 0.0

    # Sharp one-shot state
    sharp_turn_in_progress = False
    sharp_turn_end = 0.0
    sharp_lock = False  # ต้องปล่อยสองนิ้วก่อนยิงรอบใหม่

    # FPS meter
    t0 = time.time()
    fps = 0.0
    frame_count = 0

    print("="*60)
    print("🤖 Robot Control — gestures:")
    print("🖐️  OPEN         → FWD")
    print("✊  FIST         → STOP")
    print("👍  THUMB        → BACK")
    print("☝️  ONE-FINGER   → Smooth Turn (ตามมือ)")
    print("✌️  TWO-FINGERS  → Sharp Turn (one-shot)")
    print("ESC to exit.")
    print("="*60)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                await asyncio.sleep(0)
                continue

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)

            stable_gesture = "NONE"
            if res.multi_hand_landmarks and res.multi_handedness:
                hls = res.multi_hand_landmarks[0]
                label = res.multi_handedness[0].classification[0].label
                draw_skeleton(frame, hls)
                # สร้าง lm แบบ minimal ที่ classify_gesture ใช้งานได้ (x,y)
                lm = [type("P", (), {"x":p.x, "y":p.y}) for p in hls.landmark]
                g = classify_gesture(lm, hand_label=label)
                stable_gesture = stabilizer.update(g)
            else:
                stable_gesture = stabilizer.update("NONE")

            cmd = gesture_to_cmd(stable_gesture)
            now = time.time()

            # ปลดล็อกเมื่อไม่ได้ชูสองนิ้ว
            if stable_gesture not in PEACE_SET:
                sharp_lock = False

            # จับ edge: non-PEACE -> PEACE
            is_edge_to_peace = (stable_gesture in PEACE_SET) and (prev_stable not in PEACE_SET)

            # อัปเดตสถานะ sharp
            if sharp_turn_in_progress and now >= sharp_turn_end:
                sharp_turn_in_progress = False  # STOP จะถูกส่งใน execute_sharp_turn()

            # เริ่ม sharp one-shot
            if is_edge_to_peace and (not sharp_lock) and (not sharp_turn_in_progress):
                sharp_lock = True
                sharp_turn_in_progress = True
                sharp_turn_end = now + SHARP_TURN_DURATION
                sharp_cmd = "CMD:SHARP_LEFT" if stable_gesture == "PEACE_LEFT" else "CMD:SHARP_RIGHT"
                asyncio.create_task(execute_sharp_turn(state, sharp_cmd, SHARP_TURN_DURATION))
                last_cmd = sharp_cmd
                last_send_time = now

            # คำสั่งค้างอื่น ๆ ทำงานเมื่อไม่อยู่ในช่วง sharp
            if not sharp_turn_in_progress:
                if cmd != last_cmd:
                    await send_cmd(state, cmd)
                    last_cmd = cmd
                    last_send_time = now
                else:
                    if cmd in ("CMD:FWD", "CMD:BACK", "CMD:SMOOTH_LEFT", "CMD:SMOOTH_RIGHT"):
                        if (now - last_send_time) > RESEND_INTERVAL:
                            await send_cmd(state, cmd)
                            last_send_time = now

            # ===== UI (คงหน้าต่างเดิม + เพิ่มข้อมูล) =====
            frame_count += 1
            if frame_count % 10 == 0:
                t1 = time.time()
                fps = 10.0 / max(1e-6, (t1 - t0))
                t0 = t1

            draw_status_panel(frame, state, stable_gesture, last_cmd, sharp_turn_in_progress, fps)

            cv2.imshow("Robot Control", frame)  # ชื่อเดิม
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                print("\n👋 Exiting... Goodbye!")
                break

            prev_stable = stable_gesture
            await asyncio.sleep(0)  # ปล่อย event loop

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())
