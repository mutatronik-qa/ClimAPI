from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Keys
    OPENWEATHER_API_KEY: str = ""
    METEOSOURCE_API_KEY: str = ""
    METEOBLUE_API_KEY: str = ""
    
    # AWS Credentials
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG_MODE: bool = False
    
    # Cache Configuration
    CACHE_TTL_MINUTES: int = 15
    CACHE_DIR: str = "cache"
    
    # Default Location
    DEFAULT_LAT: float = 6.244
    DEFAULT_LON: float = -75.581
    DEFAULT_TIMEZONE: str = "America/Bogota"
    DEFAULT_CITY: str = "Medellín"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()