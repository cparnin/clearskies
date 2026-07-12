"""Weather data from Open-Meteo API, sampled across the whole observing window."""

from datetime import datetime

import requests

from astro import LOCAL_TZ, get_night
from config import LATITUDE, LONGITUDE, TIMEZONE

OPENMETEO_URL = "https://api.open-meteo.com/v1/forecast"


def get_weather(night: dict = None) -> dict | None:
    """Fetch hourly forecast covering tonight's observing window.

    Returns a dict with `hours` (one sample per hour across the window) plus
    the first hour's values at the top level for convenience, or None on failure.
    """
    night = night or get_night()

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
        response = requests.get(OPENMETEO_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return None

    hourly = data["hourly"]
    window_start = night["start_local"].replace(minute=0, second=0, microsecond=0)
    window_end = night["end_local"]

    samples = []
    for i, ts in enumerate(hourly["time"]):
        # Open-Meteo returns naive local ISO timestamps when timezone is set
        t = LOCAL_TZ.localize(datetime.fromisoformat(ts))
        if window_start <= t <= window_end:
            samples.append({
                "time": t,
                "label": t.strftime("%-I %p"),
                "cloud_cover": hourly["cloud_cover"][i],
                "humidity": hourly["relative_humidity_2m"][i],
                "wind_mph": hourly["wind_speed_10m"][i],
                "temperature_f": hourly["temperature_2m"][i],
                "visibility_mi": hourly["visibility"][i] / 1609.34,
            })

    if not samples:
        print("Weather: no forecast hours matched tonight's window")
        return None

    evening = samples[0]
    return {
        "hours": samples,
        "cloud_cover": evening["cloud_cover"],
        "humidity": evening["humidity"],
        "wind_mph": evening["wind_mph"],
        "temperature_f": evening["temperature_f"],
        "visibility_mi": evening["visibility_mi"],
        "forecast_hour": evening["time"].isoformat(),
    }


if __name__ == "__main__":
    weather = get_weather()
    if weather:
        print("Hourly forecast for tonight's window:\n")
        print(f"{'Hour':>6}  {'Clouds':>6}  {'Humid':>5}  {'Wind':>8}  {'Temp':>6}")
        for h in weather["hours"]:
            print(f"{h['label']:>6}  {h['cloud_cover']:>5}%  {h['humidity']:>4}%  "
                  f"{h['wind_mph']:>4.1f} mph  {h['temperature_f']:>4.0f}°F")
    else:
        print("Failed to fetch weather")
