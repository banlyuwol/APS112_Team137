# 🌅 Circadian LED Controller
### SK6812 RGBW + Raspberry Pi 4B · Canadian Sunrise/Sunset Simulation

---

## Overview

This system controls an SK6812 RGBW LED strip to simulate natural sunlight
throughout the day, supporting your circadian rhythm. It calculates local
sunrise, solar noon, and sunset times for any Canadian city, then smoothly
transitions color temperature and brightness across the day.

| Time of day | Color Temp | Effect |
|---|---|---|
| Night | — | LEDs off |
| Dawn / Dusk | ~2700 K | Warm amber glow, dim |
| Morning | ~4000 K | Neutral warm, rising |
| Solar Noon | ~6500 K | Cool daylight, full brightness |

---

## Hardware Wiring

```
Raspberry Pi 4B                SK6812 RGBW Strip
────────────────               ─────────────────
GPIO 18 (Pin 12) ──[ 330Ω ]──▶ DIN
GND              (Pin 6)  ───▶ GND
                               5V power supply (separate!) ──▶ VCC + GND
```

> ⚠️ **IMPORTANT**: Never power the LED strip from the Pi's 5V pin.
> Use a dedicated 5V power supply rated for your strip length.
> (Rule of thumb: 60 LEDs × 60mA each = ~3.6A minimum supply)
>
> Connect the power supply GND to Pi GND (common ground).

### Logic Level Shifting (recommended)
The Pi outputs 3.3V logic; SK6812 prefers 5V logic on DIN.
Use a 74AHCT125 level shifter for reliability over long strips.

---

## File Structure

```
circadian_led/
├── gui_input.py       ← Tkinter GUI (main entry point with display)
├── cli_main.py        ← Headless CLI (use over SSH)
├── sun_calc.py        ← NOAA solar algorithm (offline, no API)
├── led_controller.py  ← SK6812 driver + circadian color math
├── requirements.txt   ← Python dependencies
├── autostart.sh       ← Auto-launch GUI on display connect
└── config.json        ← Saved settings (auto-generated)
```

---

## Installation

### 0. Requirements
- Raspberry Pi 4B with Python 3.9+
- SK6812 (RGBW) LED strip
- Libraries:
```bash
pip install rpi_ws281x adafruit-circuitpython-neopixel
```
- Tkinter (for GUI version):
```
sudo apt install python3-tk
```

### 1. Clone / copy files to Pi
```bash
git clone <repo-url>
cd <repo-folder>
```

### 2. Enable SPI / PWM & configure system
```bash
sudo raspi-config
# → Interface Options → SPI → Enable
# → System Options → Boot / Auto Login → Desktop Autologin

# Fix PWM timing instability:
sudo nano /boot/config.txt
# Add:
#   core_freq=500
#   core_freq_min=500
```

### 3. Install Python dependencies
```bash
sudo apt update
sudo apt install -y python3-pip python3-tk

cd /home/pi/circadian_led
pip3 install -r requirements.txt --break-system-packages
```

### 4. Run (must be root for GPIO PWM access)
```bash
# GUI version (with display)
sudo python3 gui_input.py

# Headless / SSH (CLI)
sudo python3 main.py

# With arguments (CLI)
sudo python3 main.py --date 2025-06-21 --leds 120 --interval 30
```

### 5. Auto-start GUI on boot
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/circadian-led.desktop
```
Paste:
```bash
[Desktop Entry]
Type=Application
Name=Circadian LED
Exec=sudo python3 /home/pi/circadian_led/gui_input.py
StartupNotify=false
```

### 6. Reboot
```bash
sudo reboot
```
---

## How the Circadian Curve Works

The smooth brightness and color curve uses a **cosine interpolation**
anchored to three solar events:

```
Brightness
  1.0 |          ╭──────╮
      |        ╭╯        ╰╮
  0.5 |       ╱            ╲
      |      ╱              ╲
  0.0 |─────╯                ╰──────
      sunrise    noon      sunset
```

Color temperature follows the same curve:
- 2700 K at sunrise/sunset (warm amber, like a candle)
- 6500 K at solar noon (cool, like open sky)

The SK6812's **W (white) channel** is blended in at lower temperatures
to add warmth and CRI quality that RGB alone can't achieve.

---

## Supported Canadian Cities (built-in)

Toronto · Ottawa · Montreal · Vancouver · Calgary · Edmonton
Winnipeg · Halifax · Quebec City · Saskatoon · Regina
St. John's · Victoria · Kelowna · Custom (enter lat/lon)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| LEDs flicker / wrong colors | Check common GND between Pi and PSU |
| Permission denied on GPIO | Run with `sudo` |
| tkinter not found | `sudo apt install python3-tk` |
| Colors look off | Verify `LED_ORDER = neopixel.GRBW` in led_controller.py |
| PWM unstable | Add `core_freq=500` to `/boot/config.txt` |
