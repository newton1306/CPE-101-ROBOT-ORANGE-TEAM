# hand_servo.py — ตรวจจับมือซ้าย/ขวา + ยืนยันพิเศษฝั่ง LIFT (ลดแกว่ง) xxx
import sys, asyncio, time
import cv2
import mediapipe as mp

from gesture import classify_core, gesture_to_cmd_by_handedness, GestureStabilizer
from skeleton_draw import draw_skeleton
from ble_control import BleState, ble_worker, send_cmd

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# เว้นระยะการส่ง BLE ทีมิน
TX_MIN_GAP_S = 0.8

# ยืนยันท่าสลับยกขึ้น/ลง (ซ้าย): ต้องกดค้างเพิ่มก่อน “เปลี่ยนสถานะ”
LIFT_CONFIRM_MS = 600

def open_camera():
    for i in (0,1,2):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            ok,_ = cap.read()
            if ok: return cap
        if cap: cap.release()
    return None

class ConfirmGate:
    """ยืนยันคำสั่งสลับสถานะ: ต้องค้าง gesture เดิมจนครบเวลายืนยัน"""
    def __init__(self, confirm_ms=600):
        self.confirm_s = confirm_ms/1000.0
        self.pending = None
        self.t0 = 0.0

    def want(self, cmd, current_state, now):
        """
        ถ้า cmd != current_state => เริ่ม/นับยืนยัน
        ถ้า cmd == current_state => เคลียร์เพนดิ้ง
        คืนค่า True เมื่อถือ cmd เดิมครบ confirm_s
        """
        if cmd is None:
            self.pending = None
            return False
        if cmd == current_state:
            self.pending = None
            return False
        # ขอเปลี่ยนสถานะ
        if self.pending != cmd:
            self.pending = cmd
            self.t0 = now
            return False
        # ค้างท่าเดิมนานพอหรือยัง
        return (now - self.t0) >= self.confirm_s

async def main():
    state = BleState()
    asyncio.create_task(ble_worker(state))

    cap = open_camera()
    if not cap:
        print("เปิดกล้องไม่สำเร็จ"); return

    mp_hands = mp.solutions.hands
    # สร้าง stabilizer แยกซ้าย/ขวา
    stab_left  = GestureStabilizer(window_size=7, min_consecutive=4, min_dwell_ms=180, change_cooldown_ms=320)
    stab_right = GestureStabilizer(window_size=7, min_consecutive=4, min_dwell_ms=160, change_cooldown_ms=300)

    # สถานะฝั่ง LIFT เพื่อใช้ confirm gate
    lift_state = None  # 'CMD:LIFT_UP' หรือ 'CMD:LIFT_DOWN'
    lift_gate  = ConfirmGate(confirm_ms=LIFT_CONFIRM_MS)

    last_tx = 0.0
    last_sent = {"L": None, "R": None}

    print("ท่ามือ: ซ้าย OPEN=ยก, PEACE=ลง | ขวา OPEN=กาง, PEACE=หุบ (ESC เพื่อออก)")
    with mp_hands.Hands(model_complexity=0, max_num_hands=2,
                        min_detection_confidence=0.55,
                        min_tracking_confidence=0.55) as hands:
        while True:
            ok, frame = cap.read(); 
            if not ok: break
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = hands.process(rgb)

            # เตรียมผลต่อมือซ้าย/ขวา
            left_cmd = None; right_cmd = None
            left_g = "NONE"; right_g = "NONE"

            if res.multi_hand_landmarks and res.multi_handedness:
                # MediaPipe ใช้ดัชนีเดียวกันสำหรับ landmarks และ handedness
                for i, hland in enumerate(res.multi_hand_landmarks):
                    handed = res.multi_handedness[i].classification[0].label  # 'Left' or 'Right'
                    raw_g  = classify_core(hland.landmark)  # OPEN/PEACE/NONE
                    stable_g = stab_left.update(raw_g) if handed=="Left" else stab_right.update(raw_g)

                    # วาดพร้อมป้าย
                    lbl = f"{handed}:{stable_g}"
                    draw_skeleton(frame, hland, lbl)

                    cmd = gesture_to_cmd_by_handedness(handed, stable_g)
                    if handed == "Left":
                        left_g = stable_g
                        left_cmd = cmd
                    else:
                        right_g = stable_g
                        right_cmd = cmd

            now = time.time()
            can_tx = (now - last_tx) >= TX_MIN_GAP_S

            # ----- ฝั่ง LIFT (มือซ้าย) ใช้ confirm gate -----
            if left_cmd:
                if lift_state is None:
                    # ครั้งแรก: ส่งทันที (ตั้ง state เริ่มต้น)
                    if can_tx:
                        await send_cmd(state, left_cmd)
                        lift_state = left_cmd
                        last_sent["L"] = left_cmd
                        last_tx = time.time()
                else:
                    if left_cmd == lift_state:
                        lift_gate.pending = None  # ไม่มีการเปลี่ยน ไม่ต้องคอนเฟิร์ม
                    else:
                        if lift_gate.want(left_cmd, lift_state, now) and can_tx:
                            await send_cmd(state, left_cmd)
                            lift_state = left_cmd
                            last_sent["L"] = left_cmd
                            last_tx = time.time()

            # ----- ฝั่ง GRIP (มือขวา) ส่งปกติ (พอมี stabilizer แล้ว) -----
            if right_cmd and (right_cmd != last_sent["R"]) and can_tx:
                await send_cmd(state, right_cmd)
                last_sent["R"] = right_cmd
                last_tx = time.time()

            # HUD
            status = "BLE: Ready" if state.ready else f"BLE: Connecting... {state.last_err}"
            if state.addr: status += f" ({state.addr})"
            cv2.putText(frame, status, (10,24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,255), 2)
            cv2.putText(frame, f"L:{left_g} -> {left_cmd or '-'}   |   R:{right_g} -> {right_cmd or '-'}",
                        (10,52), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            cv2.imshow("Servo Gesture Control (Left/Right + Confirm LIFT)", frame)
            if (cv2.waitKey(1) & 0xFF) == 27: break
            await asyncio.sleep(0)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    asyncio.run(main())
