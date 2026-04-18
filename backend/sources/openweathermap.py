"""
OpenWeatherMap Source - Optional (requires API key)
https://openweathermap.org/api
"""
import os
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openweathermap.org/data/2.5"


def get_weather(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """
    Get current weather from OpenWeatherMap.
    Requires API key in OPENWEATHER_API_KEY env var.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    
    if not api_key:
        return _empty_result("openweathermap", "API key not configured")
    
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "units": "metric",
        "lang": "es"
    }
    
    try:
        logger.info(f"🌐 OpenWeatherMap: fetching for {lat}, {lon}")
        
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{BASE_URL}/weather", params=params)
            response.raise_for_status()
            data = response.json()
        
        main = data.get("main", {})
        wind = data.get("wind", {})
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "temperature": main.get("temp"),
            "humidity": main.get("humidity"),
            "precipitation": data.get("rain", {}).get("1h", 0) or data.get("rain", {}).get("1h", 0),
            "wind_speed": wind.get("speed", 0) * 3.6,  # m/s to km/h
            "source": "openweathermap"
        }
        
        logger.info(f"✅ OpenWeatherMap: success")
        return result
        
    except httpx.HTTPError as e:
        logger.warning(f"⚠️ OpenWeatherMap HTTP error: {e}")
        return _empty_result("openweathermap", str(e))
    except Exception as e:
        logger.warning(f"⚠️ OpenWeatherMap error: {e}")
        return _empty_result("openweathermap", str(e))


def _empty_result(source: str, error: str = "") -> Dict[str, Any]:
    """Return empty result."""
    return {
        "timestamp": datetime.now().isoformat(),
        "temperature": None,
        "humidity": None,
        "precipitation": None,
        "wind_speed": None,
        "source": source,
        "error": error if error else "no data"
    }