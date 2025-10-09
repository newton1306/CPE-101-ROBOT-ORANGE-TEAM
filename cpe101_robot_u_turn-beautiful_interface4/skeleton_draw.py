# skeleton_draw.py
import cv2
import mediapipe as mp

mp_drawing = mp.solutions.drawing_utils
mp_style = mp.solutions.drawing_styles

def draw_skeleton(frame, hand_landmarks):
    mp_drawing.draw_landmarks(
        frame,
        hand_landmarks,
        mp.solutions.hands.HAND_CONNECTIONS,
        mp_style.get_default_hand_landmarks_style(),
        mp_style.get_default_hand_connections_style(),
    )