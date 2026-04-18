from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional
from domain.entities.weather import WeatherData, Location, WeatherSourceInfo


class WeatherDataSource(ABC):
    """Abstract interface for weather data sources (ports)."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this source."""
        pass
    
    @property
    @abstractmethod
    def info(self) -> WeatherSourceInfo:
        """Metadata about this source."""
        pass
    
    @abstractmethod
    async def fetch_current(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """
        Fetch current weather data.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            timezone: Timezone for data
            
        Returns:
            List of WeatherData objects
        """
        pass
    
    @abstractmethod
    async def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """
        Fetch weather forecast.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            days: Number of days to forecast (max 16)
            timezone: Timezone for data
            
        Returns:
            List of WeatherData objects
        """
        pass
    
    @abstractmethod
    async def fetch_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """
        Fetch historical weather data.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            start_date: Start date for historical data
            end_date: End date for historical data
            timezone: Timezone for data
            
        Returns:
            List of WeatherData objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if source is available."""
        pass


class CacheProvider(ABC):
    """Abstract interface for caching (port)."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: any, ttl_seconds: int) -> None:
        """Set value in cache with TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache."""
        pass
    
    @abstractmethod
    def get_stats(self) -> dict:
        """Get cache statistics."""
        pass


class DataProcessor(ABC):
    """Abstract interface for data processing (port)."""
    
    @abstractmethod
    def normalize(self, raw_data: dict, source: str) -> list[WeatherData]:
        """Normalize raw data to unified schema."""
        pass
    
    @abstractmethod
    def validate(self, data: list[WeatherData]) -> tuple[list[WeatherData], list[str]]:
        """Validate and clean data, return cleaned data and issues."""
        pass
    
    @abstractmethod
    def aggregate(
        self,
        data: list[WeatherData],
        frequency: str = "hourly"
    ) -> list[WeatherData]:
        """Aggregate data by time frequency."""
        pass


class DataStorage(ABC):
    """Abstract interface for data persistence (port)."""
    
    @abstractmethod
    async def save_raw(self, data: dict, source: str, timestamp: datetime) -> str:
        """Save raw data, return file path."""
        pass
    
    @abstractmethod
    async def save_cleaned(self, data: list[WeatherData]) -> str:
        """Save cleaned data, return file path."""
        pass
    
    @abstractmethod
    async def load_cleaned(
        self,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[WeatherData]:
        """Load cleaned data with filters."""
        pass
    
    @abstractmethod
    async def list_available_data(self) -> list[dict]:
        """List available data files."""
        pass