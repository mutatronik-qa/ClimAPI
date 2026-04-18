from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, Field, field_validator, ConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    model_config = ConfigDict(extra='ignore', env_file='.env', env_file_encoding='utf-8')
    
    # API Keys - Dejar como None si no están definidas
    OPENWEATHER_API_KEY: Optional[str] = Field(default=None)
    METEOSOURCE_API_KEY: Optional[str] = Field(default=None)
    METEOBLUE_API_KEY: Optional[str] = Field(default=None)
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # CORS - Se lee como string del .env y se parsea a lista
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:3001")
    
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
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parsea ALLOWED_ORIGINS como lista."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]

# Instanciar configuración
settings = Settings()