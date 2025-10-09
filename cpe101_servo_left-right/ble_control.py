# ble_control.py — BLE UART ไป micro:bit
import asyncio
from bleak import BleakClient, BleakScanner, exc as bleak_exc

UART_WRITE_CHAR = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
NAME_PREFIX = "bbc micro"

class BleState:
    def __init__(self):
        self.client=None; self.ready=False; self.addr=""; self.last_err=""

async def _find(timeout=10):
    def filt(d, adv): return (d.name or "").lower().startswith(NAME_PREFIX)
    dev = await BleakScanner.find_device_by_filter(filt, timeout=timeout)
    if dev: return dev
    for d in await BleakScanner.discover(timeout=timeout):
        if (d.name or "").lower().startswith(NAME_PREFIX): return d
    return None

async def ble_worker(state: BleState):
    while True:
        try:
            dev = await _find(10)
            if not dev: state.last_err="not-found"; await asyncio.sleep(1.2); continue
            c = BleakClient(dev, timeout=25.0, winrt={"use_cached_services": False})
            await c.connect()
            state.client=c; state.addr=dev.address; state.ready=True; state.last_err="ready"
            while c.is_connected: await asyncio.sleep(0.5)
        except (asyncio.TimeoutError, bleak_exc.BleakError) as e:
            state.last_err=f"{type(e).__name__}: {e}"
        finally:
            if state.client:
                try: await state.client.disconnect()
                except: pass
            state.client=None; state.ready=False
            await asyncio.sleep(1.2)

async def send_cmd(state: BleState, cmd: str)->bool:
    if state.ready and state.client and cmd:
        try:
            await state.client.write_gatt_char(UART_WRITE_CHAR, (cmd+"\n").encode("utf-8"))
            return True
        except Exception as e:
            state.last_err=f"write-fail: {e}"; state.ready=False
    return False
