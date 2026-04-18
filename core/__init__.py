"""
CORE - Base Classes and Interfaces
Strategy Pattern: Abstract base for all weather sources.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================
# Domain Models
# ============================================

class WeatherData(BaseModel):
    """Standardized weather data model."""
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    source: str
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Location(BaseModel):
    """Geographic location."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"
    name: Optional[str] = None


class SourceStatus(BaseModel):
    """Status of a weather source."""
    name: str
    is_available: bool
    response_time: float
    error: Optional[str] = None


# ============================================
# Strategy Pattern - Abstract Weather Source
# ============================================

class WeatherSource(ABC):
    """
    Abstract base class for all weather data sources.
    Strategy Pattern: Each source implements this interface.
    """
    
    def __init__(self):
        self._name = self.__class__.__name__.replace("Source", "").lower()
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this source."""
        pass
    
    @property
    @abstractmethod
    def is_free(self) -> bool:
        """Whether this source requires API key."""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the API."""
        pass
    
    @abstractmethod
    def fetch_current(self, lat: float, lon: float, **kwargs) -> WeatherData:
        """Fetch current weather data."""
        pass
    
    @abstractmethod
    def fetch_forecast(self, lat: float, lon: float, days: int = 7, **kwargs) -> List[WeatherData]:
        """Fetch weather forecast."""
        pass
    
    @abstractmethod
    def fetch_historical(self, lat: float, lon: float, start_date: datetime, end_date: datetime, **kwargs) -> List[WeatherData]:
        """Fetch historical data."""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if source is available."""
        pass
    
    def _create_weather_data(self, data: Dict[str, Any]) -> WeatherData:
        """Helper to create WeatherData from dict."""
        return WeatherData(
            timestamp=data.get("timestamp", datetime.now()),
            temperature=data.get("temperature"),
            humidity=data.get("humidity"),
            precipitation=data.get("precipitation"),
            wind_speed=data.get("wind_speed"),
            source=self.name
        )


# ============================================
# Cache Provider Interface
# ============================================

class CacheProvider(ABC):
    """Abstract cache provider."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 900) -> None:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        pass
    
    @abstractmethod
    def clear(self) -> None:
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        pass


# ============================================
# Re-export for convenience
# ============================================

__all__ = [
    "WeatherData",
    "Location", 
    "SourceStatus",
    "WeatherSource",
    "CacheProvider",
]