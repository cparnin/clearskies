"""Clear Skies Tonight - Main orchestrator."""

from weather import get_weather
from moon import get_moon_info
from targets import get_recommendations
from notifier import send_notification
from config import MIN_TARGET_SCORE, MIN_CONDITIONS_SCORE, TOP_TARGETS_COUNT


def assess_conditions(weather: dict, moon: dict) -> tuple[int, str]:
    """Score overall conditions 1-10 and return summary.

    Returns:
        (score, summary_text)
    """
    score = 10  # Start perfect, deduct for issues
    issues = []

    # Cloud cover (biggest factor)
    clouds = weather["cloud_cover"]
    if clouds > 90:
        score -= 5
        issues.append(f"Cloudy ({clouds}%)")
    elif clouds > 70:
        score -= 3
        issues.append(f"Partly cloudy ({clouds}%)")
    elif clouds > 40:
        score -= 1
        issues.append(f"Some clouds ({clouds}%)")

    # Humidity (affects transparency)
    humidity = weather["humidity"]
    if humidity > 90:
        score -= 2
        issues.append("Very humid")
    elif humidity > 80:
        score -= 1
        issues.append("Humid")

    # Wind (affects tracking)
    wind = weather["wind_mph"]
    if wind > 15:
        score -= 2
        issues.append(f"Windy ({wind:.0f} mph)")
    elif wind > 10:
        score -= 1
        issues.append(f"Breezy ({wind:.0f} mph)")

    # Moon phase (for DSO imaging)
    if moon["phase_pct"] > 75 and moon["is_up"]:
        score -= 2
        issues.append(f"Bright moon ({moon['phase_pct']:.0f}%)")
    elif moon["phase_pct"] > 50 and moon["is_up"]:
        score -= 1
        issues.append(f"Moon up ({moon['phase_pct']:.0f}%)")

    score = max(1, score)  # Floor at 1

    if not issues:
        summary = "Excellent conditions!"
    else:
        summary = ", ".join(issues)

    return score, summary


def get_priority(conditions_score: int, best_target_score: float) -> str:
    """Determine notification priority based on scores."""
    combined = (conditions_score + best_target_score) / 2

    if combined >= 8:
        return "high"
    elif combined >= 6:
        return "default"
    else:
        return "low"


def run():
    """Main entry point."""
    # Gather data
    weather = get_weather()
    if not weather:
        print("Failed to fetch weather")
        return

    moon = get_moon_info()
    targets = get_recommendations()

    # Assess conditions
    conditions_score, conditions_summary = assess_conditions(weather, moon)

    # Get top targets
    good_targets = [t for t in targets if t["score"] >= MIN_TARGET_SCORE][:TOP_TARGETS_COUNT]

    # Decide whether to notify
    if conditions_score < MIN_CONDITIONS_SCORE:
        print(f"Conditions poor ({conditions_score}/10): {conditions_summary}")
        print("No notification sent.")
        return

    if not good_targets:
        print("No targets scoring 6+ tonight.")
        print("No notification sent.")
        return

    # Build notification
    best = good_targets[0]
    title = f"Clear Skies Tonight [{conditions_score}/10]"

    lines = [conditions_summary]
    lines.append(f"Window: {moon['window_start']} - {moon['window_end']}")
    lines.append("")
    lines.append("Top targets:")
    for i, t in enumerate(good_targets, 1):
        lines.append(f"{i}. {t['name']} [{t['score']}/10] peak @ {t['transit_time']}")

    message = "\n".join(lines)
    priority = get_priority(conditions_score, best["score"])

    # Send it
    print(f"Conditions: {conditions_score}/10 - {conditions_summary}")
    print(f"Best target: {best['name']} [{best['score']}/10]")
    print(f"Priority: {priority}")
    print()

    success = send_notification(title, message, priority)
    if success:
        print("Notification sent!")
    else:
        print("Notification failed!")


if __name__ == "__main__":
    run()
