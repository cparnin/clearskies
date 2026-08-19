"""Configuration for ClearSkies."""

import os


def _parse_horizon_mask(value: str) -> list:
    """Parse "250-340:90,340-20:35" into [(250.0, 340.0, 90.0), (340.0, 20.0, 35.0)]."""
    wedges = []
    for part in value.split(","):
        az_range, min_alt = part.split(":")
        az_start, az_end = az_range.split("-")
        wedges.append((float(az_start), float(az_end), float(min_alt)))
    return wedges

# ============================================================================
# REQUIRED: Change these to YOUR location and notification topic!
# ============================================================================

# Location - Get your coordinates from Google Maps (right-click → copy coordinates)
# Environment variables override the defaults (used by GitHub Actions).
# Defaults: Zephyrhills, FL (33541)
LATITUDE = float(os.environ.get("LATITUDE") or "28.2336")
LONGITUDE = float(os.environ.get("LONGITUDE") or "-82.1812")

# Timezone - Find yours at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TIMEZONE = "America/New_York"

# Location name (optional, just for display)
LOCATION_NAME = "Zephyrhills, FL"

# Notifications via ntfy.sh - Choose ANY unique topic name
# Then subscribe to that same topic in the ntfy app on your phone
NTFY_TOPIC = os.environ.get("NTFY_TOPIC") or "clearskies-chadp"

# ============================================================================
# OPTIONAL: Customize these if desired (sensible defaults below)
# ============================================================================

# The observing window runs from astronomical darkness (sun 18° below the
# horizon) all the way to astronomical dawn,
# so late-night targets are always considered — the DWARF3 can be left out
# overnight. Targets peaking before PRIME_END_HOUR get a scoring bonus;
# later peaks lose LATE_PENALTY_PER_HOUR for each hour past the cutoff and
# get grouped under "Overnight" in the notification.
PRIME_END_HOUR = 23           # 23 = 11 PM, 24 = midnight, 25 = 1 AM
LATE_PENALTY_PER_HOUR = 0.15  # score decay per hour a peak lands past prime

# Object type preference (points out of 10):
# galaxies strongly favored, ordinary nebulae a full point behind, clusters
# mostly ignored. Showpiece nebulae (SHOWPIECES in targets.py) are exempt -
# they score at full galaxy weight so the icons still make the list.
TYPE_WEIGHTS = {"galaxy": 1.5, "nebula": 0.5, "cluster": 0.2}

# Local horizon: targets peaking below MIN_ALTITUDE, or inside a HORIZON_MASK
# wedge and under that wedge's minimum altitude, are dropped entirely — a
# blocked target is not a weak target, it just can't be shot from this yard.
# HORIZON_MASK is a list of (az_start, az_end, min_alt_deg) wedges; azimuth
# ranges may wrap through north, e.g. (340, 20, 35). Set to [] for a clear
# 360° horizon. Env override format: "250-340:90,340-20:35".
# Defaults: the house blocks the WNW-NW sky at this site.
MIN_ALTITUDE = float(os.environ.get("MIN_ALTITUDE") or "30")
HORIZON_MASK = _parse_horizon_mask(os.environ.get("HORIZON_MASK") or "250-340:90")

# Scoring thresholds - adjust to be more or less picky
MIN_TARGET_SCORE = 6      # Only show targets scoring 6+ out of 10
MIN_CONDITIONS_SCORE = 6  # Only notify if conditions score 6+ out of 10
TOP_TARGETS_COUNT = 3     # Max targets per notification section (hard cap)

# DWARF3 telescope specifications (for FOV fit scoring)
# Only change these if you're using different equipment
DWARF3_FOV_DEGREES = 3.0          # Field of view in degrees (telephoto: 3° x 1.65°)
DWARF3_OPTIMAL_TARGET_MIN = 0.3   # Targets smaller than this get reduced FOV bonus
DWARF3_OPTIMAL_TARGET_MAX = 2.0   # Targets larger than this won't fit frame well
