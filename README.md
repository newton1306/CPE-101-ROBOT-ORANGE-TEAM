# 🦾 Robot Gesture Control — Setup & Run Guide

## 📁 Directory Structure
```
project/
│
├─ venv/                  ← virtual environment (will be created)
├─ hand_servo.py          ← main Python control script
├─ gesture.py             ← gesture classification logic (MediaPipe)
├─ ble_control.py         ← BLE comms with micro:bit
├─ skeleton_draw.py       ← drawing utils for visualization
├─ makecode.js            ← micro:bit firmware (MakeCode)
└─ README.md
```

---

## 🧰 1. Create and Activate Virtual Environment

```bash
# Change to your project directory
cd ..........................
```

```bash
# Create venv
python -m venv venv
```

```bash
# Activate venv (Windows)
.env\Scriptsctivate
```

> **Tip:** macOS/Linux:
> ```bash
> source venv/bin/activate
> ```

---

## 📦 2. Install Required Packages

```bash
pip install --upgrade pip
pip install opencv-python mediapipe==0.10.14 bleak
```

- **opencv-python** → เปิดกล้อง  
- **mediapipe 0.10.14** → ตรวจจับท่ามือ (รองรับโค้ด gesture.py)  
- **bleak** → ติดต่อ Bluetooth กับ micro:bit ผ่าน BLE

---

## 🧠 3. Flash micro:bit Firmware

1. เข้า [MakeCode](https://makecode.microbit.org/)  
2. อัปโหลดไฟล์ `makecode.js`  
3. กด **Download** แล้วลาก `.hex` ลง micro:bit  
4. หลังบูต ไอคอนบ้าน 🏠 จะขึ้นเมื่อ BLE พร้อมเชื่อมต่อ

---

## 🖥️ 4. Run Control Program

```bash
python hand_servo.py
```

- กล้องจะเปิดขึ้น พร้อม UI แสดง BLE, MAC, Gesture, Command, Sharp, FPS
- คำสั่งท่ามือจะถูกส่งไป micro:bit แบบเรียลไทม์

---

## 🧪 5. ทดสอบระบบ

1. เปิดโปรแกรม `hand_servo.py`  
2. ทำท่ามือต่าง ๆ → ดู UI เปลี่ยน gesture/command  
3. หุ่นยนต์ตอบสนองทันที (เดิน, เลี้ยว, หยุด)

---

## 📝 Troubleshooting

| ปัญหา                       | วิธีแก้                                                       |
|-----------------------------|----------------------------------------------------------------|
| กล้องไม่เปิด               | ตรวจสอบว่าไม่มีโปรแกรมอื่นใช้กล้อง / driver พร้อม             |
| BLE ไม่เชื่อมต่อ            | Pair micro:bit กับ Windows ก่อนเปิดโปรแกรม                   |
| ขึ้น error 020 (I2C)       | ใช้ makecode.js รุ่นล่าสุด (มี I2C guard + soft-start)       |
| Sharp หมุนเกิน             | ปรับ `SHARP_PULSE_MS` และ `BRAKE_MS` ใน makecode.js          |
| Gesture delay เยอะ          | ปรับ STAB_WINDOW / MIN_CONSEC / COOLDOWN ใน hand.py          |

---

## 🧭 Extra

- ปรับ responsiveness → `gesture.py` / stabilizer ใน `hand.py`  
- ปรับ sharp behavior → `makecode.js` (pulse+brake)  
- เพิ่ม gesture ใหม่ → เขียนใน `gesture.py` แล้วแม็ปใน `gesture_to_cmd`

---

✅ **พร้อมใช้งาน** — ทำตามนี้ทีละขั้น คุณจะควบคุมหุ่นยนต์ด้วยมือได้ทันที
