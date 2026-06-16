# dwt-bt

Disable-while-typing for Bluetooth keyboard and touchpad combos on Linux.

When typing, accidental touches on the touchpad are suppressed. The touchpad
is re-enabled a short time after the last keypress (default 200ms).

## Background

Linux's built-in disable-while-typing (DWT) support in libinput only applies
to internal laptop touchpads. External and Bluetooth devices are excluded, so
a Bluetooth keyboard with an integrated touchpad gets no protection against
accidental touches while typing. This daemon fills that gap.

It works on **Wayland** (where the traditional `syndaemon` tool does not).

### Tested on

- Surface Pro with an aftermarket Bluetooth keyboard and trackpad
- Fedora 43, GNOME, Wayland

## Requirements

- Python 3.10+
- `python3-evdev` (`sudo dnf install python3-evdev` on Fedora)

## Installation

1. **Copy the script** to somewhere on your PATH:

   ```
   cp dwt-bt.py ~/.local/bin/dwt-bt.py
   chmod +x ~/.local/bin/dwt-bt.py
   ```

2. **Find your device names:**

   ```
   libinput list-devices | grep -i "bluetooth\|keyboard\|touchpad"
   ```

   Edit `dwt-bt.py` and update `KEYBOARD_NAME` and `TOUCHPAD_NAME` to match
   your device names exactly.

3. **Install the systemd user service:**

   ```
   cp dwt-bt.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now dwt-bt.service
   ```

4. **Check it is running:**

   ```
   systemctl --user status dwt-bt.service
   ```

## Configuration

Edit `dwt-bt.py`:

| Variable | Default | Description |
|---|---|---|
| `KEYBOARD_NAME` | `"Bluetooth Keyboard"` | Exact name of keyboard device |
| `TOUCHPAD_NAME` | `"Bluetooth Keyboard Touchpad"` | Exact name of touchpad device |
| `GRAB_MS` | `200` | Milliseconds to suppress touchpad after last keypress |
| `RETRY_DELAY` | `5.0` | Seconds to wait before retrying after a disconnect |

After editing, restart the service:

```
systemctl --user restart dwt-bt.service
```

## How it works

The script monitors keyboard events via `evdev`. On the first keypress of a
typing burst it calls `grab()` on the touchpad device, giving it exclusive
ownership and silently dropping all touchpad events. `GRAB_MS` milliseconds
after the last keypress it releases the grab. Device names are matched by
name rather than event number, so the service survives Bluetooth reconnects
without needing to be restarted.

## Logs

```
journalctl --user -u dwt-bt.service -f
```
