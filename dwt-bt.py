#!/usr/bin/env python3
"""Disable-while-typing for Bluetooth keyboard+touchpad combos.

Finds devices by name (survives reconnects and event number reassignment),
grabs the touchpad for GRAB_MS ms after each keypress, then releases it.
Works on Wayland where syndaemon doesn't.
"""

import asyncio
import logging
import signal
import sys
import evdev
from evdev import InputDevice, ecodes

KEYBOARD_NAME = "Bluetooth Keyboard"
TOUCHPAD_NAME = "Bluetooth Keyboard Touchpad"
GRAB_MS = 200        # ms to suppress touchpad after last keypress
RETRY_DELAY = 5.0    # seconds to wait before retrying after disconnect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dwt-bt")


def find_device(name: str) -> InputDevice | None:
    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
            if dev.name == name:
                return dev
            dev.close()
        except (PermissionError, OSError):
            pass
    return None


async def run_once() -> None:
    """One session: find devices, run until one disconnects."""
    kb = find_device(KEYBOARD_NAME)
    tp = find_device(TOUCHPAD_NAME)

    if kb is None or tp is None:
        missing = KEYBOARD_NAME if kb is None else TOUCHPAD_NAME
        log.warning("Device not found: %r — retrying in %gs", missing, RETRY_DELAY)
        await asyncio.sleep(RETRY_DELAY)
        return

    log.info("Watching %s (%s) → suppressing %s (%s)", kb.name, kb.path, tp.name, tp.path)

    grabbed = False
    release_handle: asyncio.TimerHandle | None = None
    loop = asyncio.get_event_loop()

    def release() -> None:
        nonlocal grabbed, release_handle
        release_handle = None
        if grabbed:
            try:
                tp.ungrab()
                grabbed = False
            except OSError:
                pass

    try:
        async for event in kb.async_read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            if release_handle is not None:
                release_handle.cancel()

            if not grabbed:
                try:
                    tp.grab()
                    grabbed = True
                except OSError:
                    pass

            release_handle = loop.call_later(GRAB_MS / 1000.0, release)

    except OSError as exc:
        log.warning("Device error (%s) — reconnecting in %gs", exc, RETRY_DELAY)
    finally:
        release()
        try:
            kb.close()
        except OSError:
            pass
        try:
            tp.close()
        except OSError:
            pass

    await asyncio.sleep(RETRY_DELAY)


async def main() -> None:
    loop = asyncio.get_event_loop()
    stop = loop.create_future()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set_result, sig)

    while not stop.done():
        await asyncio.wait(
            [asyncio.ensure_future(run_once()), stop],
            return_when=asyncio.FIRST_COMPLETED,
        )

    log.info("Shutting down.")


if __name__ == "__main__":
    asyncio.run(main())
