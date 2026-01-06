"""Weather data from Open-Meteo API."""

import requests
import pytz
from datetime import datetime, timezone
import ephem
from config import LATITUDE, LONGITUDE, TIMEZONE

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"
LOCAL_TZ = pytz.timezone(TIMEZONE)


def ephem_to_local(ephem_date) -> datetime:
    """Convert ephem date to local timezone datetime."""
    utc_dt = ephem.Date(ephem_date).datetime().replace(tzinfo=pytz.UTC)
    return utc_dt.astimezone(LOCAL_TZ)


def get_viewing_hour() -> int:
    """Get the hour (0-23) for tonight's viewing time (2hrs after sunset)."""
    obs = ephem.Observer()
    obs.lat = str(LATITUDE)
    obs.lon = str(LONGITUDE)
    obs.date = datetime.now(timezone.utc)

    sun = ephem.Sun()
    sunset = obs.next_setting(sun)
    viewing_time = ephem_to_local(ephem.Date(sunset + 2 * ephem.hour))
    return viewing_time.hour


def get_weather() -> dict | None:
    """Fetch weather forecast for tonight's viewing time.

    Returns:
        dict with cloud_cover, humidity, visibility_mi, wind_mph, temperature_f, forecast_hour
        or None if request fails
    """
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "hourly": "cloud_cover,relative_humidity_2m,visibility,wind_speed_10m,temperature_2m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": TIMEZONE,
        "forecast_days": 2,
    }

    try:
        response = requests.get(OPENMETEO_URL, params=params)
        response.raise_for_status()
        data = response.json()

        hourly = data["hourly"]
        times = hourly["time"]

        # Find tonight's viewing hour (in local timezone)
        viewing_hour = get_viewing_hour()
        today = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        target_time = f"{today}T{viewing_hour:02d}:00"

        # Find index for target time
        try:
            idx = times.index(target_time)
        except ValueError:
            # Fallback to first evening hour available
            idx = viewing_hour

        return {
            "cloud_cover": hourly["cloud_cover"][idx],  # %
            "humidity": hourly["relative_humidity_2m"][idx],  # %
            "visibility_mi": hourly["visibility"][idx] / 1609.34,  # convert m to miles
            "wind_mph": hourly["wind_speed_10m"][idx],  # mph
            "temperature_f": hourly["temperature_2m"][idx],  # fahrenheit
            "forecast_hour": times[idx],
        }
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return None


if __name__ == "__main__":
    weather = get_weather()
    if weather:
        print(f"Forecast for: {weather['forecast_hour']}\n")
        print(f"Cloud cover: {weather['cloud_cover']}%")
        print(f"Humidity: {weather['humidity']}%")
        print(f"Visibility: {weather['visibility_mi']:.1f} mi")
        print(f"Wind: {weather['wind_mph']:.1f} mph")
        print(f"Temperature: {weather['temperature_f']:.1f}°F")
    else:
        print("Failed to fetch weather")
