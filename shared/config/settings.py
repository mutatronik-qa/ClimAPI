"""
Shared configuration module.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from pathlib import Path


class Settings(BaseSettings):
    """Main application settings."""
    
    APP_NAME: str = "ClimAPI"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_CORS_ORIGINS: List[str] = ["*"]
    
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "text"
    LOG_TO_FILE: bool = True
    
    CACHE_BACKEND: str = "memory"
    CACHE_TTL_CURRENT: int = 900
    CACHE_TTL_FORECAST: int = 3600
    
    DATA_DIR: Path = Field(default_factory=lambda: Path("data"))
    CACHE_DIR: Path = Field(default_factory=lambda: Path("cache"))
    LOG_DIR: Path = Field(default_factory=lambda: Path("logs"))
    
    DEFAULT_LATITUDE: float = 6.244
    DEFAULT_LONGITUDE: float = -75.581
    DEFAULT_TIMEZONE: str = "America/Bogota"
    
    OPENMETEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    OPENMETEO_FORECAST_DAYS: int = 7
    
    OPENWEATHER_API_KEY: Optional[str] = None
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5/"
    OPENWEATHER_UNITS: str = "metric"
    
    METEOBLUE_API_KEY: Optional[str] = None
    METEOBLUE_BASE_URL: str = "https://my.meteoblue.com"
    
    SIATA_API_URL: str = "https://www.siata.gov.co"
    SIATA_TIMEOUT: int = 15
    
    IDEAM_RADAR_BUCKET: str = "s3-radaresideam"
    IDEAM_RADAR_REGION: str = "us-east-1"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings