"""
SIATA Source Implementation
Local Medellín source - limited public API access.
Implements WeatherSource interface.
"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from core import WeatherSource, WeatherData

logger = logging.getLogger(__name__)


class SIATASource(WeatherSource):
    """
    SIATA (Sistema de Alerta Temprana) weather source.
    Primary location: Medellín, Colombia.
    Note: Limited public API access - uses fallback data.
    """
    
    BASE_URL = "https://www.siata.gov.co"
    
    def __init__(self):
        super().__init__()
        self._client = httpx.Client(timeout=8.0)
    
    @property
    def name(self) -> str:
        return "siata"
    
    @property
    def is_free(self) -> bool:
        return True  # Public data
    
    @property
    def base_url(self) -> str:
        return self.BASE_URL
    
    def fetch_current(self, lat: float, lon: float, **kwargs) -> WeatherData:
        """Fetch current weather from SIATA."""
        endpoints = [
            f"{self.BASE_URL}/api/v1/weather/current",
            f"{self.BASE_URL}/api/weather",
        ]
        
        for endpoint in endpoints:
            try:
                response = self._client.get(endpoint)
                if response.status_code == 200:
                    data = response.json()
                    return self._create_weather_data({
                        "timestamp": datetime.now(),
                        "temperature": data.get("temperature"),
                        "humidity": data.get("humidity"),
                        "precipitation": data.get("precipitation"),
                        "wind_speed": data.get("wind_speed"),
                        "source": self.name
                    })
            except Exception as e:
                logger.debug(f"SIATA endpoint {endpoint} failed: {e}")
                continue
        
        # Fallback: return placeholder with note
        logger.warning("SIATA API unavailable, using fallback")
        return self._create_weather_data({
            "timestamp": datetime.now(),
            "source": self.name,
            "note": "SIATA public API not available"
        })
    
    def fetch_forecast(self, lat: float, lon: float, days: int = 7, **kwargs) -> List[WeatherData]:
        """SIATA typically doesn't provide forecast - return empty."""
        return []
    
    def fetch_historical(self, lat: float, lon: float, start_date: datetime, end_date: datetime, **kwargs) -> List[WeatherData]:
        """Fetch historical data - limited availability."""
        return []
    
    def health_check(self) -> bool:
        """Check if SIATA is available."""
        try:
            response = self._client.get(f"{self.BASE_URL}", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """Close HTTP client."""
        self._client.close()