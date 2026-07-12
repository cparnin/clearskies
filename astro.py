"""Shared astronomy helpers: observer setup and tonight's dark window."""

import math
from datetime import datetime, timedelta, timezone

import ephem
import pytz

from config import LATITUDE, LONGITUDE, TIMEZONE, PRIME_END_HOUR

LOCAL_TZ = pytz.timezone(TIMEZONE)


def ephem_to_local(ephem_date) -> datetime:
    """Convert an ephem date to a local-timezone datetime."""
    utc_dt = ephem.Date(ephem_date).datetime().replace(tzinfo=pytz.UTC)
    return utc_dt.astimezone(LOCAL_TZ)


def to_deg(radians) -> float:
    return float(radians) * 180 / math.pi


def fmt_time(ephem_date) -> str:
    return ephem_to_local(ephem_date).strftime("%-I:%M %p")


def make_observer(date=None) -> ephem.Observer:
    obs = ephem.Observer()
    obs.lat = str(LATITUDE)
    obs.lon = str(LONGITUDE)
    obs.date = date if date is not None else datetime.now(timezone.utc)
    return obs


def get_night() -> dict:
    """Compute tonight's observing window.

    The window runs from darkness (sunset + 2h) to an hour before sunrise,
    so late-night targets are always considered — the DWARF3 can run
    unattended all night. `prime_end` marks the before-midnight cutoff:
    targets peaking earlier get a scoring bonus.
    """
    obs = make_observer()
    sun = ephem.Sun()

    sunset = obs.next_setting(sun)
    sunrise = make_observer(sunset).next_rising(sun)

    window_start = ephem.Date(sunset + 2 * ephem.hour)
    window_end = ephem.Date(sunrise - 1 * ephem.hour)

    # Prime cutoff: PRIME_END_HOUR is hours after the start of the evening's
    # calendar day (24 = midnight, 23 = 11 PM, 25 = 1 AM).
    start_local = ephem_to_local(window_start)
    day_start = start_local.replace(hour=0, minute=0, second=0, microsecond=0)
    prime_local = day_start + timedelta(hours=PRIME_END_HOUR)
    if prime_local < start_local:
        prime_local += timedelta(days=1)
    prime_end = min(ephem.Date(prime_local.astimezone(pytz.UTC)), window_end)

    return {
        "sunset": sunset,
        "sunrise": sunrise,
        "window_start": window_start,
        "window_end": window_end,
        "prime_end": prime_end,
        "start_local": start_local,
        "end_local": ephem_to_local(window_end),
    }


if __name__ == "__main__":
    night = get_night()
    print(f"Sunset:      {fmt_time(night['sunset'])}")
    print(f"Dark window: {fmt_time(night['window_start'])} - {fmt_time(night['window_end'])}")
    print(f"Prime until: {fmt_time(night['prime_end'])}")
