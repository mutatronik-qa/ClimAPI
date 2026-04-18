"""
Cliente sync para OpenWeatherMap (normaliza salida).
"""
from typing import Dict, Any
from datetime import datetime
import requests
import logging

logger = logging.getLogger(__name__)

class OpenWeatherMap:
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.api_key = self.config.get("api_key")
        self.base_url = self.config.get("base_url", "https://api.openweathermap.org/data/2.5/")
        self.units = self.config.get("units", "metric")

    def get_weather_data(self, location: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("API key de OpenWeatherMap no configurada")
        params = {"q": location, "appid": self.api_key, "units": self.units, "lang": "es"}
        try:
            r = requests.get(f"{self.base_url.rstrip('/')}/weather", params=params, timeout=10)
            r.raise_for_status()
            raw = r.json()
            main = raw.get("main", {})
            weather = raw.get("weather", [{}])
            wind = raw.get("wind", {})
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "temperature": main.get("temp"),
                "humidity": main.get("humidity"),
                "description": weather[0].get("description") if weather else None,
                "wind_speed": wind.get("speed"),
                "location": raw.get("name"),
                "raw": raw
            }
        except requests.RequestException as e:
            logger.error(f"OpenWeatherMap request error: {e}")
            raise