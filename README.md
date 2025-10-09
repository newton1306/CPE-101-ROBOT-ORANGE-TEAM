# Robot Control — Movement vs Servo (Separated)
_Last updated: 2025-10-09 16:18_

This README clearly **separates Movement (wheels)** and **Servo (arm/gripper)** pipelines. It is derived from your current files:

- **PC (Movement):** `/mnt/data/cpe101_robot_u_turn-beautiful_interface4/hand.py`
- **PC (Servo):** `/mnt/data/cpe101_servo_left-right/hand_servo.py`
- **micro:bit firmware (Movement):** `/mnt/data/cpe101_robot_u_turn-beautiful_interface4/makecode.js`
- **micro:bit firmware (Servo):** `/mnt/data/cpe101_servo_left-right/servo_control.js`

> **Note**: Movement and Servo run as **two independent pipelines**. Flash the matching micro:bit firmware for the pipeline you run on PC.

---

## 1) Environment Setup (common)

```bash
# go to your project dir
cd ..........................

# venv
python -m venv venv
.env\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# packages
pip install --upgrade pip
pip install opencv-python mediapipe==0.10.14 bleak
```

---

## 2) Movement Control (Wheels)

**PC script:** `hand.py`  
**micro:bit firmware:** `makecode.js` (from `cpe101_robot_u_turn-beautiful_interface4`)

### What it does
- Detects gestures and sends **wheel commands** over BLE.
- **Continuous motions:** `CMD:FWD`, `CMD:BACK`, `CMD:SMOOTH_LEFT`, `CMD:SMOOTH_RIGHT`, `CMD:STOP`  
- **Sharp motion (one-shot on PC; continuous on current firmware):** `CMD:SHARP_LEFT`, `CMD:SHARP_RIGHT`

### Firmware mapping (movement)
- Differential drive via iBIT M1/M2.
- Tunables seen in firmware: `BASE_SPEED=65`, `SMOOTH_TURN_SPEED=50`, `SHARP_TURN_SPEED=18`, etc.
- Motor write rate is guarded (`CMD_RATE_MS` etc.).

> If you want **ultra-short sharp turns**, use the **pulse+brake** firmware variant we drafted earlier; the current uploaded `makecode.js` treats SHARP like a slower continuous turn.

### Run (movement)
```bash
python hand.py
```
- UI shows: BLE status + MAC, Gesture, Command, Sharp status, FPS.


---

## 3) Servo Control (Arm + Gripper)

**PC script:** `hand_servo.py`  
**micro:bit firmware:** `servo_control.js` (from `cpe101_servo_left-right`)

### Channels / Ranges
- **SV1 (LIFT_SERVO):** shoulder lift angle (°). Default: `LIFT_DOWN_ANGLE=0` (arm rightmost), `LIFT_UP_ANGLE=45` (arm up).
- **SV2 (GRIP_SERVO):** gripper angle (°). Default: `GRIP_ZERO_ANGLE=90` (close), `GRIP_OPEN_ANGLE=145` (open).
- Valid range: `0–180°` (clamped). I2C-write gap guards are present: `MIN_I2C_GAP_MS=120`, plus settle gaps.

### PC gesture mapping (handedness-sensitive)
From `gesture.py (servo project)`:
- **Left hand:**
  - `OPEN` → `CMD:LIFT_UP`
  - `PEACE` → `CMD:LIFT_DOWN`
- **Right hand:**
  - `OPEN` → `CMD:GRIP_OPEN`
  - `PEACE` → `CMD:GRIP_CLOSE`

`hand_servo.py` adds **confirmation for LIFT side** (left): you must hold a new state briefly to switch (reduces flapping). BLE transmit gap is `TX_MIN_GAP_S≈0.8` to avoid spam.

### Firmware commands (servo)
- High-level:
  - `CMD:LIFT_UP`, `CMD:LIFT_DOWN`
  - `CMD:GRIP_OPEN`, `CMD:GRIP_CLOSE`
- Direct angle set (fast tuning):
  - `S1:<angle>` → set SV1 to exact angle (0–180)
  - `S2:<angle>` → set SV2 to exact angle (0–180)
- Calibration (persists only during runtime unless you extend it):
  - `CAL:GRIP_ZERO:<angle>`
  - `CAL:GRIP_OPEN:<angle>`
  - `CAL:LIFT_UP:<angle>`
  - `CAL:LIFT_DOWN:<angle>`

The firmware enforces I2C spacing and processes pending targets in the main loop with small pauses (5 ms) to stay stable.

### Run (servo)
```bash
python hand_servo.py
```
- UI title: “Servo Gesture Control (Left/Right + Confirm LIFT)”
- Status line shows BLE/MAC and the **left/right** gesture→command mapping live.


---

## 4) Flashing micro:bit Firmware

1. Go to <https://makecode.microbit.org/>
2. Import the corresponding `makecode.js` (movement) **or** `servo_control.js` (servo).
3. Download `.hex` and drag to the micro:bit drive.
4. After boot, the home icon appears when BLE is ready.


---

## 5) Troubleshooting

- **I2C error 020 (movement):** use firmware with I2C guards (`I2C_GUARD_MS`, pair-gap), soft-start ramp for SMOOTH, and a settle window after SHARP before accepting SMOOTH.
- **Servo jitter:** raise `MIN_I2C_GAP_MS` to 150–200 ms; use `S1:`/`S2:` to confirm mechanical bounds; adjust `LIFT_*`/`GRIP_*` angles to match your horn installation.
- **Gesture delay:** in PC scripts, reduce stabilizer parameters (window/consecutive/cooldown); set MediaPipe `model_complexity=0`.
- **Sharp too long:** switch to pulse+brake movement firmware; adjusting only PC duration won’t help if firmware treats SHARP as continuous.
- **BLE not connecting:** pair micro:bit in OS first; ensure only one app holds the BLE characteristic.


---

## 6) BLE Command Reference

### Movement (to movement firmware)
```
CMD:FWD
CMD:BACK
CMD:SMOOTH_LEFT
CMD:SMOOTH_RIGHT
CMD:SHARP_LEFT
CMD:SHARP_RIGHT
CMD:STOP
```

### Servo (to servo firmware)
```
CMD:LIFT_UP
CMD:LIFT_DOWN
CMD:GRIP_OPEN
CMD:GRIP_CLOSE
S1:<0-180>
S2:<0-180>
CAL:GRIP_ZERO:<0-180>
CAL:GRIP_OPEN:<0-180>
CAL:LIFT_UP:<0-180>
CAL:LIFT_DOWN:<0-180>
```

---

## 7) Notes on Camera & Performance
- Set camera to 640×480 if needed for faster inference:
  ```python
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
  ```
- Keep room lighting consistent to stabilize detection.

---

**Owner:** Newton  
**Contact:** (fill in)  
