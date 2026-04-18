"""
SIATA Source - Local Medellín data
https://www.siata.gov.co/
"""
import httpx
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://www.siata.gov.co"


def get_weather(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """
    Get current weather from SIATA (Medellín).
    This is a local source, may not have public API.
    """
    try:
        logger.info(f"🌐 SIATA: fetching for {lat}, {lon}")
        
        # Try common SIATA endpoints
        endpoints = [
            f"{BASE_URL}/api/v1/weather/current",
            f"{BASE_URL}/api/weather",
        ]
        
        with httpx.Client(timeout=8) as client:
            for endpoint in endpoints:
                try:
                    response = client.get(endpoint)
                    if response.status_code == 200:
                        data = response.json()
                        return {
                            "timestamp": datetime.now().isoformat(),
                            "temperature": data.get("temperature"),
                            "humidity": data.get("humidity"),
                            "precipitation": data.get("precipitation"),
                            "wind_speed": data.get("wind_speed"),
                            "source": "siata"
                        }
                except Exception:
                    continue
        
        # If no API available, return a placeholder
        logger.info("⚠️ SIATA: no API available, using fallback")
        return _fallback_result()
        
    except Exception as e:
        logger.warning(f"⚠️ SIATA error: {e}")
        return _fallback_result()


def _fallback_result() -> Dict[str, Any]:
    """Return placeholder data when SIATA is not available."""
    # Use Open-Meteo as fallback for Medellín area
    return {
        "timestamp": datetime.now().isoformat(),
        "temperature": None,
        "humidity": None,
        "precipitation": None,
        "wind_speed": None,
        "source": "siata",
        "note": "SIATA API not publicly available, use other sources"
    }


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