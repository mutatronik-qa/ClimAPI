"""
Weather Sources - ALL in one file.
Each function returns the same standardized schema.
"""
import httpx
import os
import re
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ====================
# Common Schema
# ====================
# All functions return:
# {
#     "timestamp": str,
#     "temperature": float | None,
#     "humidity": float | None,
#     "precipitation": float | None,
#     "wind_speed": float | None,
#     "source": str,
#     "error": str | None
# }

def _result(data: Dict[str, Any], source: str, error: str = None) -> Dict[str, Any]:
    """Create standardized result."""
    return {
        "timestamp": data.get("timestamp", datetime.now().isoformat()),
        "temperature": data.get("temperature"),
        "humidity": data.get("humidity"),
        "precipitation": data.get("precipitation"),
        "wind_speed": data.get("wind_speed"),
        "source": source,
        "error": error
    }


# ====================
# Open-Meteo (PRIMARY - FREE)
# ====================

def get_weather_open_meteo(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """Open-Meteo - No API key required."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": kwargs.get("timezone", "America/Bogota"),
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "forecast_days": 2
    }
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        if not times:
            return _result({}, "open-meteo", "no data")
        
        # Get last valid entry
        idx = len(times) - 1
        for i in range(len(times) - 1, -1, -1):
            temp = _safe_get(hourly.get("temperature_2m", []), i)
            if temp is not None:
                idx = i
                break
        
        return _result({
            "timestamp": times[idx],
            "temperature": _safe_get(hourly.get("temperature_2m", []), idx),
            "humidity": _safe_get(hourly.get("relative_humidity_2m", []), idx),
            "precipitation": _safe_get(hourly.get("precipitation", []), idx),
            "wind_speed": _safe_get(hourly.get("wind_speed_10m", []), idx),
        }, "open-meteo")
        
    except Exception as e:
        logger.warning(f"Open-Meteo failed: {e}")
        return _result({}, "open-meteo", str(e))


# ====================
# OpenWeatherMap (Requires API Key)
# ====================

def get_weather_openweathermap(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """OpenWeatherMap - requires API key from environment."""
    api_key = os.getenv("OPENWEATHER_API_KEY") or os.getenv("OPENWEATHERMAP_API_KEY")
    
    if not api_key:
        return _result({}, "openweathermap", "API key not set")
    
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        
        main = data.get("main", {})
        wind = data.get("wind", {})
        rain = data.get("rain", {})
        
        return _result({
            "timestamp": datetime.now().isoformat(),
            "temperature": main.get("temp"),
            "humidity": main.get("humidity"),
            "precipitation": rain.get("1h", 0),
            "wind_speed": (wind.get("speed", 0) * 3.6),
        }, "openweathermap")
        
    except Exception as e:
        logger.warning(f"OpenWeatherMap failed: {e}")
        return _result({}, "openweathermap", str(e))


# ====================
# MeteoBlue (Requires API Key)
# ====================

def get_weather_meteoblue(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """MeteoBlue - requires API key."""
    api_key = os.getenv("METEOBLUE_API_KEY")
    
    if not api_key:
        return _result({}, "meteoblue", "API key not set")
    
    asl = kwargs.get("asl", 1405)
    url = (
        "https://my.meteoblue.com/packages/basic-15min_basic-3h_current_clouds-1h_sunmoon_moonlight-30min"
        f"?apikey={api_key}&lat={lat}&lon={lon}&asl={asl}&format=json&secret_share=climapi"
    )
    
    try:
        with httpx.Client(timeout=15) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        
        hours = data.get("hours", [])
        if not hours:
            return _result({}, "meteoblue", "no data")
        
        current = hours[0]
        return _result({
            "timestamp": current.get("time", datetime.now().isoformat()),
            "temperature": current.get("temperature"),
            "humidity": current.get("humidity"),
            "precipitation": current.get("precipitation"),
            "wind_speed": current.get("wind_speed"),
        }, "meteoblue")
        
    except Exception as e:
        logger.warning(f"MeteoBlue failed: {e}")
        return _result({}, "meteoblue", str(e))


# ====================
# SIATA (Local - Medellín)
# ====================

def get_weather_siata(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """SIATA - Medellín local source via web scraping."""
    url = os.getenv("SIATA_OPERACIONAL_URL", "https://www.siata.gov.co/operacional/#")

    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text

        temperature = _find_html_value(html, r"Temperatura[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)")
        humidity = _find_html_value(html, r"Humedad[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)")
        precipitation = _find_html_value(html, r"Precipaci[oó]n[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)")
        wind_speed = _find_html_value(html, r"Viento[^0-9\n\r]{0,30}([0-9]+(?:\.[0-9]+)?)")

        note = "SIATA scraped page"
        error = None if (temperature or humidity or precipitation or wind_speed) else "scrape incomplete"

        return _result({
            "timestamp": datetime.now().isoformat(),
            "temperature": temperature,
            "humidity": humidity,
            "precipitation": precipitation,
            "wind_speed": wind_speed,
            "note": note
        }, "siata", error)

    except Exception as e:
        logger.warning(f"SIATA scraping failed: {e}")
        return _result({}, "siata", str(e))


# ====================
# IDEAM Radar (Optional)
# ====================

def get_weather_radar(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """IDEAM Radar - AWS S3 public bucket."""
    cmd = [
        "aws",
        "s3",
        "ls",
        "--no-sign-request",
        "s3://s3-radaresideam/"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "AWS CLI error")

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        sample = lines[:5]
        files_count = len(lines)
        note = f"Radar index found: {files_count} objects"

        return _result({
            "timestamp": datetime.now().isoformat(),
            "temperature": None,
            "humidity": None,
            "precipitation": None,
            "wind_speed": None,
            "note": note,
            "files_count": files_count,
            "sample_files": sample
        }, "ideam_radar", None if files_count else "no radar objects found")

    except Exception as e:
        logger.warning(f"IDEAM radar lookup failed: {e}")
        return _result({}, "ideam_radar", str(e))


# ====================
# Registry
# ====================

SOURCES = {
    "open-meteo": get_weather_open_meteo,
    "openweathermap": get_weather_openweathermap,
    "meteoblue": get_weather_meteoblue,
    "siata": get_weather_siata,
    "ideam-radar": get_weather_radar,
}

# Priority order for merging (first valid wins)
PRIORITY = ["open-meteo", "openweathermap", "meteoblue", "siata", "ideam-radar"]


def get_source(name: str):
    """Get source function by name."""
    return SOURCES.get(name)


def list_sources() -> list:
    """List all available sources."""
    return list(SOURCES.keys())


# ====================
# Helpers
# ====================

def _safe_get(arr: list, idx: int) -> Optional[float]:
    """Safely get float from list."""
    try:
        if idx >= len(arr) or arr is None:
            return None
        val = arr[idx]
        return float(val) if val is not None else None
    except (ValueError, TypeError, IndexError):
        return None