import time

import board
import busio
import adafruit_ssd1306

from cat_animation import (
    BASE_FRAME_DURATION,
    IDLE_SPEED,
    TAP_SPEED,
    idle_frames,
    prep_frames,
    tap_frames,
)


class DisplayManager:
    TITLE_WINDOW = 12

    def __init__(self):
        i2c = busio.I2C(board.SCL, board.SDA)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

        self.song = ""
        self.artist = ""
        self.position = 0
        self.duration = 0
        self.bpm = 0

        self.mode = "cat"
        self.last_frame_time = 0.0
        self.last_scroll_time = 0.0
        self.frame_index = 0
        self.scroll_index = 0

        self.key_activity_until = 0.0
        self.cover_bitmap = None

    def handle_message(self, msg):
        parts = msg.split("|")
        if not parts:
            return

        if parts[0] == "SONG" and len(parts) >= 6:
            self.song = parts[1]
            self.artist = parts[2]
            self.position = self._safe_int(parts[3])
            self.duration = self._safe_int(parts[4])
            self.bpm = self._safe_int(parts[5])
            self.mode = "spotify"

        elif parts[0] == "COVER" and len(parts) >= 2:
            self.cover_bitmap = self._decode_cover(parts[1])

        elif parts[0] == "IDLE":
            self.mode = "cat"

    def note_key_activity(self):
        self.key_activity_until = time.monotonic() + 0.35

    def draw(self):
        if self.mode == "spotify":
            self.draw_spotify()
        else:
            self.draw_cat()

    def draw_spotify(self):
        self.display.fill(0)

        progress = 0.0
        if self.duration > 0:
            progress = self.position / self.duration
        progress = max(0.0, min(progress, 1.0))

        bars = int(progress * 10)
        bar = "█" * bars + "░" * (10 - bars)

        left_x = 0
        width_chars = self.TITLE_WINDOW

        if self.cover_bitmap:
            self._blit_cover(self.cover_bitmap, 96, 0)
            width_chars = 15

        self.display.text("Spotify", left_x, 0, 1)
        self.display.text(self._scroll_text(self.song, width_chars), left_x, 11, 1)

        time_label = self._fmt(self.position)
        self.display.text(time_label, left_x, 23, 1)
        self.display.text(bar, left_x + 34, 23, 1)

        self.display.show()

    def draw_cat(self):
        now = time.monotonic()
        frame_duration = self._frame_duration()
        if now - self.last_frame_time < frame_duration:
            return

        frame = self._get_cat_frame(now)
        buf = self.display.buffer
        buf[: len(buf)] = frame[: len(buf)]
        self.display.show()

        self.frame_index += 1
        self.last_frame_time = now

    def _frame_duration(self):
        if self.bpm > 0:
            beat = 60.0 / self.bpm
            return max(0.08, min(0.30, beat / 2.0))
        return BASE_FRAME_DURATION

    def _get_cat_frame(self, now):
        if now < self.key_activity_until:
            return tap_frames[self.frame_index % len(tap_frames)]

        if self.bpm >= TAP_SPEED:
            return tap_frames[self.frame_index % len(tap_frames)]

        if self.bpm > IDLE_SPEED:
            return prep_frames[self.frame_index % len(prep_frames)]

        return idle_frames[self.frame_index % len(idle_frames)]

    def _scroll_text(self, text, width):
        text = text or ""
        if len(text) <= width:
            return text

        now = time.monotonic()
        if now - self.last_scroll_time > 0.25:
            self.scroll_index = (self.scroll_index + 1) % (len(text) + 3)
            self.last_scroll_time = now

        padded = text + "   " + text
        start = self.scroll_index
        end = start + width
        return padded[start:end]

    def _decode_cover(self, hex_data):
        try:
            raw = bytes.fromhex(hex_data)
        except ValueError:
            return None

        if len(raw) != 128:
            return None

        return raw

    def _blit_cover(self, bitmap, x, y):
        # Expect 32x32 image in SSD1306 page format (32 * 32 / 8 = 128 bytes).
        buf = self.display.buffer
        if not buf or len(buf) < 512:
            return

        for page in range(4):
            src_off = page * 32
            dst_off = (page + y // 8) * 128 + x
            buf[dst_off : dst_off + 32] = bitmap[src_off : src_off + 32]

    @staticmethod
    def _safe_int(value):
        try:
            return int(value)
        except ValueError:
            return 0

    @staticmethod
    def _fmt(total_seconds):
        total_seconds = max(0, int(total_seconds))
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
