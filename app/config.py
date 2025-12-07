from pydantic import BaseSettings, AnyHttpUrl, Field
from typing import List

class Settings(BaseSettings):
    # API Keys - Dejar como None si no están definidas
    OPENWEATHER_API_KEY: str
    METEOSOURCE_API_KEY: str
    METEOBLUE_API_KEY: str
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS
    ALLOWED_ORIGINS: List[AnyHttpUrl] = Field(default=["http://localhost:3000"])
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
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

# Instanciar configuración
settings = Settings()