"""
led_controller.py
-----------------
Circadian rhythm LED controller for SK6812 RGBW LEDs on Raspberry Pi 4B.
Handles smooth color/temperature transitions via rpi_ws281x / neopixel.
"""

import math
import time
import board
import neopixel

# ──────────────────────────────────────────────
# HARDWARE CONFIG — adjust to your wiring
# ──────────────────────────────────────────────
LED_PIN        = board.D18   # GPIO18 (PWM0) — connect SK6812 DIN here
LED_COUNT      = 60          # Number of LEDs in your strip
LED_BRIGHTNESS = 0.5         # GLOBAL MAX BRIGHTNESS (0.0–1.0)
LED_ORDER      = neopixel.GRBW  # SK6812 GRBW byte order

pixels = neopixel.NeoPixel(
    LED_PIN, LED_COUNT,
    brightness=LED_BRIGHTNESS,
    auto_write=False,
    pixel_order=LED_ORDER
)


# ──────────────────────────────────────────────
# COLOR TEMPERATURE → RGB CONVERSION
# ──────────────────────────────────────────────
def kelvin_to_rgb(kelvin: float) -> tuple[int, int, int]:
    temp = max(1000, min(12000, kelvin)) / 100.0

    # Red
    if temp <= 66:
        r = 255
    else:
        r = 329.698727446 * ((temp - 60) ** -0.1332047592)
        r = max(0, min(255, r))

    # Green
    if temp <= 66:
        g = 99.4708025861 * math.log(temp) - 161.1195681661
    else:
        g = 288.1221695283 * ((temp - 60) ** -0.0755148492)
    g = max(0, min(255, g))

    # Blue
    if temp >= 66:
        b = 255
    elif temp <= 19:
        b = 0
    else:
        b = 138.5177312231 * math.log(temp - 10) - 305.0447927307
        b = max(0, min(255, b))

    return int(r), int(g), int(b)


# ──────────────────────────────────────────────
# SMOOTH CURVE — maps time-of-day → LED params
# ──────────────────────────────────────────────
def smooth_factor(t: float, t_rise: float, t_noon: float, t_set: float) -> float:
    if t < t_rise or t > t_set:
        return 0.0
    if t <= t_noon:
        span = t_noon - t_rise
        if span == 0:
            return 1.0
        phase = (t - t_rise) / span
        return (1 - math.cos(math.pi * phase)) / 2
    else:
        span = t_set - t_noon
        if span == 0:
            return 1.0
        phase = (t - t_noon) / span
        return (1 + math.cos(math.pi * phase)) / 2


MAX_BRIGHTNESS = 0.2  # global cap for 142 LEDs (0.0 - 1.0)

def circadian_params(factor: float) -> dict:
    """
    Map smooth factor (0–1) to Kelvin, brightness, and warm-white channel.
    Scales brightness for long LED strips.
    """
    if factor < 0.01:
        return {"kelvin": 1800, "brightness": 0.0, "white": 0}

    # Kelvin: 2700 K at edges → 6500 K at noon
    kelvin = 2700 + (6500 - 2700) * (factor ** 0.7)

    # Brightness: scaled down for long LED strips
    brightness = (factor ** 0.5) * MAX_BRIGHTNESS

    # White channel: blend in warm white at dawn/dusk
    white_blend = max(0.0, 1.0 - factor * 1.5)
    white = int(white_blend * 180 * brightness)  # cap at ~180 * scaled brightness

    return {"kelvin": kelvin, "brightness": brightness, "white": white}


# ──────────────────────────────────────────────
# APPLY TO STRIP (instant)
# ──────────────────────────────────────────────
def apply_to_leds(params: dict) -> None:
    r, g, b = kelvin_to_rgb(params["kelvin"])
    br = params["brightness"]
    w = params["white"]

    r = int(r * br)
    g = int(g * br)
    b = int(b * br)

    pixels.fill((r, g, b, w))
    pixels.show()


# ──────────────────────────────────────────────
# APPLY SMOOTH TRANSITION
# ──────────────────────────────────────────────
def transition_to(params: dict, steps: int = 20, delay: float = 0.05) -> None:
    """Smoothly transition from current LED state to target params."""
    r_target, g_target, b_target = kelvin_to_rgb(params["kelvin"])
    br_target = params["brightness"]
    w_target = params["white"]

    # Read current pixels
    try:
        r_cur, g_cur, b_cur, w_cur = pixels[0]
    except Exception:
        r_cur = g_cur = b_cur = w_cur = 0

    for step in range(1, steps + 1):
        factor = step / steps
        r = int(r_cur + (r_target * br_target - r_cur) * factor)
        g = int(g_cur + (g_target * br_target - g_cur) * factor)
        b = int(b_cur + (b_target * br_target - b_cur) * factor)
        w = int(w_cur + (w_target - w_cur) * factor)
        pixels.fill((r, g, b, w))
        pixels.show()
        time.sleep(delay)


# ──────────────────────────────────────────────
# TURN OFF LIGHTS
# ──────────────────────────────────────────────
def leds_off() -> None:
    pixels.fill((0, 0, 0, 0))
    pixels.show()


# ──────────────────────────────────────────────
# MAIN LOOP (smooth updates)
# ──────────────────────────────────────────────
def run_loop(sun_times: dict, poll_interval: float = 30.0, verbose: bool = True) -> None:
    if verbose:
        print("[LED] Controller running. Press Ctrl+C to stop.")

    try:
        while True:
            now = time.localtime()
            t = (now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec) / 86400.0

            factor = smooth_factor(
                t,
                sun_times["sunrise_frac"],
                sun_times["noon_frac"],
                sun_times["sunset_frac"],
            )
            params = circadian_params(factor)
            transition_to(params, steps=20, delay=poll_interval / 20)

            if verbose:
                print(
                    f"[LED] {now.tm_hour:02d}:{now.tm_min:02d}  "
                    f"factor={factor:.3f}  "
                    f"K={params['kelvin']:.0f}  "
                    f"br={params['brightness']:.2f}  "
                    f"W={params['white']}"
                )

    except KeyboardInterrupt:
        if verbose:
            print("\n[LED] Shutting down — LEDs off.")
        leds_off()
