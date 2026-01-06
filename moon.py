"""Moon phase and position calculations."""

import ephem
from datetime import datetime, timezone
from config import LATITUDE, LONGITUDE


def get_observer_tonight() -> ephem.Observer:
    """Create an observer for tonight's prime viewing time (2 hrs after sunset)."""
    obs = ephem.Observer()
    obs.lat = str(LATITUDE)
    obs.lon = str(LONGITUDE)
    obs.date = datetime.now(timezone.utc)

    # Get next sunset
    sun = ephem.Sun()
    try:
        next_sunset = obs.next_setting(sun)
    except ephem.AlwaysUpError:
        next_sunset = obs.date

    # Set time to 2 hours after sunset
    obs.date = ephem.Date(next_sunset + 2 * ephem.hour)
    return obs


def get_moon_info() -> dict:
    """Get moon information for tonight.

    Returns:
        dict with phase_pct, altitude_deg, rising, setting, phase_name, viewing_window
    """
    obs = get_observer_tonight()
    moon = ephem.Moon(obs)

    # Phase percentage (0 = new, 100 = full)
    phase_pct = moon.phase

    # Current altitude in degrees
    altitude_deg = float(moon.alt) * 180 / 3.14159

    # Rise and set times (raw for calculations)
    moon_rise_time = None
    try:
        moon_rise_time = obs.next_rising(moon)
        rising = ephem.localtime(moon_rise_time).strftime("%-I:%M %p")
    except ephem.AlwaysUpError:
        rising = "Always up"
    except ephem.NeverUpError:
        rising = "Never rises"

    try:
        setting = ephem.localtime(obs.next_setting(moon)).strftime("%-I:%M %p")
    except ephem.AlwaysUpError:
        setting = "Always up"
    except ephem.NeverUpError:
        setting = "Never sets"

    # Phase name
    if phase_pct < 5:
        phase_name = "New Moon"
    elif phase_pct < 45:
        phase_name = "Crescent"
    elif phase_pct < 55:
        phase_name = "Half Moon"
    elif phase_pct < 95:
        phase_name = "Gibbous"
    else:
        phase_name = "Full Moon"

    # Calculate viewing window
    sun = ephem.Sun()
    obs_now = ephem.Observer()
    obs_now.lat = str(LATITUDE)
    obs_now.lon = str(LONGITUDE)
    obs_now.date = datetime.now(timezone.utc)

    sunset = obs_now.next_setting(sun)
    sunrise = obs_now.next_rising(sun)

    window_start = ephem.localtime(ephem.Date(sunset + 2 * ephem.hour)).strftime("%-I:%M %p")

    # Window ends at moon rise (if bright moon) or sunrise - 1hr
    if phase_pct > 50 and moon_rise_time and moon_rise_time < sunrise:
        window_end = ephem.localtime(moon_rise_time).strftime("%-I:%M %p")
        window_note = "moon rise"
    else:
        window_end = ephem.localtime(ephem.Date(sunrise - 1 * ephem.hour)).strftime("%-I:%M %p")
        window_note = "dawn"

    return {
        "phase_pct": round(phase_pct, 1),
        "phase_name": phase_name,
        "altitude_deg": round(altitude_deg, 1),
        "rising": rising,
        "setting": setting,
        "is_up": altitude_deg > 0,
        "window_start": window_start,
        "window_end": window_end,
        "window_note": window_note,
    }


if __name__ == "__main__":
    obs = get_observer_tonight()
    viewing_time = ephem.localtime(obs.date).strftime("%-I:%M %p")
    print(f"Moon info for tonight ({viewing_time}):\n")

    info = get_moon_info()
    print(f"Phase: {info['phase_name']} ({info['phase_pct']}%)")
    print(f"Altitude: {info['altitude_deg']}°")
    print(f"Moon is {'up' if info['is_up'] else 'down'}")
    print(f"Next rise: {info['rising']}")
    print(f"Next set: {info['setting']}")
    print(f"\nBest window: {info['window_start']} - {info['window_end']} ({info['window_note']})")
