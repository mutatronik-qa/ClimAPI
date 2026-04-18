"""
Open-Meteo Source - Primary weather source (FREE, no API key)
https://open-meteo.com/
"""
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"


def validate_coords(lat: float, lon: float) -> None:
    """Validate coordinates."""
    if not -90 <= lat <= 90:
        raise ValueError(f"Invalid latitude: {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"Invalid longitude: {lon}")


def get_weather(lat: float, lon: float, timezone: str = "America/Bogota") -> Dict[str, Any]:
    """
    Get current weather from Open-Meteo.
    
    Returns standardized format:
    {
        "timestamp": str,
        "temperature": float,
        "humidity": float,
        "precipitation": float,
        "wind_speed": float,
        "source": str
    }
    """
    validate_coords(lat, lon)
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "forecast_days": 2
    }
    
    try:
        logger.info(f"🌐 Open-Meteo: fetching for {lat}, {lon}")
        
        with httpx.Client(timeout=10) as client:
            response = client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Parse hourly data - get latest values
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        if not times:
            return _empty_result("open-meteo")
        
        # Get last valid entry
        idx = -1
        temperature = _safe_float(hourly.get("temperature_2m", []), idx)
        
        # If last is None, find valid one
        if temperature is None:
            for i in range(len(times) - 1, -1, -1):
                temperature = _safe_float(hourly.get("temperature_2m", []), i)
                if temperature is not None:
                    idx = i
                    break
        else:
            idx = len(times) - 1
        
        if idx < 0:
            return _empty_result("open-meteo")
        
        result = {
            "timestamp": times[idx] if idx < len(times) else datetime.now().isoformat(),
            "temperature": _safe_float(hourly.get("temperature_2m", []), idx),
            "humidity": _safe_float(hourly.get("relative_humidity_2m", []), idx),
            "precipitation": _safe_float(hourly.get("precipitation", []), idx),
            "wind_speed": _safe_float(hourly.get("wind_speed_10m", []), idx),
            "source": "open-meteo"
        }
        
        logger.info(f"✅ Open-Meteo: success")
        return result
        
    except httpx.HTTPError as e:
        logger.error(f"❌ Open-Meteo HTTP error: {e}")
        return _error_result("open-meteo", str(e))
    except Exception as e:
        logger.error(f"❌ Open-Meteo error: {e}")
        return _error_result("open-meteo", str(e))


def get_hourly_forecast(lat: float, lon: float, days: int = 2, timezone: str = "America/Bogota") -> List[Dict[str, Any]]:
    """Get hourly forecast data."""
    validate_coords(lat, lon)
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": timezone,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "forecast_days": min(days, 16)
    }
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        results = []
        for i, time_str in enumerate(times):
            results.append({
                "timestamp": time_str,
                "temperature": _safe_float(hourly.get("temperature_2m", []), i),
                "humidity": _safe_float(hourly.get("relative_humidity_2m", []), i),
                "precipitation": _safe_float(hourly.get("precipitation", []), i),
                "wind_speed": _safe_float(hourly.get("wind_speed_10m", []), i),
                "source": "open-meteo"
            })
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Open-Meteo forecast error: {e}")
        return []


def _safe_float(arr: list, idx: int) -> Optional[float]:
    """Safely get float from list."""
    try:
        if idx >= len(arr) or arr is None:
            return None
        val = arr[idx]
        if val is None:
            return None
        return float(val)
    except (ValueError, TypeError, IndexError):
        return None


def _empty_result(source: str) -> Dict[str, Any]:
    """Return empty result."""
    return {
        "timestamp": datetime.now().isoformat(),
        "temperature": None,
        "humidity": None,
        "precipitation": None,
        "wind_speed": None,
        "source": source
    }


def _error_result(source: str, error: str) -> Dict[str, Any]:
    """Return error result."""
    return {
        "timestamp": datetime.now().isoformat(),
        "temperature": None,
        "humidity": None,
        "precipitation": None,
        "wind_speed": None,
        "source": source,
        "error": error
    }