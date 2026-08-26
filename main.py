"""ClearSkies - Main orchestrator."""

import re
import sys
from datetime import timedelta

import ephem

from astro import ephem_to_local, fmt_time, get_night, local_to_ephem, make_observer, to_deg
from config import MIN_CONDITIONS_SCORE, MIN_TARGET_SCORE, TOP_TARGETS_COUNT
from moon import get_moon_info
from notifier import send_notification
from targets import get_recommendations
from weather import get_weather


def find_clear_stretch(hours: list, max_cloud: int = 40, min_hours: int = 2) -> list | None:
    """Find the longest run of consecutive hours at or under max_cloud cover."""
    best, run = None, []
    for h in hours + [None]:
        if h and h["cloud_cover"] <= max_cloud:
            run.append(h)
        else:
            if len(run) >= min_hours and (best is None or len(run) > len(best)):
                best = run
            run = []
    return best


def effective_night(night: dict, stretch: list | None) -> dict:
    """Clamp the observing window to the clear stretch of weather, so targets
    are scored for when the sky is actually usable - not for hours of clouds."""
    if stretch is None:
        return night

    start = max(night["window_start"], local_to_ephem(stretch[0]["time"]))
    end = min(night["window_end"], local_to_ephem(stretch[-1]["time"] + timedelta(hours=1)))
    if start >= end:
        return night

    eff = dict(night)
    eff["window_start"] = ephem.Date(start)
    eff["window_end"] = ephem.Date(end)
    eff["start_local"] = ephem_to_local(start)
    eff["end_local"] = ephem_to_local(end)
    return eff


def moonlit_fraction(hours: list) -> float:
    """Fraction of the given forecast hours during which the moon is up."""
    def moon_up(t):
        return to_deg(ephem.Moon(make_observer(local_to_ephem(t))).alt) > 0
    return sum(moon_up(h["time"]) for h in hours) / len(hours)


def assess_conditions(weather: dict, moon: dict, stretch: list | None,
                      moonlit: float) -> tuple[int, str]:
    """Score overall conditions 1-10 and return a summary.

    Scores the best clear stretch of the night rather than a single evening
    snapshot - a night that clears at 11 PM is still worth setting up for.
    """
    hours = weather["hours"]
    all_night = stretch is None or (
        stretch[0]["time"] == hours[0]["time"] and stretch[-1]["time"] == hours[-1]["time"]
    )

    score = 10
    issues = []

    if stretch is None:
        # No 2-hour run under 40% clouds - not an imaging night
        stretch = hours
        score -= 2
        issues.append("no clear stretch")

    def avg(key):
        return sum(h[key] for h in stretch) / len(stretch)

    clouds = avg("cloud_cover")
    if clouds > 80:
        score -= 5
        issues.append(f"Cloudy ({clouds:.0f}%)")
    elif clouds > 50:
        score -= 3
        issues.append(f"Partly cloudy ({clouds:.0f}%)")
    elif clouds > 25:
        score -= 1
        issues.append(f"Some clouds ({clouds:.0f}%)")

    humidity = avg("humidity")
    if humidity > 90:
        score -= 2
        issues.append("Very humid")
    elif humidity > 80:
        score -= 1
        issues.append("Humid")

    wind = avg("wind_mph")
    if wind > 15:
        score -= 2
        issues.append(f"Windy ({wind:.0f} mph)")
    elif wind > 10:
        score -= 1
        issues.append(f"Breezy ({wind:.0f} mph)")

    # Moon: phase-scaled penalty, weighted by how much of the usable stretch
    # is moonlit. A bright moon washes out broadband targets (galaxies
    # especially), so a full moon up all night kills the night outright —
    # but one that sets early barely dings it.
    phase = moon["phase_pct"]
    moon_penalty = round((5 if phase > 80 else 3 if phase > 50 else 1 if phase > 25 else 0) * moonlit)
    if moon_penalty:
        score -= moon_penalty
        label = "Bright moon" if phase > 80 else "Moon up"
        issues.append(f"{label} ({phase:.0f}%)")

    # Timing notes when only part of the night is clear
    if not all_night:
        if stretch[0]["time"] != hours[0]["time"]:
            issues.append(f"clears ~{stretch[0]['label']}")
        if stretch[-1]["time"] != hours[-1]["time"]:
            issues.append(f"clouds return ~{stretch[-1]['label']}")

    score = max(1, score)
    summary = ", ".join(issues) if issues else "Excellent conditions!"
    return score, summary


