# gesture.py
import time
import numpy as np

def finger_open(lm, tip, pip):
    return lm[tip].y < lm[pip].y

def classify_gesture(lm, hand_label="Right"):
    """
    hand_label = "Left" หรือ "Right" จาก MediaPipe
    - "Left" = มือซ้ายในชีวิตจริง (แต่ในกล้องเป็นขวา เพราะ mirror)
    - "Right" = มือขวาในชีวิตจริง (แต่ในกล้องเป็นซ้าย เพราะ mirror)
    """
    idx = finger_open(lm, 8, 6)
    mid = finger_open(lm,12,10)
    ring= finger_open(lm,16,14)
    pink= finger_open(lm,20,18)
    
    # ปรับการตรวจจับ thumb ตาม hand_label
    if hand_label == "Right":  # มือขวาในชีวิตจริง (ในกล้องดูเป็นซ้าย)
        thumb = (lm[4].x < lm[2].x - 0.03)  # โป้งอยู่ซ้าย
    else:  # มือซ้ายในชีวิตจริง (ในกล้องดูเป็นขวา)
        thumb = (lm[4].x > lm[2].x + 0.03)  # โป้งอยู่ขวา
    
    opens = sum([thumb, idx, mid, ring, pink])
    
    # ชูนิ้วกลางเพียงนิ้วเดียว = เลี้ยวแบบ smooth ค้าง
    if not thumb and not idx and mid and not ring and not pink:
        if hand_label == "Right":  # มือขวา -> เลี้ยวขวา
            return "MIDDLE_RIGHT"
        else:  # มือซ้าย -> เลี้ยวซ้าย
            return "MIDDLE_LEFT"
    
    # ชูสองนิ้ว (นิ้วชี้+นิ้วกลาง) = เลี้ยวสั้นและคม
    if not thumb and idx and mid and not ring and not pink:
        if hand_label == "Right":  # มือขวา -> เลี้ยวขวาแบบคม
            return "PEACE_RIGHT"
        else:  # มือซ้าย -> เลี้ยวซ้ายแบบคม
            return "PEACE_LEFT"
    
    if opens >= 4: return "OPEN"
    if opens == 0: return "FIST"
    
    # ปรับ THUMB gesture ตาม hand_label
    if hand_label == "Right":
        thumb_only = (lm[4].x < lm[2].x - 0.03) and not idx and not mid and not ring and not pink
    else:
        thumb_only = (lm[4].x > lm[2].x + 0.03) and not idx and not mid and not ring and not pink
    
    if thumb_only: return "THUMB"
    return "NONE"

def gesture_to_cmd(g):
    return {
        "OPEN":"CMD:FWD",
        "FIST":"CMD:STOP",
        "THUMB":"CMD:BACK",
        "MIDDLE_LEFT":"CMD:SMOOTH_LEFT",
        "MIDDLE_RIGHT":"CMD:SMOOTH_RIGHT",
        "PEACE_LEFT":"CMD:SHARP_LEFT",
        "PEACE_RIGHT":"CMD:SHARP_RIGHT"
    }.get(g,"CMD:STOP")


class GestureStabilizer:
    """กรอง gesture ให้เปลี่ยนเมื่อ gesture เดิมนิ่งพอ"""
    def __init__(self, window_size=5, min_consecutive=3, min_dwell_ms=100, change_cooldown_ms=150):
        self.window = []
        self.window_size = window_size
        self.min_consecutive = min_consecutive
        self.min_dwell_ms = min_dwell_ms
        self.change_cooldown_ms = change_cooldown_ms
        self.last_stable = "NONE"
        self.last_change_time = 0
        self.last_seen_time = 0

    def update(self, gesture):
        now = time.time()*1000
        self.window.append(gesture)
        if len(self.window) > self.window_size:
            self.window.pop(0)
        if self.window.count(self.window[-1]) >= self.min_consecutive:
            candidate = self.window[-1]
            if candidate != self.last_stable:
                if (now - self.last_change_time) > self.change_cooldown_ms:
                    self.last_stable = candidate
                    self.last_change_time = now
        return self.last_stable