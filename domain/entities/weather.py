from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import numpy as np


class WeatherData(BaseModel):
    """Normalized weather data entity."""
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    source: str
    
    @field_validator('temperature', 'humidity', 'precipitation', 'wind_speed', mode='before')
    @classmethod
    def handle_null_values(cls, v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return None
        return v


class Location(BaseModel):
    """Geographic location entity."""
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"
    name: Optional[str] = None
    country: Optional[str] = None
    
    @field_validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v
    
    @field_validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v


class WeatherSourceInfo(BaseModel):
    """Information about a weather data source."""
    name: str
    display_name: str
    requires_api_key: bool = False
    is_free: bool = True
    base_url: Optional[str] = None
    documentation_url: Optional[str] = None


class WeatherRecord(BaseModel):
    """Complete weather record with location and data."""
    location: Location
    data: list[WeatherData]
    source: str
    fetched_at: datetime = Field(default_factory=datetime.now)
    cache_ttl_seconds: int = 900


class DataQualityMetrics(BaseModel):
    """Data quality metrics for a dataset."""
    total_records: int
    complete_records: int
    missing_data_percent: float
    outlier_count: int
    data_sources: list[str]
    timestamp_range: tuple[datetime, datetime]
    overall_quality: str = "good"  # good, fair, poor