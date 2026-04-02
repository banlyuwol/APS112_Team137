"""
sun_calc.py
-----------
Calculates sunrise, solar noon, and sunset using NOAA algorithm.

Simplified for:
→ Fixed Canada-average location
→ No city selection required
"""

import math
from datetime import datetime, date, timedelta


# ──────────────────────────────────────────────
# CANADA AVERAGE (used everywhere)
# ──────────────────────────────────────────────
CANADA_LAT = 56.1304
CANADA_LON = -106.3468
TZ_STD = -6
TZ_DST = -5


# ──────────────────────────────────────────────
# DST LOGIC (Canada-wide)
# ──────────────────────────────────────────────
def _is_dst_canada(d: date) -> bool:
    march1 = date(d.year, 3, 1)
    first_sun_march = march1 + timedelta(days=(6 - march1.weekday()) % 7)
    dst_start = first_sun_march + timedelta(weeks=1)

    nov1 = date(d.year, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)

    return dst_start <= d < dst_end


def _deg2rad(d): return d * math.pi / 180
def _rad2deg(r): return r * 180 / math.pi


def _julian_day(d: date) -> float:
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    jdn = d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return float(jdn)


def _solar_noon_utc(jd: float, lon_deg: float):
    n = jd - 2451545.0

    L0 = (280.46646 + 36000.76983 * (n / 36525)) % 360
    M  = _deg2rad((357.52911 + 35999.05029 * (n / 36525)) % 360)

    C  = 1.914602 * math.sin(M) + 0.019993 * math.sin(2 * M)

    sun_lon = (L0 + C) % 360
    omega   = 125.04 - 1934.136 * (n / 36525)
    apparent_lon = sun_lon - 0.00569 - 0.00478 * math.sin(_deg2rad(omega))

    epsilon = 23.44

    dec = _rad2deg(math.asin(math.sin(_deg2rad(epsilon)) * math.sin(_deg2rad(apparent_lon))))

    B = _deg2rad(360 / 365 * (n % 365 - 81))
    eot_min = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

    solar_noon_utc = 720 - 4 * lon_deg - eot_min
    return solar_noon_utc / 60.0, dec


def calculate_sun_times(
    target_date: date,
    lat: float,
    lon: float,
    tz_std: int,
    tz_dst: int,
) -> dict:

    jd  = _julian_day(target_date)
    noon_utc_h, declination = _solar_noon_utc(jd, lon)

    cos_ha = (
        math.sin(_deg2rad(-0.833))
        - math.sin(_deg2rad(lat)) * math.sin(_deg2rad(declination))
    ) / (math.cos(_deg2rad(lat)) * math.cos(_deg2rad(declination)))

    if cos_ha < -1:
        raise ValueError("Midnight sun — sun never sets.")
    if cos_ha > 1:
        raise ValueError("Polar night — sun never rises.")

    ha_deg = _rad2deg(math.acos(cos_ha))
    half_day_hours = ha_deg / 15.0

    sunrise_utc = noon_utc_h - half_day_hours
    sunset_utc  = noon_utc_h + half_day_hours

    dst = _is_dst_canada(target_date)
    offset = tz_dst if dst else tz_std

    sunrise_local = sunrise_utc + offset
    noon_local    = noon_utc_h  + offset
    sunset_local  = sunset_utc  + offset

    def to_frac(h): return (h % 24) / 24.0
    def to_str(h): return f"{int(h%24):02d}:{int((h%1)*60):02d}"

    return {
        "sunrise_frac": to_frac(sunrise_local),
        "noon_frac":    to_frac(noon_local),
        "sunset_frac":  to_frac(sunset_local),

        "sunrise_str":  to_str(sunrise_local),
        "noon_str":     to_str(noon_local),
        "sunset_str":   to_str(sunset_local),
    }


# ──────────────────────────────────────────────
# 🔥 SIMPLE FUNCTION FOR YOUR GUI
# ──────────────────────────────────────────────
def calculate_canada_sun_times(target_date: date) -> dict:
    return calculate_sun_times(
        target_date,
        CANADA_LAT,
        CANADA_LON,
        TZ_STD,
        TZ_DST,
    )


if __name__ == "__main__":
    result = calculate_canada_sun_times(date.today())
    for k, v in result.items():
        print(f"{k}: {v}")
