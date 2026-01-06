"""Configuration for Clear Skies Tonight."""

# Location
LATITUDE = 28.23
LONGITUDE = -82.18
TIMEZONE = "America/New_York"
LOCATION_NAME = "Zephyrhills, FL"

# Notifications
NTFY_TOPIC = "clearskies-chadp"

# Scoring thresholds
MIN_TARGET_SCORE = 6  # Only show targets scoring this or higher
MIN_CONDITIONS_SCORE = 5  # Only notify if conditions score this or higher
TOP_TARGETS_COUNT = 5  # Number of targets to show in notification
