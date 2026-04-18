"""Open-Meteo weather data source adapter."""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional

from domain.entities.weather import WeatherData, WeatherSourceInfo
from domain.interfaces.sources import WeatherDataSource

logger = logging.getLogger(__name__)


class OpenMeteoAdapter(WeatherDataSource):
    """
    Adapter for Open-Meteo API (free, no API key required).
    
    API Documentation: https://open-meteo.com/en/docs
    """
    
    def __init__(
        self,
        base_url: str = "https://api.open-meteo.com/v1/forecast",
        timeout: int = 10
    ):
        self._base_url = base_url
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    @property
    def name(self) -> str:
        return "open-meteo"
    
    @property
    def info(self) -> WeatherSourceInfo:
        return WeatherSourceInfo(
            name="open-meteo",
            display_name="Open-Meteo",
            requires_api_key=False,
            is_free=True,
            base_url="https://open-meteo.com",
            documentation_url="https://open-meteo.com/en/docs"
        )
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def fetch_current(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """Fetch current weather data from Open-Meteo."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "forecast_days": 2
        }
        
        client = await self._get_client()
        
        try:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_hourly_data(data, source="open-meteo")
            
        except httpx.HTTPError as e:
            logger.error(f"Open-Meteo HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Open-Meteo error: {e}")
            raise
    
    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """Fetch forecast data from Open-Meteo."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "forecast_days": min(days, 16)
        }
        
        client = await self._get_client()
        
        try:
            response = await client.get(self._base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_hourly_data(data, source="open-meteo-forecast")
            
        except httpx.HTTPError as e:
            logger.error(f"Open-Meteo forecast error: {e}")
            raise
    
    async def fetch_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """Fetch historical data from Open-Meteo."""
        historical_url = "https://archive-api.open-meteo.com/v1/archive"
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "timezone": timezone,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        }
        
        client = await self._get_client()
        
        try:
            response = await client.get(historical_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return self._parse_hourly_data(data, source="open-meteo-historical")
            
        except httpx.HTTPError as e:
            logger.error(f"Open-Meteo historical error: {e}")
            raise
    
    def _parse_hourly_data(self, data: dict, source: str) -> list[WeatherData]:
        """Parse Open-Meteo hourly response into WeatherData objects."""
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        
        result = []
        
        for i, time_str in enumerate(times):
            try:
                timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                
                temp = hourly.get("temperature_2m", [])
                humidity = hourly.get("relative_humidity_2m", [])
                precipitation = hourly.get("precipitation", [])
                wind_speed = hourly.get("wind_speed_10m", [])
                
                weather_data = WeatherData(
                    timestamp=timestamp,
                    temperature=self._safe_get_float(temp, i),
                    humidity=self._safe_get_float(humidity, i),
                    precipitation=self._safe_get_float(precipitation, i),
                    wind_speed=self._safe_get_float(wind_speed, i),
                    source=source
                )
                result.append(weather_data)
                
            except (ValueError, IndexError) as e:
                logger.debug(f"Skipping invalid data point: {e}")
                continue
        
        return result
    
    def _safe_get_float(self, arr: list, index: int) -> Optional[float]:
        """Safely get float value from array, handling None/missing values."""
        try:
            if index >= len(arr):
                return None
            val = arr[index]
            if val is None:
                return None
            return float(val)
        except (ValueError, TypeError):
            return None
    
    async def health_check(self) -> bool:
        """Check if Open-Meteo API is available."""
        try:
            client = await self._get_client()
            response = await client.get(
                self._base_url,
                params={"latitude": 6.244, "longitude": -75.581, "forecast_days": 1}
            )
            return response.status_code == 200
        except Exception:
            return False


# Factory function for creating the adapter
def create_open_meteo_adapter(config: Optional[dict] = None) -> OpenMeteoAdapter:
    """Factory to create Open-Meteo adapter with optional config."""
    if config is None:
        config = {}
    
    return OpenMeteoAdapter(
        base_url=config.get("base_url", "https://api.open-meteo.com/v1/forecast"),
        timeout=config.get("timeout", 10)
    )