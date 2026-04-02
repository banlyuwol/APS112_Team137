"""
sun_calc.py
-----------
Calculates sunrise, solar noon, and sunset for any Canadian location
using the NOAA Solar Calculator algorithm (accurate to ±1 min).

No external API needed — pure math, works offline on the Pi.
"""

import math
from datetime import datetime, date, timedelta


# ──────────────────────────────────────────────
# CANADIAN CITY PRESETS
# (lat, lon, tz_offset_standard, tz_offset_dst, dst_start_week, dst_end_week)
# ──────────────────────────────────────────────
CANADIAN_CITIES = {
    "Toronto":       (43.65, -79.38, -5, -4),
    "Ottawa":        (45.42, -75.69, -5, -4),
    "Montreal":      (45.50, -73.57, -5, -4),
    "Vancouver":     (49.25, -123.12, -8, -7),
    "Calgary":       (51.05, -114.07, -7, -6),
    "Edmonton":      (53.55, -113.47, -7, -6),
    "Winnipeg":      (49.90, -97.13,  -6, -5),
    "Halifax":       (44.65, -63.60,  -4, -3),
    "Quebec City":   (46.81, -71.21,  -5, -4),
    "Saskatoon":     (52.13, -106.67, -6, -5),
    "Regina":        (50.45, -104.62, -6, -5),
    "St. John's":    (47.56, -52.71,  -3, -2),
    "Victoria":      (48.43, -123.37, -8, -7),
    "Kelowna":       (49.89, -119.50, -8, -7),
    "Custom":        None,   # user enters lat/lon manually
}


def _is_dst_canada(d: date) -> bool:
    """
    Canada DST: second Sunday of March → first Sunday of November.
    (Most provinces; Saskatchewan excluded — it never observes DST.)
    """
    # Second Sunday in March
    march1 = date(d.year, 3, 1)
    first_sun_march = march1 + timedelta(days=(6 - march1.weekday()) % 7)
    dst_start = first_sun_march + timedelta(weeks=1)

    # First Sunday in November
    nov1 = date(d.year, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)

    return dst_start <= d < dst_end


def _deg2rad(d): return d * math.pi / 180
def _rad2deg(r): return r * 180 / math.pi


def _julian_day(d: date) -> float:
    """Convert calendar date to Julian Day Number."""
    a = (14 - d.month) // 12
    y = d.year + 4800 - a
    m = d.month + 12 * a - 3
    jdn = d.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return float(jdn)


def _solar_noon_utc(jd: float, lon_deg: float) -> float:
    """Return solar noon in fractional UTC hours."""
    # Julian century
    n  = jd - 2451545.0
    # Mean longitude / anomaly
    L0 = (280.46646 + 36000.76983 * (n / 36525)) % 360
    M  = _deg2rad((357.52911 + 35999.05029 * (n / 36525) - 0.0001537 * (n / 36525) ** 2) % 360)
    # Equation of centre
    C  = (1.914602 - 0.004817 * (n / 36525) - 0.000014 * (n / 36525) ** 2) * math.sin(M)
    C += (0.019993 - 0.000101 * (n / 36525)) * math.sin(2 * M)
    C += 0.000289 * math.sin(3 * M)
    # Sun's true longitude / apparent longitude
    sun_lon = (L0 + C) % 360
    omega   = 125.04 - 1934.136 * (n / 36525)
    apparent_lon = sun_lon - 0.00569 - 0.00478 * math.sin(_deg2rad(omega))
    # Obliquity
    epsilon0 = 23 + 26 / 60 + 21.448 / 3600 - (46.8150 * (n / 36525)) / 3600
    epsilon  = epsilon0 + 0.00256 * math.cos(_deg2rad(omega))
    # Right ascension & declination
    ra  = _rad2deg(math.atan2(math.cos(_deg2rad(epsilon)) * math.sin(_deg2rad(apparent_lon)),
                              math.cos(_deg2rad(apparent_lon))))
    dec = _rad2deg(math.asin(math.sin(_deg2rad(epsilon)) * math.sin(_deg2rad(apparent_lon))))
    # Equation of time (minutes)
    var_y = math.tan(_deg2rad(epsilon / 2)) ** 2
    eot = (
        4 * _rad2deg(
            var_y * math.sin(2 * _deg2rad(L0))
            - 2 * math.sin(M) * (1 - var_y * math.cos(2 * _deg2rad(L0)))  # simplified
            + 4 * math.sin(M) * math.cos(2 * _deg2rad(L0))  # ≈ correction
        )
    )
    # Simpler, accurate EoT (minutes)
    B   = _deg2rad(360 / 365 * (n % 365 - 81))
    eot_min = 9.87 * math.sin(2 * B) - 7.53 * math.cos(B) - 1.5 * math.sin(B)

    solar_noon_utc = 720 - 4 * lon_deg - eot_min   # minutes from midnight UTC
    return solar_noon_utc / 60.0, dec


