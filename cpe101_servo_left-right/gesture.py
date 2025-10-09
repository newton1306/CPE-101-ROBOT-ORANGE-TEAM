# gesture.py — จำแนกท่ามือ + stabilizer (รองรับ OPEN/PEACE และ Handedness)
import time
from collections import deque, Counter

def _finger_up(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def classify_core(lm):
    """
    คืนค่า: 'OPEN' | 'PEACE' | 'NONE'
    OPEN  = นิ้วกาง >= 4
    PEACE = ชี้+กลางกาง (ring/pinky พับ)
    """
    idx  = _finger_up(lm, 8, 6)
    mid  = _finger_up(lm,12,10)
    ring = _finger_up(lm,16,14)
    pink = _finger_up(lm,20,18)

    opens = sum([idx, mid, ring, pink])
    if opens >= 4:
        return "OPEN"
    if idx and mid and (not ring) and (not pink):
        return "PEACE"
    return "NONE"

def gesture_to_cmd_by_handedness(handed, gesture):
    """
    mapping ตามที่ผู้ใช้ต้องการ:
    - LEFT hand:  OPEN -> LIFT_UP,  PEACE -> LIFT_DOWN
    - RIGHT hand: OPEN -> GRIP_OPEN, PEACE -> GRIP_CLOSE
    """
    if gesture == "NONE" or handed not in ("Left","Right"):
        return None
    if handed == "Left":
        return {"OPEN":"CMD:LIFT_UP", "PEACE":"CMD:LIFT_DOWN"}.get(gesture)
    else:  # Right
        return {"OPEN":"CMD:GRIP_OPEN", "PEACE":"CMD:GRIP_CLOSE"}.get(gesture)

class GestureStabilizer:
    """ต้องเห็นซ้ำ/ค้างก่อนยอมเปลี่ยน + คูลดาวน์"""
    def __init__(self, window_size=7, min_consecutive=4, min_dwell_ms=160, change_cooldown_ms=300):
        self.W = window_size
        self.K = min_consecutive
        self.dwell = min_dwell_ms/1000.0
        self.cool  = change_cooldown_ms/1000.0
        self.buf = deque(maxlen=self.W)
        self.cand = None
        self.cand_t = 0.0
        self.stable = "NONE"
        self.stable_t = 0.0

    def update(self, raw):
        now = time.time()
        self.buf.append((raw, now))
        if (now - self.stable_t) < self.cool:
            return self.stable

        # consecutive
        run = 1
        consec_ok = False
        for i in range(len(self.buf)-2, -1, -1):
            if self.buf[i][0] == raw:
                run += 1
                if run >= self.K:
                    consec_ok = True
                    break
            else:
                break

        if not consec_ok and self.buf:
            counts = Counter([g for g,_ in self.buf])
            maj, cnt = counts.most_common(1)[0]
            if maj == raw and cnt >= max(self.K, int(self.W*0.6)):
                consec_ok = True

        if consec_ok:
            if self.cand != raw:
                self.cand, self.cand_t = raw, now
            if (now - self.cand_t) >= self.dwell:
                self.stable, self.stable_t = self.cand, now
        return self.stable
