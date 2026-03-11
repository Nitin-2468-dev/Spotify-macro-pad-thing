# Spotify Macropad with OLED Display

A custom **Spotify control macropad** built using the **Seeed XIAO RP2040**, running **KMK firmware** and powered by a **Python bridge application** that connects Spotify playback data to the keyboard over USB.

The device acts as a **hardware Spotify controller + display**, showing live song information, album art, and animations on a small OLED screen.

---

## Project Goals

This project aims to create a **dedicated hardware controller for Spotify** with the following capabilities:

- Control music playback
- Display currently playing song
- Show playback progress
- Adjust volume
- Scrub through the track
- Display album art
- Animate a BongoCat reacting to music
- Run a lightweight PC companion app

The final result behaves similarly to a **mini StreamDeck specifically for Spotify**.

---

## System Architecture

```text
Spotify App
      ↓
Spotify Web API
      ↓
spotify_bridge.exe (Python)
      ↓
USB Serial
      ↓
KMK Firmware
      ↓
Macropad Hardware
      ↓
OLED Display + Controls
```

The bridge software connects Spotify playback data to the keyboard firmware through a serial protocol.

---

## Hardware Components

### Main controller

- **Seeed XIAO RP2040**

### Input devices

- 6 × MX-style mechanical switches
- 2 × EC11 rotary encoders

### Display

- **0.91" SSD1306 OLED display (128×32)**

### Lighting

- **16 × SK6812 MINI-E RGB LEDs**

### Other components

- 20 × 1N4148 diodes
- Blank DSA keycaps
- Screws and heat-set inserts

---

## Firmware

Firmware is written using **KMK (Keyboard Module Kit)**.

KMK is a Python-based keyboard firmware built on **CircuitPython**.

### Why KMK was chosen

- Python-based development
- Rapid iteration
- Easy display integration
- Native RP2040 support

### Firmware responsibilities

- Scan key matrix
- Handle rotary encoders
- Communicate with PC bridge via USB serial
- Render OLED display UI
- Play animations

---

## PC Bridge Software

The PC companion application:

```text
spotify_bridge.py
```

or compiled version:

```text
spotify_bridge.exe
```

### Responsibilities

- Connect to Spotify Web API
- Authenticate user
- Retrieve playback data
- Send updates to keyboard
- Receive control commands
- Execute Spotify API actions

The bridge can be packaged as a standalone executable so users **do not need Python installed**.

---

## Spotify Integration

Spotify integration uses the **Spotify Web API**.

Authentication uses OAuth.

### Required permission

```text
user-read-playback-state
```

This allows the bridge to read:

- currently playing track
- artist
- playback progress
- duration
- album art
- tempo (BPM)

Some features require **Spotify Premium**.

---

## Serial Protocol

Communication between the keyboard and bridge uses a simple text protocol.

Examples:

```text
SONG|title|artist|position|duration|tempo
VOL|70
IDLE
COVER|bitmap_data
CMD|NEXT
CMD|PLAY
CMD|SEEK|120
```

This protocol allows **two-way communication**.

---

## OLED Display UI

The 128×32 OLED shows several screens.

### Spotify screen

```text
Spotify
Blinding Lights
████░░░░░░ 1:42
```

Displays:

- song title
- playback progress bar
- current playback time

### Volume screen

```text
Volume
██████░░░░ 60%
```

Appears when adjusting volume.

### Idle screen

```text
BongoCat animation
```

Displayed when nothing is playing.

---

## BongoCat Animation

The OLED displays an animated **BongoCat**.

States:

- Idle breathing animation
- Typing animation when keys are pressed
- Music-synchronized animation when Spotify is playing

The animation reacts to song tempo using the track's BPM.

---

## Album Art Rendering

The bridge downloads album art from Spotify. The image is:

1. Downloaded
2. Resized to 32×32 pixels
3. Converted to monochrome
4. Sent to the keyboard as a bitmap

The OLED displays the album cover next to the song information.

---

## Macropad Controls

### Keys

| Key        | Action          |
| ---------- | --------------- |
| Play/Pause | Toggle playback |
| Next       | Next track      |
| Previous   | Previous track  |
| Shuffle    | Toggle shuffle  |
| Repeat     | Toggle repeat   |
| Mute       | Set volume to 0 |

### Encoder 1

Controls **Spotify volume**

```text
Rotate right → volume up
Rotate left → volume down
```

### Encoder 2

Controls **track scrubbing**

```text
Rotate right → seek forward
Rotate left → seek backward
```

---

## Display Progress Bar

Playback progress is rendered as a 10-segment bar.

Example:

```text
████░░░░░░
```

Progress is calculated using:

```text
progress = position / duration
```

---

## Features

### Core features

- Spotify playback display
- Playback progress bar
- Hardware volume control
- Track scrubbing
- Shuffle toggle
- Repeat toggle

### UI features

- OLED interface
- Scrolling song titles
- Album art display
- BongoCat animations

### System features

- Two-way serial protocol
- PC companion application
- Standalone executable bridge
- Automatic Spotify authentication
- Token caching
- Auto reconnect USB

---

## Why This Design

This architecture was chosen because KMK firmware provides flexible keyboard development while Python allows quick UI development and API integration.

The bridge software separates Spotify integration from firmware, making the keyboard firmware lightweight and reusable.

The result is a **modular system** where:

- firmware handles hardware
- bridge handles network/API logic

---

## Future Improvements

Potential upgrades:

- animated audio visualizer
- RGB LEDs reacting to music
- system tray bridge application
- device auto-detection
- multi-service support (YouTube Music, Apple Music)
- better OLED UI layouts

---

## Project Status

Current stage:

- Software architecture completed
- Firmware and bridge logic implemented
- Waiting for hardware components to assemble the physical macropad