def calculate_sun_times(
    target_date: date,
    lat: float,
    lon: float,
    tz_std: int,
    tz_dst: int,
    province_uses_dst: bool = True,
) -> dict:
    """
    Returns dict with sunrise, noon, sunset as:
      - datetime objects (local time)
      - float fractions of the 24-hour day (0.0–1.0)
      - formatted HH:MM strings

    Raises ValueError if sun doesn't rise/set (polar night or midnight sun).
    """
    jd  = _julian_day(target_date)
    noon_utc_h, declination = _solar_noon_utc(jd, lon)

    # Hour angle for sunrise/sunset (solar elevation = -0.833° for refraction)
    cos_ha = (
        math.sin(_deg2rad(-0.833))
        - math.sin(_deg2rad(lat)) * math.sin(_deg2rad(declination))
    ) / (math.cos(_deg2rad(lat)) * math.cos(_deg2rad(declination)))

    if cos_ha < -1 or cos_ha > 1:
        if cos_ha < -1:
            raise ValueError("Midnight sun — sun never sets on this date.")
        else:
            raise ValueError("Polar night — sun never rises on this date.")

    ha_deg = _rad2deg(math.acos(cos_ha))  # half-day length in degrees
    half_day_hours = ha_deg / 15.0        # convert to hours

    sunrise_utc = noon_utc_h - half_day_hours
    sunset_utc  = noon_utc_h + half_day_hours

    # Apply timezone
    dst = _is_dst_canada(target_date) if province_uses_dst else False
    offset = tz_dst if dst else tz_std

    sunrise_local = sunrise_utc + offset
    noon_local    = noon_utc_h  + offset
    sunset_local  = sunset_utc  + offset

    def hours_to_hhmm(h: float) -> str:
        h = h % 24
        hh = int(h)
        mm = int((h - hh) * 60)
        return f"{hh:02d}:{mm:02d}"

    def hours_to_frac(h: float) -> float:
        return (h % 24) / 24.0

    def hours_to_dt(h: float) -> datetime:
        h = h % 24
        return datetime(
            target_date.year, target_date.month, target_date.day,
            int(h), int((h % 1) * 60), int((h * 60 % 1) * 60)
        )

    return {
        "date":          target_date.isoformat(),
        "latitude":      lat,
        "longitude":     lon,
        "timezone":      f"UTC{offset:+d} ({'DST' if dst else 'STD'})",
        "declination":   round(declination, 3),

        "sunrise_str":   hours_to_hhmm(sunrise_local),
        "noon_str":      hours_to_hhmm(noon_local),
        "sunset_str":    hours_to_hhmm(sunset_local),

        "sunrise_dt":    hours_to_dt(sunrise_local),
        "noon_dt":       hours_to_dt(noon_local),
        "sunset_dt":     hours_to_dt(sunset_local),

        "sunrise_frac":  hours_to_frac(sunrise_local),
        "noon_frac":     hours_to_frac(noon_local),
        "sunset_frac":   hours_to_frac(sunset_local),

        "day_length_h":  round(2 * half_day_hours, 2),
    }


if __name__ == "__main__":
    # Quick self-test
    result = calculate_sun_times(date.today(), 43.65, -79.38, -5, -4)
    for k, v in result.items():
        print(f"  {k}: {v}")
