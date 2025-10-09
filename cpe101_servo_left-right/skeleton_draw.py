# skeleton_draw.py — วาดมือ + ป้าย L/R เหนือข้อมือ
import mediapipe as mp
import cv2

mp_drawing = mp.solutions.drawing_utils
mp_style   = mp.solutions.drawing_styles

def draw_skeleton(frame, hand_landmarks, label_text=None):
    mp_drawing.draw_landmarks(
        frame, hand_landmarks,
        mp.solutions.hands.HAND_CONNECTIONS,
        mp_style.get_default_hand_landmarks_style(),
        mp_style.get_default_hand_connections_style(),
    )
    if label_text:
        h, w = frame.shape[:2]
        wrist = hand_landmarks.landmark[0]
        x = int(wrist.x * w)
        y = int(wrist.y * h) - 12
        cv2.putText(frame, label_text, (x, max(16, y)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
