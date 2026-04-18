"""
MeteoBlue Source - Optional (requires API key)
https://www.meteoblue.com/
"""
import os
import httpx
import logging
import hmac
import hashlib
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://my.meteoblue.com"


def get_weather(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """
    Get current weather from MeteoBlue.
    Requires METEOBLUE_API_KEY and METEOBLUE_SHARED_SECRET in env.
    """
    api_key = os.getenv("METEOBLUE_API_KEY")
    shared_secret = os.getenv("METEOBLUE_SHARED_SECRET")
    
    if not api_key:
        return _empty_result("meteoblue", "API key not configured")
    
    params = {
        "lat": lat,
        "lon": lon,
        "apikey": api_key,
        "format": "json"
    }
    
    # Sign request if secret provided
    if shared_secret:
        query = urllib.parse.urlencode(params)
        path = f"/packages/basic-1h?{query}"
        sig = hmac.new(shared_secret.encode(), path.encode(), hashlib.sha256).hexdigest()
        url = f"{BASE_URL}{path}&sig={sig}"
    else:
        url = f"{BASE_URL}/packages/basic-1h"
        params["asl"] = kwargs.get("asl", 1500)
        for k, v in params.items():
            url += f"&{k}={v}"
    
    try:
        logger.info(f"🌐 MeteoBlue: fetching for {lat}, {lon}")
        
        with httpx.Client(timeout=12) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        
        # Parse response - look for current conditions
        # MeteoBlue returns hourly data, get first entry
        hours = data.get("hours", [])
        
        if not hours:
            return _empty_result("meteoblue", "no data in response")
        
        current = hours[0]
        
        result = {
            "timestamp": current.get("time", datetime.now().isoformat()),
            "temperature": current.get("temperature") or current.get("temp"),
            "humidity": current.get("humidity"),
            "precipitation": current.get("precipitation") or 0,
            "wind_speed": current.get("wind_speed") or 0,
            "source": "meteoblue"
        }
        
        logger.info(f"✅ MeteoBlue: success")
        return result
        
    except httpx.HTTPError as e:
        logger.warning(f"⚠️ MeteoBlue HTTP error: {e}")
        return _empty_result("meteoblue", str(e))
    except Exception as e:
        logger.warning(f"⚠️ MeteoBlue error: {e}")
        return _empty_result("meteoblue", str(e))


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