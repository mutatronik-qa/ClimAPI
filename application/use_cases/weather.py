"""Get current weather use case."""
from datetime import datetime
from typing import Optional
import asyncio

from domain.entities.weather import WeatherData, Location, WeatherRecord
from domain.interfaces.sources import WeatherDataSource, CacheProvider


class GetCurrentWeather:
    """
    Use case for fetching current weather data.
    
    Responsibilities:
    - Orchestrate data fetching from source
    - Handle caching
    - Return normalized data
    """
    
    def __init__(
        self,
        source: WeatherDataSource,
        cache: Optional[CacheProvider] = None
    ):
        self.source = source
        self.cache = cache
    
    async def execute(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "America/Bogota",
        force_refresh: bool = False
    ) -> WeatherRecord:
        """
        Execute the use case.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            timezone: Timezone for data
            force_refresh: Skip cache and fetch fresh data
            
        Returns:
            WeatherRecord with current weather data
        """
        cache_key = f"current:{source.name}:{latitude}:{longitude}:{timezone}"
        
        # Try cache first
        if not force_refresh and self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        # Fetch from source
        data = await self.source.fetch_current(latitude, longitude, timezone)
        
        location = Location(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone
        )
        
        record = WeatherRecord(
            location=location,
            data=data,
            source=self.source.name,
            fetched_at=datetime.now()
        )
        
        # Store in cache
        if self.cache:
            await self.cache.set(cache_key, record, ttl_seconds=900)
        
        return record


class GetForecast:
    """Use case for fetching weather forecast."""
    
    def __init__(
        self,
        source: WeatherDataSource,
        cache: Optional[CacheProvider] = None
    ):
        self.source = source
        self.cache = cache
    
    async def execute(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        timezone: str = "America/Bogota"
    ) -> WeatherRecord:
        """Execute forecast fetch."""
        cache_key = f"forecast:{self.source.name}:{latitude}:{longitude}:{days}:{timezone}"
        
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        data = await self.source.fetch_forecast(latitude, longitude, days, timezone)
        
        location = Location(latitude=latitude, longitude=longitude, timezone=timezone)
        
        record = WeatherRecord(
            location=location,
            data=data,
            source=self.source.name,
            fetched_at=datetime.now()
        )
        
        if self.cache:
            await self.cache.set(cache_key, record, ttl_seconds=3600)
        
        return record


class GetHistoricalWeather:
    """Use case for fetching historical weather data."""
    
    def __init__(
        self,
        source: WeatherDataSource,
        cache: Optional[CacheProvider] = None
    ):
        self.source = source
        self.cache = cache
    
    async def execute(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        timezone: str = "America/Bogota"
    ) -> WeatherRecord:
        """Execute historical data fetch."""
        cache_key = f"historical:{self.source.name}:{latitude}:{longitude}:{start_date.isoformat()}:{end_date.isoformat()}"
        
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        data = await self.source.fetch_historical(
            latitude, longitude, start_date, end_date, timezone
        )
        
        location = Location(latitude=latitude, longitude=longitude, timezone=timezone)
        
        record = WeatherRecord(
            location=location,
            data=data,
            source=self.source.name,
            fetched_at=datetime.now()
        )
        
        if self.cache:
            await self.cache.set(cache_key, record, ttl_seconds=86400)
        
        return record