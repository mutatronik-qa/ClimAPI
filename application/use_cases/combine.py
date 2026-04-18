"""Combine weather sources use case."""
from datetime import datetime
from typing import Optional

from domain.entities.weather import WeatherData, Location, WeatherRecord
from domain.interfaces.sources import WeatherDataSource, CacheProvider


class CombineWeatherSources:
    """
    Use case for combining data from multiple weather sources.
    
    Responsibilities:
    - Fetch data from multiple sources in parallel
    - Normalize and align timestamps
    - Handle missing data gracefully
    - Provide combined output
    """
    
    def __init__(
        self,
        sources: list[WeatherDataSource],
        cache: Optional[CacheProvider] = None
    ):
        self.sources = sources
        self.cache = cache
    
    async def execute(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "America/Bogota",
        sources_to_use: Optional[list[str]] = None
    ) -> WeatherRecord:
        """
        Execute multi-source fetch.
        
        Args:
            latitude: Location latitude
            longitude: Location longitude
            timezone: Timezone for data
            sources_to_use: Optional list of source names to use
            
        Returns:
            WeatherRecord with combined data from all sources
        """
        import asyncio
        
        # Filter sources if specified
        sources_to_fetch = []
        for source in self.sources:
            if sources_to_use is None or source.name in sources_to_use:
                sources_to_fetch.append(source)
        
        # Fetch from all sources concurrently
        async def fetch_with_cache(source):
            cache_key = f"current:{source.name}:{latitude}:{longitude}:{timezone}"
            if self.cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    return cached
            data = await source.fetch_current(latitude, longitude, timezone)
            return {
                "source": source.name,
                "data": data
            }
        
        results = await asyncio.gather(
            *[fetch_with_cache(s) for s in sources_to_fetch],
            return_exceptions=True
        )
        
        # Combine data from all sources
        combined_data: list[WeatherData] = []
        
        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, dict):
                for weather_data in result.get("data", []):
                    weather_data.source = result["source"]
                    combined_data.append(weather_data)
        
        location = Location(latitude=latitude, longitude=longitude, timezone=timezone)
        
        return WeatherRecord(
            location=location,
            data=combined_data,
            source="combined",
            fetched_at=datetime.now()
        )


class GenerateQualityReport:
    """Use case for generating data quality reports."""
    
    def __init__(self, processor):
        self.processor = processor
    
    def execute(self, data: list[WeatherData]) -> dict:
        """
        Generate data quality report.
        
        Args:
            data: List of weather data to analyze
            
        Returns:
            Dictionary with quality metrics
        """
        if not data:
            return {
                "summary": {
                    "total_records": 0,
                    "complete_records": 0,
                    "missing_data_percent": 100,
                    "overall_quality": "no_data"
                }
            }
        
        total = len(data)
        
        # Calculate completeness
        complete = sum(
            1 for d in data
            if d.temperature is not None
            and d.humidity is not None
            and d.precipitation is not None
            and d.wind_speed is not None
        )
        
        missing_percent = ((total - complete) / total) * 100 if total > 0 else 100
        
        # Determine quality level
        if missing_percent < 10:
            quality = "excellent"
        elif missing_percent < 25:
            quality = "good"
        elif missing_percent < 50:
            quality = "fair"
        else:
            quality = "poor"
        
        # Get sources
        sources = list(set(d.source for d in data))
        
        # Get timestamp range
        timestamps = [d.timestamp for d in data if d.timestamp]
        if timestamps:
            timestamp_range = (min(timestamps), max(timestamps))
        else:
            timestamp_range = (None, None)
        
        return {
            "summary": {
                "total_records": total,
                "complete_records": complete,
                "missing_data_percent": round(missing_percent, 2),
                "overall_quality": quality,
                "data_sources": sources,
                "timestamp_range": {
                    "start": timestamp_range[0].isoformat() if timestamp_range[0] else None,
                    "end": timestamp_range[1].isoformat() if timestamp_range[1] else None
                }
            },
            "per_field": {
                "temperature": self._field_completeness(data, "temperature"),
                "humidity": self._field_completeness(data, "humidity"),
                "precipitation": self._field_completeness(data, "precipitation"),
                "wind_speed": self._field_completeness(data, "wind_speed")
            }
        }
    
    def _field_completeness(self, data: list[WeatherData], field: str) -> dict:
        """Calculate completeness for a specific field."""
        values = [getattr(d, field) for d in data]
        non_null = [v for v in values if v is not None]
        total = len(values)
        
        return {
            "total": total,
            "available": len(non_null),
            "percent": round((len(non_null) / total) * 100, 2) if total > 0 else 0
        }