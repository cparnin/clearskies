"""Configuration for Clear Skies Tonight."""

import os

# ============================================================================
# REQUIRED: Change these to YOUR location and notification topic!
# ============================================================================

# Location - Get your coordinates from Google Maps (right-click → copy coordinates)
# These read from environment variables for GitHub Actions, or use defaults below
# ⚠️ CHANGE THE DEFAULT VALUES to your location!
LATITUDE = float(os.environ.get("LATITUDE", "28.2336"))   # ← YOUR latitude here
LONGITUDE = float(os.environ.get("LONGITUDE", "-82.1812"))  # ← YOUR longitude here

# Timezone - Find yours at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
# ⚠️ CHANGE THIS if you're not in Eastern Time!
TIMEZONE = "America/New_York"  # ← YOUR timezone here

# Location name (optional, just for display)
LOCATION_NAME = "Zephyrhills, FL"  # ← YOUR city/location name (optional)

# Notifications via ntfy.sh - Choose ANY unique topic name
# Then subscribe to that same topic in the ntfy app on your phone
# ⚠️ CHANGE THIS to your own topic name!
NTFY_TOPIC = "clearskies-chadp"  # ← YOUR unique topic name here

# ============================================================================
# OPTIONAL: Customize these if desired (sensible defaults below)
# ============================================================================

# Observing constraints
MAX_OBSERVING_HOUR = 23  # Don't recommend targets peaking after 11 PM (23:00)
                         # Change to 24 for midnight, 22 for 10 PM, 1 for 1 AM, etc.

# Scoring thresholds - adjust to be more or less picky
MIN_TARGET_SCORE = 6  # Only show targets scoring 6+ out of 10
                      # Lower to 5.5 to see more targets
                      # Raise to 7 for only excellent targets

MIN_CONDITIONS_SCORE = 6  # Only notify if weather conditions score 6+ out of 10
                          # Lower to 5 to get notified on marginal nights

TOP_TARGETS_COUNT = 10  # Number of targets to show in notification
                        # Increase to 15 for more options
                        # Decrease to 5 for just the best

# DWARF3 telescope specifications (for FOV fit scoring)
# Only change these if you're using different equipment
DWARF3_FOV_DEGREES = 3.0          # Field of view in degrees (telephoto: 3° x 1.65°)
DWARF3_OPTIMAL_TARGET_MIN = 0.3   # Targets smaller than this get reduced FOV bonus
DWARF3_OPTIMAL_TARGET_MAX = 2.0   # Targets larger than this won't fit frame well
