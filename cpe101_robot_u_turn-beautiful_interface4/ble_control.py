# ble_control.py
import asyncio
from bleak import BleakClient, BleakScanner, exc as bleak_exc

UART_SERVICE     = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
UART_WRITE_CHAR  = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

class BleState:
    def __init__(self):
        self.client = None
        self.write_uuid = None
        self.ready = False
        self.addr = ""
        self.last_err = ""

async def find_device(timeout=10):
    def filt(d, adv):
        return (d.name or "").lower().startswith("bbc micro")
    dev = await BleakScanner.find_device_by_filter(filt, timeout=timeout)
    return dev

async def ble_worker(state: BleState):
    while True:
        try:
            dev = await find_device(timeout=10)
            if not dev:
                await asyncio.sleep(1); continue
            state.addr = dev.address
            c = BleakClient(dev, timeout=20.0, winrt={"use_cached_services": False})
            await c.connect()
            state.client = c
            state.write_uuid = UART_WRITE_CHAR
            state.ready = True
            print("BLE connected:", dev.address)
            while c.is_connected:
                await asyncio.sleep(0.5)
        except (asyncio.TimeoutError, bleak_exc.BleakError) as e:
            state.last_err = str(e)
        finally:
            if state.client:
                try: await state.client.disconnect()
                except: pass
            state.client = None
            state.ready = False
            await asyncio.sleep(1.5)

async def send_cmd(state: BleState, cmd: str):
    if state.ready and state.client:
        await state.client.write_gatt_char(state.write_uuid, (cmd+"\n").encode("utf-8"))