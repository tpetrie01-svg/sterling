# weather.py
import logging
import re
import requests

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_WORDS = (
    "weather", "forecast", "temperature outside", "how hot", "how cold",
    "is it raining", "is it snowing", "humidity", "wind speed",
)

LOCATION_RE = re.compile(
    r"\b(?:weather|forecast|temperature)\b.*?\b(?:in|for|at)\s+([A-Za-z][A-Za-z\s,.'-]*)",
    re.IGNORECASE,
)

# WMO weather codes -> plain-English condition
WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    56: "light freezing drizzle", 57: "dense freezing drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    66: "light freezing rain", 67: "heavy freezing rain",
    71: "slight snow fall", 73: "moderate snow fall", 75: "heavy snow fall",
    77: "snow grains",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    85: "slight snow showers", 86: "heavy snow showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


def needs_weather(prompt: str) -> bool:
    p = prompt.lower()
    return any(w in p for w in WEATHER_WORDS)


def _extract_location(prompt: str) -> str | None:
    m = LOCATION_RE.search(prompt)
    if not m:
        return None
    loc = m.group(1).strip(" .,'\"")
    return loc or None


def get_weather(prompt: str) -> tuple[str, str | None]:
    """Look up current weather via Open-Meteo.

    Returns (context, error) mirroring search.web_search: on success `error`
    is None and `context` holds a formatted summary for the LLM. On failure
    `context` is "" and `error` is a short human-readable reason.
    """
    location = _extract_location(prompt)
    if not location:
        return "", "no location was given, so ask the user which city they mean"

    try:
        geo = requests.get(GEOCODE_URL, params={"name": location, "count": 1}, timeout=5)
        geo.raise_for_status()
        results = geo.json().get("results")
    except requests.RequestException:
        logger.exception("weather geocoding failed for location: %r", location)
        return "", "the weather lookup failed"

    if not results:
        return "", f"couldn't find a location matching '{location}'"

    place = results[0]
    lat, lon = place["latitude"], place["longitude"]
    label = ", ".join(filter(None, [place.get("name"), place.get("admin1"), place.get("country")]))

    try:
        fc = requests.get(FORECAST_URL, params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "timezone": "auto",
            "forecast_days": 1,
        }, timeout=5)
        fc.raise_for_status()
        data = fc.json()
    except requests.RequestException:
        logger.exception("weather forecast fetch failed for %s,%s", lat, lon)
        return "", "the weather lookup failed"

    cur = data.get("current", {})
    daily = data.get("daily", {})
    condition = WEATHER_CODES.get(cur.get("weather_code"), "unknown conditions")

    lines = [
        f"Current weather in {label}: {condition}, {cur.get('temperature_2m')}°F "
        f"(feels like {cur.get('apparent_temperature')}°F), "
        f"humidity {cur.get('relative_humidity_2m')}%, "
        f"wind {cur.get('wind_speed_10m')} mph, "
        f"precipitation {cur.get('precipitation')} in."
    ]
    if daily.get("temperature_2m_max"):
        lines.append(
            f"Today's high {daily['temperature_2m_max'][0]}°F, "
            f"low {daily['temperature_2m_min'][0]}°F."
        )
    return "\n".join(lines), None
