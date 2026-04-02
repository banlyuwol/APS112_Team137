"""
cli_main.py
-----------
Headless CLI alternative — use this when SSH-ing into the Pi
without a display attached.

Usage:
  python3 cli_main.py
  python3 cli_main.py --city Toronto --date 2025-12-21 --leds 60
"""

import argparse
from datetime import date

from sun_calc import calculate_sun_times, CANADIAN_CITIES
import led_controller


def main():
    parser = argparse.ArgumentParser(description="Circadian LED controller (CLI)")
    parser.add_argument("--city",     default=None, help="Canadian city name")
    parser.add_argument("--lat",      type=float, default=None)
    parser.add_argument("--lon",      type=float, default=None)
    parser.add_argument("--date",     default=date.today().isoformat(),
                        help="YYYY-MM-DD (default: today)")
    parser.add_argument("--leds",     type=int, default=60,
                        help="Number of LEDs in strip")
    parser.add_argument("--interval", type=int, default=30,
                        help="Update interval in seconds")
    parser.add_argument("--no-dst",   action="store_true",
                        help="Disable DST (e.g. Saskatchewan)")
    args = parser.parse_args()

    # ── Resolve location ──────────────────────────────────────
    if args.city:
        city = args.city.strip()
        coords = CANADIAN_CITIES.get(city)
        if coords is None:
            print(f"Unknown city '{city}'. Available cities:")
            for c in CANADIAN_CITIES:
                print(f"  {c}")
            return
        lat, lon, tz_std, tz_dst = coords
    elif args.lat is not None and args.lon is not None:
        lat, lon, tz_std, tz_dst = args.lat, args.lon, -5, -4
    else:
        # Interactive prompt
        print("\nAvailable cities:")
        cities = [c for c in CANADIAN_CITIES if c != "Custom"]
        for i, c in enumerate(cities, 1):
            print(f"  {i:2d}. {c}")
        choice = input("\nEnter city number or name (or 'custom'): ").strip()
        try:
            idx = int(choice) - 1
            city = cities[idx]
        except (ValueError, IndexError):
            city = choice
        coords = CANADIAN_CITIES.get(city)
        if coords:
            lat, lon, tz_std, tz_dst = coords
        else:
            lat   = float(input("Latitude  (e.g. 43.65): "))
            lon   = float(input("Longitude (e.g. -79.38): "))
            tz_std, tz_dst = -5, -4

    # ── Calculate sun times ───────────────────────────────────
    target = date.fromisoformat(args.date)
    dst    = not args.no_dst

    try:
        st = calculate_sun_times(target, lat, lon, tz_std, tz_dst, dst)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("\n" + "═" * 44)
    print(f"  📍 {lat:.4f}°N, {lon:.4f}°E   {st['timezone']}")
    print(f"  📅 {st['date']}")
    print("─" * 44)
    print(f"  🌅 Sunrise    : {st['sunrise_str']}")
    print(f"  ☀️  Solar Noon : {st['noon_str']}")
    print(f"  🌇 Sunset     : {st['sunset_str']}")
    print(f"  ⏱  Day length  : {st['day_length_h']} h")
    print("═" * 44)

    input("\nPress Enter to start the LED controller (Ctrl+C to quit)…")

    led_controller.LED_COUNT = args.leds
    led_controller.run_loop(
        sun_times={
            "sunrise_frac": st["sunrise_frac"],
            "noon_frac":    st["noon_frac"],
            "sunset_frac":  st["sunset_frac"],
        },
        poll_interval=args.interval,
    )


if __name__ == "__main__":
    main()
