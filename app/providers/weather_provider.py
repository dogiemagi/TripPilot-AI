from typing import Any
import httpx
from .base import WeatherProvider


CITY_COORDINATES = {
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bangalore": (12.9716, 77.5946),
    "goa": (15.2993, 74.1240),
    "paris": (48.8566, 2.3522),
    "dubai": (25.2048, 55.2708),
}


class OpenMeteoWeatherProvider(WeatherProvider):
    async def get_forecast(self, city: str, date: str | None = None) -> dict[str, Any]:
        norm_city = city.strip().lower()
        lat, lon = CITY_COORDINATES.get(norm_city, (17.3850, 78.4867))
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto"
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    curr = data.get("current", {})
                    temp = curr.get("temperature_2m", 28.0)
                    humidity = curr.get("relative_humidity_2m", 55)
                    return {
                        "city": city.title(),
                        "temperature_celsius": temp,
                        "humidity_percent": humidity,
                        "condition": "Clear and pleasant" if temp < 32 else "Warm and sunny",
                        "packing_tips": "Light breathable cottons, sunglasses, and comfortable walking shoes.",
                        "is_live": True,
                        "source": "open-meteo-api",
                    }
        except Exception:
            pass

        # Fallback deterministic weather
        return {
            "city": city.title(),
            "temperature_celsius": 29.0,
            "humidity_percent": 60,
            "condition": "Partly cloudy with pleasant evening breeze",
            "packing_tips": "Light cotton clothing, sunscreen, and hydration gear.",
            "is_live": False,
            "source": "deterministic_weather_estimator",
        }
