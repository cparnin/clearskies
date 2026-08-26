"""Moon phase and position for tonight's observing window."""

import ephem

from astro import fmt_time, get_night, make_observer, to_deg


def phase_name(phase_pct: float) -> str:
    if phase_pct < 5:
        return "New Moon"
    if phase_pct < 45:
        return "Crescent"
    if phase_pct < 55:
        return "Half Moon"
    if phase_pct < 95:
        return "Gibbous"
    return "Full Moon"


def get_moon_info(night: dict = None) -> dict:
    """Get moon information for tonight's window."""
    night = night or get_night()
    obs = make_observer(night["window_start"])
    moon = ephem.Moon(obs)

    altitude_deg = to_deg(moon.alt)

    rising = setting = None
    try:
        rising = obs.next_rising(moon)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        pass
    try:
        setting = obs.next_setting(moon)
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        pass

    return {
        "phase_pct": round(moon.phase, 1),
        "phase_name": phase_name(moon.phase),
        "altitude_deg": round(altitude_deg, 1),
        "is_up": altitude_deg > 0,
        "rising": fmt_time(rising) if rising else None,
        "setting": fmt_time(setting) if setting else None,
        "window_start": fmt_time(night["window_start"]),
        "window_end": fmt_time(night["window_end"]),
    }


if __name__ == "__main__":
    night = get_night()
    info = get_moon_info(night)
    print(f"Moon at start of window ({info['window_start']}):\n")
    print(f"Phase: {info['phase_name']} ({info['phase_pct']}%)")
    print(f"Altitude: {info['altitude_deg']}° ({'up' if info['is_up'] else 'down'})")
    print(f"Next rise: {info['rising'] or 'n/a'}")
    print(f"Next set: {info['setting'] or 'n/a'}")
