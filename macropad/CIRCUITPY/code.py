import time

import board
import usb_cdc

from kmk.kmk_keyboard import KMKKeyboard
from kmk.keys import KC, make_key
from kmk.modules.encoder import EncoderHandler
from kmk.scanners import DiodeOrientation

from display_manager import DisplayManager
from rgb_manager import RGBManager

DRAW_INTERVAL_S = 0.05

keyboard = KMKKeyboard()
keyboard.col_pins = (board.GP26, board.GP27, board.GP28)
keyboard.row_pins = (board.GP6, board.GP7)
keyboard.diode_orientation = DiodeOrientation.COL2ROW

encoder_handler = EncoderHandler()
encoder_handler.pins = (
    (board.GP0, board.GP1),  # volume
    (board.GP2, board.GP3),  # scrub
)
keyboard.modules.append(encoder_handler)

serial_data = usb_cdc.data
display = DisplayManager()
rgb = RGBManager(board.GP29, count=16, brightness=0.25)

_last_draw = 0.0
_last_pressed = 0


def _send_command(command):
    try:
        serial_data.write((command + "\n").encode("utf-8"))
    except Exception:
        pass


def _cmd_press(message):
    def _handler(_key, _keyboard, *args, **kwargs):
        _send_command(message)
        display.note_key_activity()

    return _handler


# Custom actions routed to the bridge for Spotify API control.
make_key(names=("SP_PLAY",), on_press=_cmd_press("CMD|PLAY_PAUSE"))
make_key(names=("SP_NEXT",), on_press=_cmd_press("CMD|NEXT"))
make_key(names=("SP_PREV",), on_press=_cmd_press("CMD|PREV"))
make_key(names=("SP_SHUF",), on_press=_cmd_press("CMD|SHUFFLE"))
make_key(names=("SP_REPT",), on_press=_cmd_press("CMD|REPEAT"))
make_key(names=("SP_MUTE",), on_press=_cmd_press("CMD|MUTE"))
make_key(names=("VOL_UP_CMD",), on_press=_cmd_press("CMD|VOL_REL|2"))
make_key(names=("VOL_DN_CMD",), on_press=_cmd_press("CMD|VOL_REL|-2"))
make_key(names=("SEEK_FWD",), on_press=_cmd_press("CMD|SEEK_REL|5"))
make_key(names=("SEEK_BACK",), on_press=_cmd_press("CMD|SEEK_REL|-5"))

keyboard.keymap = [[
    KC.SP_MUTE,
    KC.SP_SHUF,
    KC.SP_REPT,
    KC.SP_PREV,
    KC.SP_PLAY,
    KC.SP_NEXT,
]]

encoder_handler.map = [
    ((KC.VOL_DN_CMD, KC.VOL_UP_CMD),),
    ((KC.SEEK_BACK, KC.SEEK_FWD),),
]


def _safe_read_serial_line():
    if not serial_data.in_waiting:
        return None

    try:
        line = serial_data.readline()
        if not line:
            return None
        return line.decode("utf-8", errors="ignore").strip()
    except Exception:
        return None


def after_matrix_scan(_keyboard):
    global _last_draw, _last_pressed

    msg = _safe_read_serial_line()
    if msg:
        display.handle_message(msg)
        if msg.startswith("SONG|"):
            parts = msg.split("|")
            if len(parts) >= 6:
                try:
                    rgb.set_bpm(int(parts[5]))
                except ValueError:
                    rgb.set_bpm(0)
        elif msg.startswith("IDLE"):
            rgb.set_bpm(0)

    pressed = len(keyboard.keys_pressed)
    if pressed > _last_pressed:
        display.note_key_activity()
    _last_pressed = pressed

    now = time.monotonic()
    if now - _last_draw >= DRAW_INTERVAL_S:
        display.draw()
        rgb.update()
        _last_draw = now


keyboard.after_matrix_scan = after_matrix_scan

if __name__ == "__main__":
    keyboard.go()
