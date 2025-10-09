// iBIT: SV1 = ยกแขน (มุม), SV2 = คีบ (มุม) — zero คีบ = 90°, เปิด = 180°
bluetooth.startUartService()
basic.showIcon(IconNames.Happy)

// === ช่องเซอร์โว ===
const LIFT_SERVO = ibitServo.SV1
const GRIP_SERVO = ibitServo.SV2

// === ขอบเขตมุม ===
const S_MIN = 0
const S_MAX = 180

// === ยกแขน (SV1) ===
// 0° = ชี้ขวาสุด (ตำแหน่งหมุดมาร์ก), 45° = ยกขึ้น (ทวนเข็ม)
let LIFT_DOWN_ANGLE = 0
let LIFT_UP_ANGLE = 45

// === คีบ (SV2) ===
let GRIP_ZERO_ANGLE = 90    // หุบ (ศูนย์)
let GRIP_OPEN_ANGLE = 145   // กาง

// --- สถานะ/เป้าหมาย ---
let s1Target = LIFT_DOWN_ANGLE
let s1Applied = -1
let pendS1 = true

let s2Target = GRIP_ZERO_ANGLE
let s2Applied = -1
let pendS2 = true

// === Timing (กันสั่งถี่ I2C) ===
const MIN_I2C_GAP_MS = 120
const I2C_SETTLE_MS = 120
let lastI2C = input.runningTime()
let nextAt = input.runningTime()

function now() { return input.runningTime() }
function canI2C() { return now() >= nextAt && (now() - lastI2C) >= MIN_I2C_GAP_MS }
function plan(dt: number) { nextAt = now() + dt }
function clamp(v: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, v)) }

function setServo(ch: ibitServo, angle: number) {
    if (!canI2C()) return false
    iBIT.Servo(ch, clamp(angle, S_MIN, S_MAX))
    lastI2C = now()
    plan(Math.max(MIN_I2C_GAP_MS, I2C_SETTLE_MS))
    return true
}

// === Apply ตามเป้าหมาย (ยิงคำสั่งครั้งเดียวเมื่อถึงคิว) ===
function applyS1(angle: number) {
    if (!setServo(LIFT_SERVO, angle)) { pendS1 = true; return }
    s1Applied = angle
    pendS1 = false
}
function applyS2(angle: number) {
    if (!setServo(GRIP_SERVO, angle)) { pendS2 = true; return }
    s2Applied = angle
    pendS2 = false
}

// === คำสั่งระดับสูง ===
function liftDown() { s1Target = LIFT_DOWN_ANGLE; pendS1 = true }
function liftUp() { s1Target = LIFT_UP_ANGLE; pendS1 = true }

function gripClose() { s2Target = GRIP_ZERO_ANGLE; pendS2 = true } // หุบ = 90°
function gripOpen() { s2Target = GRIP_OPEN_ANGLE; pendS2 = true } // เปิด = 180°

// === โฮมตอนบูต/ต่อบลูทูธ ===
function startupHome() {
    s1Target = LIFT_DOWN_ANGLE; s1Applied = -1; pendS1 = true
    s2Target = GRIP_ZERO_ANGLE; s2Applied = -1; pendS2 = true
    applyS1(s1Target); basic.pause(120); applyS1(s1Target)
    applyS2(s2Target); basic.pause(120); applyS2(s2Target)
}

// === BLE UART ===
bluetooth.onUartDataReceived(serial.delimiters(Delimiters.NewLine), function () {
    const msg = bluetooth.uartReadUntil(serial.delimiters(Delimiters.NewLine))

    // คำสั่งยกแขน
    if (msg == "CMD:LIFT_DOWN") { liftDown(); return }
    if (msg == "CMD:LIFT_UP") { liftUp(); return }

    // คำสั่งคีบ
    if (msg == "CMD:GRIP_CLOSE") { gripClose(); return }
    if (msg == "CMD:GRIP_OPEN") { gripOpen(); return }

    // ตั้งมุมตรง (ทดสอบ/ปรับจูน)
    if (msg.indexOf("S1:") == 0) {
        const a = clamp(parseInt(msg.substr(3)), S_MIN, S_MAX)
        s1Target = a; pendS1 = true; return
    }
    if (msg.indexOf("S2:") == 0) {
        const a = clamp(parseInt(msg.substr(3)), S_MIN, S_MAX)
        s2Target = a; pendS2 = true; return
    }

    // Calibration:
    //   CAL:GRIP_ZERO:<angle>   (ค่า "หุบ")
    //   CAL:GRIP_OPEN:<angle>   (ค่า "กาง")
    //   CAL:LIFT_UP:<angle>, CAL:LIFT_DOWN:<angle>
    if (msg.indexOf("CAL:") == 0) {
        const p = msg.split(":")
        if (p.length == 3) {
            const key = p[1]; const val = clamp(parseInt(p[2]), S_MIN, S_MAX)
            if (key == "GRIP_ZERO") { GRIP_ZERO_ANGLE = val; if (!pendS2 && s2Target == s2Applied) { s2Target = val; pendS2 = true } }
            else if (key == "GRIP_OPEN") { GRIP_OPEN_ANGLE = val }
            else if (key == "LIFT_UP") { LIFT_UP_ANGLE = val; if (!pendS1 && s1Target == s1Applied) { s1Target = val; pendS1 = true } }
            else if (key == "LIFT_DOWN") { LIFT_DOWN_ANGLE = val; if (!pendS1 && s1Target == s1Applied) { s1Target = val; pendS1 = true } }
        }
        return
    }
})

bluetooth.onBluetoothConnected(function () {
    basic.showIcon(IconNames.House)
    startupHome()
})
bluetooth.onBluetoothDisconnected(function () {
    basic.showIcon(IconNames.No)
})

// บูตครั้งแรก
startupHome()

// === Main loop ===
basic.forever(function () {
    if (pendS1 && s1Target != s1Applied) { applyS1(s1Target); basic.pause(5); return }
    if (pendS2 && s2Target != s2Applied) { applyS2(s2Target); basic.pause(5); return }
    basic.pause(5)
})
