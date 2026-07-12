"""Configuration for Clear Skies Tonight."""

import os

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

# The observing window runs from darkness (sunset + 2h) all the way to dawn,
# so late-night targets are always considered — the DWARF3 can be left out
# overnight. Targets peaking before PRIME_END_HOUR get a scoring bonus;
# later peaks lose LATE_PENALTY_PER_HOUR for each hour past the cutoff and
# get grouped under "Overnight" in the notification.
PRIME_END_HOUR = 24           # 24 = midnight, 23 = 11 PM, 25 = 1 AM
LATE_PENALTY_PER_HOUR = 0.15  # score decay per hour a peak lands past prime

# Object type preference (points out of 10):
# galaxies favored, nebulae close behind, clusters mostly ignored.
TYPE_WEIGHTS = {"galaxy": 1.5, "nebula": 1.0, "cluster": 0.2}

# Scoring thresholds - adjust to be more or less picky
MIN_TARGET_SCORE = 6      # Only show targets scoring 6+ out of 10
MIN_CONDITIONS_SCORE = 6  # Only notify if conditions score 6+ out of 10
TOP_TARGETS_COUNT = 8     # Max targets per section of the notification

# DWARF3 telescope specifications (for FOV fit scoring)
# Only change these if you're using different equipment
DWARF3_FOV_DEGREES = 3.0          # Field of view in degrees (telephoto: 3° x 1.65°)
DWARF3_OPTIMAL_TARGET_MIN = 0.3   # Targets smaller than this get reduced FOV bonus
DWARF3_OPTIMAL_TARGET_MAX = 2.0   # Targets larger than this won't fit frame well
