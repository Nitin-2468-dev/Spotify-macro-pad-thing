import json
import time
from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import serial
import serial.tools.list_ports
import spotipy
from PIL import Image
from spotipy.oauth2 import SpotifyOAuth

CONFIG_PATH = Path(__file__).with_name("config.json")
BAUD_RATE = 115200
POLL_INTERVAL_S = 0.35
RECONNECT_DELAY_S = 2.0


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_spotify_client(config):
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=config["CLIENT_ID"],
            client_secret=config["CLIENT_SECRET"],
            redirect_uri=config["REDIRECT_URI"],
            scope=" ".join(
                [
                    "user-read-playback-state",
                    "user-modify-playback-state",
                ]
            ),
        )
    )


def find_port():
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        return None

    preferred = ("XIAO", "RP2040", "CircuitPython", "USB")
    for p in ports:
        desc = (p.description or "").upper()
        if any(token in desc for token in preferred):
            return p.device

    return ports[0].device


def open_serial_with_retry():
    while True:
        port = find_port()
        if port:
            try:
                print(f"Connecting to serial port: {port}")
                return serial.Serial(port, BAUD_RATE, timeout=0.02)
            except Exception as exc:
                print(f"Serial connect failed: {exc}")
        else:
            print("No serial port found. Retrying...")
        time.sleep(RECONNECT_DELAY_S)


def build_cover_hex(url):
    if not url:
        return None

    with urlopen(url, timeout=10) as resp:
        image_bytes = resp.read()

    img = Image.open(BytesIO(image_bytes)).convert("L").resize((32, 32))

    # 1-bit threshold
    bw = img.point(lambda p: 255 if p > 127 else 0, mode="1")

    pixels = bw.load()
    packed = bytearray(128)
    for page in range(4):
        for x in range(32):
            value = 0
            for bit in range(8):
                y = page * 8 + bit
                if pixels[x, y] == 255:
                    value |= 1 << bit
            packed[page * 32 + x] = value

    return packed.hex()


def safe_write(ser, text):
    ser.write((text + "\n").encode("utf-8"))


def handle_command(sp, playback, cmd_line):
    parts = cmd_line.strip().split("|")
    if len(parts) < 2 or parts[0] != "CMD":
        return

    action = parts[1]

    if action == "NEXT":
        sp.next_track()
    elif action == "PREV":
        sp.previous_track()
    elif action == "PLAY_PAUSE":
        is_playing = bool(playback and playback.get("is_playing"))
        if is_playing:
            sp.pause_playback()
        else:
            sp.start_playback()
    elif action == "SHUFFLE":
        current = bool(playback and playback.get("shuffle_state"))
        sp.shuffle(not current)
    elif action == "REPEAT":
        order = ["off", "context", "track"]
        cur = (playback or {}).get("repeat_state", "off")
        next_mode = order[(order.index(cur) + 1) % len(order)] if cur in order else "off"
        sp.repeat(next_mode)
    elif action == "MUTE":
        sp.volume(0)
    elif action == "VOL_REL" and len(parts) >= 3:
        delta = int(parts[2])
        current = int((playback or {}).get("device", {}).get("volume_percent", 0))
        sp.volume(max(0, min(100, current + delta)))
    elif action == "SEEK_REL" and len(parts) >= 3:
        delta_sec = int(parts[2])
        progress = int((playback or {}).get("progress_ms", 0))
        duration = int((playback or {}).get("item", {}).get("duration_ms", 0))
        target = max(0, min(duration, progress + delta_sec * 1000))
        sp.seek_track(target)


def poll_commands(sp, ser, playback):
    # Drain all queued commands each cycle.
    while ser.in_waiting:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            try:
                handle_command(sp, playback, line)
            except Exception as exc:
                print(f"Command error [{line}]: {exc}")


def read_tempo(sp, track_id):
    if not track_id:
        return 0
    try:
        features = sp.audio_features([track_id])
        if features and features[0] and features[0].get("tempo"):
            return int(round(features[0]["tempo"]))
    except Exception as exc:
        print(f"Tempo lookup failed: {exc}")
    return 0


def send_playback_state(sp, ser, cache):
    playback = sp.current_playback()
    poll_commands(sp, ser, playback)

    if playback and playback.get("item"):
        track = playback["item"]
        song = (track.get("name") or "").replace("|", "/")
        artists = track.get("artists") or []
        artist_name = (artists[0].get("name") if artists else "") or ""
        artist_name = artist_name.replace("|", "/")
        position = int((playback.get("progress_ms") or 0) / 1000)
        duration = int((track.get("duration_ms") or 0) / 1000)
        track_id = track.get("id") or ""

        if track_id and track_id != cache["track_id"]:
            cache["track_id"] = track_id
            cache["tempo"] = read_tempo(sp, track_id)
            images = track.get("album", {}).get("images", [])
            image_url = images[-1]["url"] if images else None
            try:
                cache["cover"] = build_cover_hex(image_url) if image_url else None
            except Exception as exc:
                print(f"Cover conversion failed: {exc}")
                cache["cover"] = None

        bpm = cache["tempo"]
        safe_write(ser, f"SONG|{song}|{artist_name}|{position}|{duration}|{bpm}")
        if cache["cover"]:
            safe_write(ser, f"COVER|{cache['cover']}")
    else:
        safe_write(ser, "IDLE")


def main():
    config = load_config()
    sp = build_spotify_client(config)
    ser = open_serial_with_retry()
    cache = {"track_id": "", "tempo": 0, "cover": None}

    while True:
        try:
            if not ser.is_open:
                ser = open_serial_with_retry()
            send_playback_state(sp, ser, cache)
            time.sleep(POLL_INTERVAL_S)
        except KeyboardInterrupt:
            print("Stopping bridge")
            break
        except Exception as exc:
            print(f"Bridge loop error: {exc}")
            try:
                ser.close()
            except Exception:
                pass
            time.sleep(RECONNECT_DELAY_S)
            ser = open_serial_with_retry()


if __name__ == "__main__":
    main()
