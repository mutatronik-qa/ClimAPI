"""
Open-Meteo Source Implementation
Primary source: FREE, no API key required.
Implements WeatherSource interface (Strategy Pattern).
"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from core import WeatherSource, WeatherData

logger = logging.getLogger(__name__)


class OpenMeteoSource(WeatherSource):
    """
    Open-Meteo weather data source.
    API Documentation: https://open-meteo.com/en/docs
    """
    
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    HISTORICAL_URL = "https://archive-api.open-meteo.com/v1/archive"
    
    def __init__(self):
        super().__init__()
        self._client = httpx.Client(timeout=10.0)
    
    @property
    def name(self) -> str:
        return "open-meteo"
    
    @property
    def is_free(self) -> bool:
        return True
    
    @property
    def base_url(self) -> str:
        return self.FORECAST_URL
    
    def fetch_current(self, lat: float, lon: float, **kwargs) -> WeatherData:
        """Fetch current weather data."""
        timezone = kwargs.get("timezone", "America/Bogota")
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "forecast_days": 2
        }
        
        try:
            response = self._client.get(self.FORECAST_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            if not times:
                return self._create_weather_data({
                    "timestamp": datetime.now(),
                    "source": self.name
                })
            
            # Get latest valid entry
            idx = -1
            for i in range(len(times) - 1, -1, -1):
                temp = self._safe_get(hourly.get("temperature_2m", []), i)
                if temp is not None:
                    idx = i
                    break
            
            if idx < 0:
                return self._create_weather_data({
                    "timestamp": datetime.now(),
                    "source": self.name
                })
            
            return self._create_weather_data({
                "timestamp": datetime.fromisoformat(times[idx]),
                "temperature": self._safe_get(hourly.get("temperature_2m", []), idx),
                "humidity": self._safe_get(hourly.get("relative_humidity_2m", []), idx),
                "precipitation": self._safe_get(hourly.get("precipitation", []), idx),
                "wind_speed": self._safe_get(hourly.get("wind_speed_10m", []), idx),
                "source": self.name
            })
            
        except Exception as e:
            logger.error(f"Open-Meteo fetch_current error: {e}")
            return self._create_weather_data({
                "timestamp": datetime.now(),
                "source": self.name,
                "error": str(e)
            })
    
    def fetch_forecast(self, lat: float, lon: float, days: int = 7, **kwargs) -> List[WeatherData]:
        """Fetch weather forecast."""
        timezone = kwargs.get("timezone", "America/Bogota")
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "timezone": timezone,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "forecast_days": min(days, 16)
        }
        
        try:
            response = self._client.get(self.FORECAST_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            results = []
            for i, time_str in enumerate(times):
                results.append(self._create_weather_data({
                    "timestamp": datetime.fromisoformat(time_str),
                    "temperature": self._safe_get(hourly.get("temperature_2m", []), i),
                    "humidity": self._safe_get(hourly.get("relative_humidity_2m", []), i),
                    "precipitation": self._safe_get(hourly.get("precipitation", []), i),
                    "wind_speed": self._safe_get(hourly.get("wind_speed_10m", []), i),
                    "source": self.name
                }))
            
            return results
            
        except Exception as e:
            logger.error(f"Open-Meteo fetch_forecast error: {e}")
            return []
    
    def fetch_historical(self, lat: float, lon: float, start_date: datetime, end_date: datetime, **kwargs) -> List[WeatherData]:
        """Fetch historical data."""
        timezone = kwargs.get("timezone", "America/Bogota")
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "timezone": timezone,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        }
        
        try:
            response = self._client.get(self.HISTORICAL_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            results = []
            for i, time_str in enumerate(times):
                results.append(self._create_weather_data({
                    "timestamp": datetime.fromisoformat(time_str),
                    "temperature": self._safe_get(hourly.get("temperature_2m", []), i),
                    "humidity": self._safe_get(hourly.get("relative_humidity_2m", []), i),
                    "precipitation": self._safe_get(hourly.get("precipitation", []), i),
                    "wind_speed": self._safe_get(hourly.get("wind_speed_10m", []), i),
                    "source": self.name
                }))
            
            return results
            
        except Exception as e:
            logger.error(f"Open-Meteo fetch_historical error: {e}")
            return []
    
    def health_check(self) -> bool:
        """Check if Open-Meteo API is available."""
        try:
            response = self._client.get(
                self.FORECAST_URL,
                params={"latitude": 6.244, "longitude": -75.581, "forecast_days": 1}
            )
            return response.status_code == 200
        except Exception:
            return False
    
    @staticmethod
    def _safe_get(arr: list, idx: int) -> float | None:
        """Safely get float from list."""
        try:
            if idx >= len(arr) or arr is None:
                return None
            val = arr[idx]
            return float(val) if val is not None else None
        except (ValueError, TypeError, IndexError):
            return None
    
    def close(self):
        """Close HTTP client."""
        self._client.close()