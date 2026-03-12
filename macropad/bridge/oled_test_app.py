"""Desktop OLED simulator for the macropad serial protocol.

Usage:
  python oled_test_app.py --demo
  python oled_test_app.py --port COM7
"""

import argparse
import threading
import time
import tkinter as tk

try:
    import serial
except ImportError:
    serial = None


SCALE = 4
OLED_W = 128
OLED_H = 32


class OLEDState:
    def __init__(self):
        self.song = ""
        self.artist = ""
        self.position = 0
        self.duration = 0
        self.bpm = 0
        self.mode = "IDLE"
        self.cover = None

    def apply(self, msg):
        parts = msg.strip().split("|")
        if not parts:
            return

        if parts[0] == "SONG" and len(parts) >= 6:
            self.song = parts[1]
            self.artist = parts[2]
            self.position = _safe_int(parts[3])
            self.duration = max(0, _safe_int(parts[4]))
            self.bpm = max(0, _safe_int(parts[5]))
            self.mode = "SPOTIFY"
        elif parts[0] == "COVER" and len(parts) >= 2:
            raw = _decode_cover(parts[1])
            if raw is not None:
                self.cover = raw
        elif parts[0] == "IDLE":
            self.mode = "IDLE"


def _safe_int(v):
    try:
        return int(v)
    except ValueError:
        return 0


def _decode_cover(hex_data):
    try:
        raw = bytes.fromhex(hex_data)
    except ValueError:
        return None
    return raw if len(raw) == 128 else None


def _fmt_time(total):
    m = total // 60
    s = total % 60
    return f"{m}:{s:02d}"


class OLEDTestUI:
    def __init__(self, state):
        self.state = state

        self.root = tk.Tk()
        self.root.title("Spotify Macropad OLED Test")
        self.root.configure(bg="#1e1e1e")

        self.canvas = tk.Canvas(
            self.root,
            width=OLED_W * SCALE,
            height=OLED_H * SCALE,
            bg="black",
            highlightthickness=1,
            highlightbackground="#404040",
        )
        self.canvas.pack(padx=16, pady=16)

        self.status = tk.StringVar(value="Ready")
        tk.Label(self.root, textvariable=self.status, bg="#1e1e1e", fg="#d0d0d0").pack(pady=(0, 12))

        self.scroll = 0
        self.root.after(60, self._tick)

    def run(self):
        self.root.mainloop()

    def _tick(self):
        self.draw()
        self.root.after(60, self._tick)

    def draw(self):
        self.canvas.delete("all")

        if self.state.mode == "SPOTIFY":
            self._draw_spotify()
            self.status.set(f"Mode: Spotify | BPM: {self.state.bpm}")
        else:
            self._draw_idle()
            self.status.set("Mode: Idle")

    def _draw_idle(self):
        phase = int(time.monotonic() * 3) % 2
        eye = 2 if phase == 0 else 1
        self._text(3, 1, "BongoCat idle")
        self._pixel_block(18, 14, 3, eye)
        self._pixel_block(32, 14, 3, eye)
        self._pixel_block(8, 22, 24, 3)

    def _draw_spotify(self):
        if self.state.cover:
            self._draw_cover(96, 0, self.state.cover)
            title_w = 14
        else:
            title_w = 20

        self._text(0, 0, "Spotify")
        self._text(0, 10, self._scroll_text(self.state.song or "Nothing playing", title_w))

        progress = 0.0
        if self.state.duration > 0:
            progress = max(0.0, min(self.state.position / self.state.duration, 1.0))
        bars = int(progress * 10)
        bar = "█" * bars + "░" * (10 - bars)

        self._text(0, 22, _fmt_time(self.state.position))
        self._text(38, 22, bar)

    def _draw_cover(self, ox, oy, raw):
        for page in range(4):
            for x in range(32):
                v = raw[page * 32 + x]
                for bit in range(8):
                    if v & (1 << bit):
                        self._pixel(ox + x, oy + page * 8 + bit)

    def _scroll_text(self, text, width):
        if len(text) <= width:
            return text
        if int(time.monotonic() * 4) != self.scroll:
            self.scroll = int(time.monotonic() * 4)
        idx = self.scroll % (len(text) + 3)
        return (text + "   " + text)[idx : idx + width]

    def _text(self, x, y, s):
        self.canvas.create_text(
            x * SCALE,
            y * SCALE,
            anchor="nw",
            text=s,
            fill="#ffffff",
            font=("Courier", 7 * SCALE // 2),
        )

    def _pixel(self, x, y):
        self.canvas.create_rectangle(
            x * SCALE,
            y * SCALE,
            x * SCALE + SCALE,
            y * SCALE + SCALE,
            outline="",
            fill="#f0f0f0",
        )

    def _pixel_block(self, x, y, w, h):
        self.canvas.create_rectangle(
            x * SCALE,
            y * SCALE,
            (x + w) * SCALE,
            (y + h) * SCALE,
            outline="",
            fill="#f0f0f0",
        )


def demo_feed(state):
    samples = [
        ("Blinding Lights", "The Weeknd", 200),
        ("As It Was", "Harry Styles", 168),
        ("Stairway to Heaven", "Led Zeppelin", 482),
    ]
    i = 0
    pos = 0
    while True:
        song, artist, dur = samples[i % len(samples)]
        bpm = 90 + (i % 3) * 24
        state.apply(f"SONG|{song}|{artist}|{pos}|{dur}|{bpm}")
        pos += 1
        if pos > dur:
            pos = 0
            i += 1
            if i % 2 == 1:
                state.apply("IDLE")
                time.sleep(1.5)
        time.sleep(0.35)


def serial_feed(state, port, baud):
    if serial is None:
        raise RuntimeError("pyserial is required for --port mode")

    with serial.Serial(port, baud, timeout=0.1) as ser:
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                state.apply(line)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Run with generated fake Spotify messages")
    parser.add_argument("--port", help="Read OLED protocol messages from a serial port")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    state = OLEDState()

    if args.demo:
        t = threading.Thread(target=demo_feed, args=(state,), daemon=True)
        t.start()
    elif args.port:
        t = threading.Thread(target=serial_feed, args=(state, args.port, args.baud), daemon=True)
        t.start()
    else:
        parser.error("Use either --demo or --port")

    OLEDTestUI(state).run()


if __name__ == "__main__":
    main()
