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
        timeout = kwargs.get("timeout", 10)
        with httpx.Client(timeout=timeout) as client:
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
        timeout = kwargs.get("timeout", 10)
        with httpx.Client(timeout=timeout) as client:
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
# MeteoSource (Requires API Key)
# ====================

def get_weather_meteosource(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """MeteoSource - requires API key from environment."""
    api_key = os.getenv("METEOSOURCE_API_KEY")

    if not api_key:
        return _result({}, "meteosource", "API key not set")

    url = "https://www.meteosource.com/api/v1/free/point"
    params = {
        "key": api_key,
        "units": kwargs.get("units", "metric")
    }

    # Support both place_id and lat/lon coordinates
    if kwargs.get("place_id"):
        params["place_id"] = kwargs["place_id"]
    else:
        params["lat"] = lat
        params["lon"] = lon

    try:
        timeout = kwargs.get("timeout", 15)
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        current = data.get("current", {})
        return _result({
            "timestamp": current.get("time", datetime.now().isoformat()),
            "temperature": current.get("temperature"),
            "humidity": current.get("humidity"),
            "precipitation": current.get("precipitation", 0),
            "wind_speed": current.get("wind_speed"),
        }, "meteosource")

    except Exception as e:
        logger.warning(f"MeteoSource failed: {e}")
        return _result({}, "meteosource", str(e))


import hmac
import hashlib
from urllib.parse import quote

def _sign_meteoblue_query(query: str, secret: str) -> str:
    """Signs a Meteoblue query using HMAC SHA256."""
    sig = hmac.new(
        secret.encode(),
        query.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{query}&sig={sig}"

# ====================
# MeteoBlue (Requires API Key)
# ====================

def get_weather_meteoblue(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """MeteoBlue - requires API key."""
    api_key = os.getenv("METEOBLUE_API_KEY")
    
    if not api_key:
        return _result({}, "meteoblue", "API key not set")
    
    asl = kwargs.get("asl", 1405)
    secret = os.getenv("METEOBLUE_SHARED_SECRET") or os.getenv("shared_secret")
    
    # Base query path and params
    package = "basic-15min_basic-3h_current_clouds-1h_sunmoon_moonlight-30min"
    query = f"/packages/{package}?apikey={api_key}&lat={lat}&lon={lon}&asl={asl}&format=json"
    
    # If secret is provided, sign the query for maximum security
    if secret:
        full_query = _sign_meteoblue_query(query, secret)
        url = f"https://my.meteoblue.com{full_query}"
    else:
        # Fallback to secret_share if no secret for HMAC is found
        url = f"https://my.meteoblue.com{query}&secret_share=climapi"
    
    try:
        timeout = kwargs.get("timeout", 15)
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        
        hours = data.get("hours", [])
        if not hours:
            return _result({}, "meteoblue", "no data")
        
        current = hours[0]
        # Ensure we return numeric values or None
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
    """SIATA - Medellín local source via web scraping.
    Note: SIATA provides data for the Aburrá Valley region.
    """
    url = os.getenv("SIATA_METEOROLOGIA_URL", "https://www.siata.gov.co/operacional/Meteorologia/")
    logger.info(f"Accessing SIATA regional directory: {url}")

    try:
        timeout = kwargs.get("timeout", 15)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            html = response.text
            
        # If we can see directory listing or specific categories, it's working
        if "Meteorologia" in html or "Temperatura" in html or "Humedad" in html or "parent directory" in html.lower():
            return _result({
                "timestamp": datetime.now().isoformat(),
                "note": "SIATA Operational directory accessible",
                "url": url,
                "status": "online"
            }, "siata")
            
        return _result({}, "siata", "directory structure not recognized")

    except Exception as e:
        logger.warning(f"SIATA lookup failed: {e}")
        return _result({}, "siata", str(e))


# ====================
# IDEAM Radar (Optional)
# ====================

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    boto3 = None
    Config = None
    UNSIGNED = None
    BOTO3_AVAILABLE = False


def get_weather_radar(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """IDEAM Radar - AWS S3 public bucket.
    Returns general status of the radar network and available files.
    """
    bucket_name = os.getenv("IDEAM_RADAR_BUCKET", "s3-radaresideam")
    prefix = kwargs.get("prefix", "")
    
    # Known radar locations
    RADAR_SITES = {
        "Barrancabermeja": {"lat": 7.0, "lon": -73.8},
        "Guaviare": {"lat": 2.5, "lon": -72.6},
        "Munchique": {"lat": 2.5, "lon": -76.9},
        "Carimagua": {"lat": 4.5, "lon": -71.3}
    }

    if not BOTO3_AVAILABLE:
        return _result({}, "ideam_radar", "boto3 is not installed")

    try:
        s3 = boto3.client(
            "s3",
            config=Config(signature_version=UNSIGNED)
        )

        paginator = s3.get_paginator("list_objects_v2")
        max_items = kwargs.get("max_items", 100)
        page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix, PaginationConfig={'MaxItems': max_items})

        files = []
        for page in page_iterator:
            for obj in page.get("Contents", []):
                files.append(obj.get("Key"))

        files_count = len(files)
        sample = files[:5]
        
        return _result({
            "timestamp": datetime.now().isoformat(),
            "temperature": None,
            "humidity": None,
            "precipitation": None,
            "wind_speed": None,
            "note": f"Radar network status: {files_count} files available",
            "files_count": files_count,
            "radar_sites": RADAR_SITES,
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
    "meteosource": get_weather_meteosource,
    "meteoblue": get_weather_meteoblue,
    "siata": get_weather_siata,
    "ideam-radar": get_weather_radar,
}

# Priority order for merging (first valid wins)
PRIORITY = ["open-meteo", "openweathermap", "meteosource", "meteoblue", "siata", "ideam-radar"]


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
        if arr is None or idx >= len(arr):
            return None
        val = arr[idx]
        return float(val) if val is not None else None
    except (ValueError, TypeError, IndexError):
        return None


def _find_html_value(html: str, pattern: str) -> Optional[float]:
    """Extract a numeric weather value from SIATA HTML."""
    match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    try:
        return float(match.group(1))
    except (ValueError, TypeError):
        return None