_CATALOG_PREFIX = re.compile(r"^(M|NGC|IC|Sh2|B|C|Cr|Mel)[\s-]*\d")


def display_name(name: str) -> str:
    """Notification-friendly target name: drop a leading catalog designation
    ("M8 - Lagoon Nebula" -> "Lagoon Nebula") but keep descriptive suffixes
    ("Veil Nebula - East") and bare designations ("M77 + NGC 1055") intact."""
    prefix, sep, rest = name.partition(" - ")
    if sep and rest and _CATALOG_PREFIX.match(prefix):
        return rest
    return name


def moon_emoji(phase_pct: float) -> str:
    if phase_pct < 5:
        return "🌑"
    if phase_pct < 45:
        return "🌒"
    if phase_pct < 55:
        return "🌓"
    if phase_pct < 95:
        return "🌔"
    return "🌕"


def get_priority(conditions_score: int, best_target_score: float) -> str:
    """Determine notification priority based on scores."""
    combined = (conditions_score + best_target_score) / 2
    if combined >= 8:
        return "high"
    if combined >= 6:
        return "default"
    return "low"


def build_message(conditions_summary: str, night: dict, imaging: dict, moon: dict,
                  top: list) -> str:
    """Body is ntfy Markdown: bold section headers render on Android/web."""
    sky = "✨" if conditions_summary == "Excellent conditions!" else "🌤️"
    lines = [f"{sky} {conditions_summary}"]

    moon_line = f"{moon_emoji(moon['phase_pct'])} {moon['phase_name']} {moon['phase_pct']:.0f}%"
    if moon["is_up"] and moon["setting"]:
        moon_line += f", sets {moon['setting']}"
    elif not moon["is_up"] and moon["rising"]:
        moon_line += f", rises {moon['rising']}"
    lines.append(moon_line)

    window = f"🕐 Dark {fmt_time(night['window_start'])}–{fmt_time(night['window_end'])}"
    if imaging["window_start"] != night["window_start"] or imaging["window_end"] != night["window_end"]:
        window += f" · Clear {fmt_time(imaging['window_start'])}–{fmt_time(imaging['window_end'])}"
    lines.append(window)

    lines.append("")
    lines.append("**🔭 Shoot tonight**")
    for t in top:
        line = f"• {display_name(t['name'])} — peak {t['peak_time']}"
        if t["is_late"]:
            line += " (overnight, leave it out)"
        lines.append(line)

    return "\n".join(lines)


def run(dry_run: bool = False):
    """Main entry point."""
    night = get_night()

    weather = get_weather(night)
    if not weather:
        print("Failed to fetch weather")
        return

    moon = get_moon_info(night)

    stretch = find_clear_stretch(weather["hours"])
    imaging = effective_night(night, stretch)
    targets = get_recommendations(imaging)

    moonlit = moonlit_fraction(stretch or weather["hours"])
    conditions_score, conditions_summary = assess_conditions(weather, moon, stretch, moonlit)

    top = [t for t in targets if t["score"] >= MIN_TARGET_SCORE][:TOP_TARGETS_COUNT]

    if conditions_score < MIN_CONDITIONS_SCORE:
        print(f"Conditions poor ({conditions_score}/10): {conditions_summary}")
        print("No notification sent.")
        return

    if not top:
        print(f"No targets scoring {MIN_TARGET_SCORE}+ tonight.")
        print("No notification sent.")
        return

    quality = ("Excellent" if conditions_score >= 9 else
               "Great" if conditions_score >= 8 else
               "Good" if conditions_score >= 7 else "Fair")
    title = f"{quality} night for imaging — {conditions_score}/10"
    message = build_message(conditions_summary, night, imaging, moon, top)
    priority = get_priority(conditions_score, top[0]["score"])

    print(f"=== {title} (priority: {priority}) ===")
    print(message)
    print()

    if dry_run:
        print("(dry run - notification not sent)")
        return

    if send_notification(title, message, priority):
        print("Notification sent!")
    else:
        print("Notification failed!")


if __name__ == "__main__":
    run(dry_run="--dry-run" in sys.argv)
