"""Build Windows EXEs for the bridge and OLED test app with PyInstaller.

Usage:
  python build_exe.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def run(cmd):
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=ROOT)


def build(script_name, exe_name):
    run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onefile",
            "--noconsole",
            "--name",
            exe_name,
            script_name,
        ]
    )


def main():
    build("spotify_bridge.py", "spotify_bridge")
    build("oled_test_app.py", "oled_test_app")
    print("\nBuild complete.")
    print(f"Bridge EXE: {DIST / 'spotify_bridge.exe'}")
    print(f"OLED Test EXE: {DIST / 'oled_test_app.exe'}")
    print(f"Build temp dir: {BUILD}")


if __name__ == "__main__":
    main()
