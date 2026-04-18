"""API Pydantic models."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class LocationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"


class WeatherDataPoint(BaseModel):
    timestamp: str
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    source: str


class WeatherResponse(BaseModel):
    location: LocationRequest
    data: List[WeatherDataPoint]
    source: str
    fetched_at: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class SourceInfo(BaseModel):
    name: str
    display_name: str
    requires_api_key: bool
    is_free: bool


class CacheStats(BaseModel):
    hits: int
    misses: int
    hit_rate_percent: float
    cached_entries: int


class DataQualitySummary(BaseModel):
    total_records: int
    complete_records: int
    missing_data_percent: float
    overall_quality: str
    data_sources: List[str]
    timestamp_range: dict


class ErrorResponse(BaseModel):
    detail: str
    error_type: Optional[str] = None