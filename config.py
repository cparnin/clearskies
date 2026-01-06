"""Configuration for Clear Skies Tonight."""

import os

# Location (reads from environment variables if set, otherwise uses defaults)
# Defaults are downtown Zephyrhills - set your actual coords in GitHub Secrets
LATITUDE = float(os.environ.get("LATITUDE", "28.2336"))
LONGITUDE = float(os.environ.get("LONGITUDE", "-82.1812"))
TIMEZONE = "America/New_York"
LOCATION_NAME = "Zephyrhills, FL"

# Notifications
NTFY_TOPIC = "clearskies-chadp"

# Scoring thresholds
MIN_TARGET_SCORE = 6  # Only show targets scoring this or higher
MIN_CONDITIONS_SCORE = 6  # Only notify if conditions score this or higher
TOP_TARGETS_COUNT = 5  # Number of targets to show in notification
