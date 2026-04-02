"""
main.py
-----------
Headless CLI alternative — use this when SSH-ing into the Pi
without a display attached.

Usage:
  python3 cli_main.py
"""

import argparse
from datetime import date, datetime

from sun_calc import calculate_sun_times
import led_controller

# Canada average
CANADA_LAT = 56.1304
CANADA_LON = -106.3468
TZ_STD = -6
TZ_DST = -5


def main():
    parser = argparse.ArgumentParser(description="Circadian LED controller (CLI)")

    parser.add_argument("--date", default=date.today().isoformat(),
                        help="YYYY-MM-DD (default: today)")
    parser.add_argument("--time", default=None,
                        help="HH:MM (default: current system time)")
    parser.add_argument("--leds", type=int, default=60,
                        help="Number of LEDs in the strip")
    parser.add_argument("--interval", type=int, default=30,
                        help="Loop polling interval in seconds")

    args = parser.parse_args()

    if args.leds <= 0:
        raise ValueError("LED count must be > 0")
    if args.interval <= 0:
        raise ValueError("Interval must be > 0")

    target_date = date.fromisoformat(args.date)

    # Use system time if not provided
    if args.time:
        current_time = datetime.strptime(args.time, "%H:%M").time()
    else:
        current_time = datetime.now().time()

    # Calculate sun times using Canada-average
    st = calculate_sun_times(
        target_date,
        CANADA_LAT,
        CANADA_LON,
        TZ_STD,
        TZ_DST,
    )

    # Configure LED strip
    led_controller.LED_COUNT = args.leds

    # Run LED loop silently (headless)
led_controller.run_loop(
    sun_times={
        "sunrise_frac": st["sunrise_frac"],
        "noon_frac": st["noon_frac"],
        "sunset_frac": st["sunset_frac"],
    },
    poll_interval=args.interval,
    verbose=False  # suppress prints
)

if __name__ == "__main__":
    main()
