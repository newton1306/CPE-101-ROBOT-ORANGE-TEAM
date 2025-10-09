// iBIT (INEX) + UART gesture control — Simplified 2-Wheel Turns
// ————————————————————————————————————————————————————————————
bluetooth.startUartService()
basic.showIcon(IconNames.Happy)

// ===== Tunables =====
let BASE_SPEED = 65        // เดินหน้า/ถอย
let SMOOTH_TURN_SPEED = 50 // เลี้ยว smooth (ช้ากว่า)
let SHARP_TURN_SPEED = 18  // เลี้ยวคม ตรงนี้แหละชะงักๆเลย
let MIN_START_DELAY = 800  // ms หลังบูตค่อยยอมสั่งมอเตอร์
let RX_TIMEOUT = 1000      // ms ไม่มีคำสั่ง -> STOP
let CMD_RATE_MS = 80       // เวลาขั้นต่ำระหว่างคำสั่งมอเตอร์

// ===== State =====
let mode = "STOP"
let speedTarget = 0
let lastRx = input.runningTime()
let lastMotorCmd = 0
let lastAppliedMode = ""
let bootAt = input.runningTime()

// ===== Wheel control (2-wheel differential drive) =====
function setWheels(left: number, right: number) {
    left = Math.max(-100, Math.min(100, left))
    right = Math.max(-100, Math.min(100, right))

    if (left == 0 && right == 0) {
        iBIT.MotorStop()
        return
    }

    let lDir = left >= 0 ? ibitMotor.Forward : ibitMotor.Backward
    let rDir = right >= 0 ? ibitMotor.Forward : ibitMotor.Backward
    iBIT.setMotor(ibitMotorCH.M1, lDir, Math.abs(left))
    iBIT.setMotor(ibitMotorCH.M2, rDir, Math.abs(right))
}

// ===== Target setter =====
function setTarget(m: string, spd: number) {
    mode = m
    speedTarget = Math.max(0, Math.min(100, spd))
    lastRx = input.runningTime()
}

// ===== Apply motion =====
function applyMotionIfNeeded() {
    if (input.runningTime() - bootAt < MIN_START_DELAY) {
        iBIT.MotorStop()
        return
    }

    if (input.runningTime() - lastRx > RX_TIMEOUT) {
        mode = "STOP"
        speedTarget = 0
    }

    if (input.runningTime() - lastMotorCmd < CMD_RATE_MS) return

    const stamp = mode + ":" + speedTarget
    if (stamp == lastAppliedMode) return
    lastAppliedMode = stamp

    // Motion mapping
    if (speedTarget <= 0 || mode == "STOP") {
        setWheels(0, 0)
    } else if (mode == "FWD") {
        // เดินหน้า: ทั้งสองล้อหมุนเดินหน้า
        setWheels(speedTarget, speedTarget)
    } else if (mode == "BACK") {
        // ถอยหลัง: ทั้งสองล้อหมุนถอยหลัง
        setWheels(-speedTarget, -speedTarget)
    } else if (mode == "SMOOTH_LEFT") {
        // เลี้ยวซ้ายแบบ smooth: ล้อซ้ายถอยหลัง ล้อขวาเดินหน้า
        setWheels(-speedTarget, speedTarget)
    } else if (mode == "SMOOTH_RIGHT") {
        // เลี้ยวขวาแบบ smooth: ล้อซ้ายเดินหน้า ล้อขวาถอยหลัง
        setWheels(speedTarget, -speedTarget)
    } else if (mode == "SHARP_LEFT") {
        // เลี้ยวซ้ายแบบคม: ล้อซ้ายถอยหลัง ล้อขวาเดินหน้า (เร็วกว่า)
        setWheels(-speedTarget, speedTarget)
    } else if (mode == "SHARP_RIGHT") {
        // เลี้ยวขวาแบบคม: ล้อซ้ายเดินหน้า ล้อขวาถอยหลัง (เร็วกว่า)
        setWheels(speedTarget, -speedTarget)
    } else {
        setWheels(0, 0)
    }
    lastMotorCmd = input.runningTime()
}

// ===== Map UART -> target =====
function driveByCmd(cmd: string) {
    if (cmd == "FWD") setTarget("FWD", BASE_SPEED)
    else if (cmd == "BACK") setTarget("BACK", BASE_SPEED)
    else if (cmd == "SMOOTH_LEFT") setTarget("SMOOTH_LEFT", SMOOTH_TURN_SPEED)
    else if (cmd == "SMOOTH_RIGHT") setTarget("SMOOTH_RIGHT", SMOOTH_TURN_SPEED)
    else if (cmd == "SHARP_LEFT") setTarget("SHARP_LEFT", SHARP_TURN_SPEED)
    else if (cmd == "SHARP_RIGHT") setTarget("SHARP_RIGHT", SHARP_TURN_SPEED)
    else setTarget("STOP", 0)
}

// ===== UART receive =====
bluetooth.onUartDataReceived(serial.delimiters(Delimiters.NewLine), function () {
    const msg = bluetooth.uartReadUntil(serial.delimiters(Delimiters.NewLine))
    if (msg.length >= 4 && msg.indexOf("CMD:") == 0) driveByCmd(msg.substr(4))
})

bluetooth.onBluetoothConnected(function () { basic.showIcon(IconNames.House) })
bluetooth.onBluetoothDisconnected(function () {
    setTarget("STOP", 0)
    setWheels(0, 0)
    basic.showIcon(IconNames.No)
})

// ===== main loop =====
basic.forever(function () {
    applyMotionIfNeeded()
    basic.pause(20)
})