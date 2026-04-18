"""Pydantic models for API."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Location(BaseModel):
    """Location coordinates."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"


class WeatherData(BaseModel):
    """Standardized weather data."""
    timestamp: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    source: str
    error: Optional[str] = None


class WeatherResponse(BaseModel):
    """API response model."""
    location: Location
    data: dict
    fetched_at: str


class SourceStatus(BaseModel):
    """Source status info."""
    name: str
    status: str
    response_time: float
    error: Optional[str] = None


class CacheStats(BaseModel):
    """Cache statistics."""
    cached_entries: int
    cache_ttl: int