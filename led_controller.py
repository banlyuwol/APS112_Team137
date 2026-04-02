"""
led_controller.py
-----------------
Circadian rhythm LED controller for SK6812 RGBW LEDs on Raspberry Pi 4B.
Handles color/temperature calculation and LED signal output via rpi_ws281x.
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
LED_BRIGHTNESS = 1.0         # 0.0–1.0 global brightness cap
LED_ORDER      = neopixel.GRBW  # SK6812 GRBW byte order

pixels = neopixel.NeoPixel(
    LED_PIN, LED_COUNT,
    brightness=LED_BRIGHTNESS,
    auto_write=False,
    pixel_order=LED_ORDER
)

def init_pixels():
    """Re-initialize the NeoPixel object (useful if LED_COUNT changes)."""
    global pixels
    pixels = neopixel.NeoPixel(
        LED_PIN, LED_COUNT,
        brightness=LED_BRIGHTNESS,
        auto_write=False,
        pixel_order=LED_ORDER
    )


# ──────────────────────────────────────────────
# COLOR TEMPERATURE → RGB CONVERSION
# Approximation of Planckian locus (Tanner–Fairchild)
# Input : color temperature in Kelvin (1000 K – 12000 K)
# Output: (r, g, b) each 0–255
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
# Uses a piecewise cosine curve anchored to
# sunrise, solar noon, and sunset.
# ──────────────────────────────────────────────
def smooth_factor(
    t: float,           # current time as fraction of day (0.0–1.0)
    t_rise: float,      # sunrise fraction
    t_noon: float,      # solar noon fraction
    t_set: float,       # sunset fraction
) -> float:
    """
    Returns 0.0 (night) → 1.0 (full daylight) using cosine blending.
    """
    if t < t_rise or t > t_set:
        return 0.0
    if t <= t_noon:
        # morning ramp: 0 → 1
        span = t_noon - t_rise
        if span == 0:
            return 1.0
        phase = (t - t_rise) / span        # 0 → 1
        return (1 - math.cos(math.pi * phase)) / 2
    else:
        # afternoon ramp: 1 → 0
        span = t_set - t_noon
        if span == 0:
            return 1.0
        phase = (t - t_noon) / span        # 0 → 1
        return (1 + math.cos(math.pi * phase)) / 2


def circadian_params(factor: float, gui_brightness_cap: float = 1.0) -> dict:
    if factor < 0.01:
        return {"kelvin": 1800, "brightness": 0.0, "white": 0}

    kelvin = 2700 + (6500 - 2700) * (factor ** 0.7)
    brightness = (factor ** 0.5) * gui_brightness_cap  # scale by cap
    white_blend = max(0.0, 1.0 - factor * 1.5)
    white = int(white_blend * 100 * brightness)

    return {"kelvin": kelvin, "brightness": brightness, "white": white}


# ──────────────────────────────────────────────
# APPLY TO STRIP
# ──────────────────────────────────────────────
def apply_to_leds(params: dict) -> None:
    """
    Push computed color + white to every pixel and latch.
    """
    r, g, b = kelvin_to_rgb(params["kelvin"])
    br = params["brightness"]
    w  = params["white"]

    r = int(r * br)
    g = int(g * br)
    b = int(b * br)

    pixels.fill((r, g, b, w))
    pixels.show()


def leds_off() -> None:
    pixels.fill((0, 0, 0, 0))
    pixels.show()


# ──────────────────────────────────────────────
# MAIN LOOP (called by scheduler / main.py)
# ──────────────────────────────────────────────
def run_loop(sun_times: dict, poll_interval: float = 30.0, verbose: bool = True, gui_brightness_cap: float = 1.0) -> None:
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
            params = circadian_params(factor, gui_brightness_cap)
            apply_to_leds(params)

            if verbose:
                print(f"[LED] {now.tm_hour:02d}:{now.tm_min:02d} "
                      f"factor={factor:.3f} K={params['kelvin']:.0f} "
                      f"br={params['brightness']:.2f} W={params['white']}")
            time.sleep(poll_interval)
