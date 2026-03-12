import time

try:
    import neopixel
except ImportError:  # Running where neopixel is unavailable.
    neopixel = None


class RGBManager:
    def __init__(self, pin, count=16, brightness=0.2):
        self._pixels = None
        self._last = 0.0
        self._phase = 0.0
        self._bpm = 0

        if neopixel is not None:
            try:
                self._pixels = neopixel.NeoPixel(pin, count, brightness=brightness, auto_write=False)
                self._pixels.fill((0, 0, 0))
                self._pixels.show()
            except Exception:
                self._pixels = None

    def set_bpm(self, bpm):
        self._bpm = max(0, int(bpm))

    def update(self):
        if self._pixels is None:
            return

        now = time.monotonic()
        if now - self._last < 0.03:
            return
        self._last = now

        if self._bpm <= 0:
            self._pixels.fill((0, 0, 0))
            self._pixels.show()
            return

        pulse = (self._bpm / 180.0)
        pulse = max(0.1, min(pulse, 1.0))
        self._phase += pulse * 0.45
        phase = self._phase % 2.0
        if phase > 1.0:
            phase = 2.0 - phase

        level = int(phase * 40)
        color = (level // 4, level, level // 2)
        self._pixels.fill(color)
        self._pixels.show()
