"""
Configuración centralizada de ClimAPI usando Pydantic.

Maneja:
- Variables de entorno (.env)
- Valores por defecto
- Validación de tipos
- Ubicaciones predefinidas
- TTL de caché diferenciado
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import Optional, Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class CacheSettings(BaseSettings):
    """Configuración de caché por tipo de dato."""
    
    current_weather: int = Field(15, description="TTL para datos actuales (minutos)")
    forecast: int = Field(60, description="TTL para pronósticos (minutos)")
    historical: int = Field(1440, description="TTL para históricos (minutos)")
    radar: int = Field(10, description="TTL para radar (minutos)")
    siata: int = Field(15, description="TTL para SIATA (minutos)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_weather": 15,
                "forecast": 60,
                "historical": 1440,
                "radar": 10,
                "siata": 15
            }
        }


class LocationSettings(BaseSettings):
    """Ubicaciones predefinidas con coordenadas."""
    
    medellin: Dict = {
        "name": "Medellín, Colombia",
        "latitude": 6.2442,
        "longitude": -75.5812,
        "timezone": "America/Bogota",
        "altitude": 1495
    }
    bello: Dict = {
        "name": "Bello, Colombia",
        "latitude": 6.3373,
        "longitude": -75.5610,
        "timezone": "America/Bogota",
        "altitude": 1400
    }
    envigado: Dict = {
        "name": "Envigado, Colombia",
        "latitude": 6.1636,
        "longitude": -75.5898,
        "timezone": "America/Bogota",
        "altitude": 1600
    }
    bogota: Dict = {
        "name": "Bogotá, Colombia",
        "latitude": 4.7110,
        "longitude": -74.0721,
        "timezone": "America/Bogota",
        "altitude": 2640
    }
    
    def get_location(self, name: str) -> Optional[Dict]:
        """Obtiene datos de una ubicación por nombre."""
        locations_dict = {
            "medellin": self.medellin,
            "bello": self.bello,
            "envigado": self.envigado,
            "bogota": self.bogota
        }
        return locations_dict.get(name.lower())


class Settings(BaseSettings):
    """
    Configuración principal de ClimAPI.
    
    Lee variables de .env y aplica valores por defecto.
    """
    
    # ============================================
    # DIRECTORIOS Y RUTAS
    # ============================================
    
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATA_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "data")
    CACHE_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "cache")
    LOG_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "logs")
    NOTEBOOKS_DIR: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "notebooks")
    
    # ============================================
    # APLICACIÓN
    # ============================================
    
    APP_NAME: str = "ClimAPI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(False, description="Modo debug")
    ENVIRONMENT: str = Field("development", description="environment: development, staging, production")
    
    # ============================================
    # API Y SERVIDOR
    # ============================================
    
    API_HOST: str = Field("0.0.0.0", description="Host para FastAPI")
    API_PORT: int = Field(8000, description="Puerto para FastAPI")
    API_DOCS_ENABLED: bool = Field(True, description="Habilitar Swagger docs")
    API_CORS_ORIGINS: List[str] = Field(
        ["http://localhost:3000", "http://localhost:8000"],
        description="CORS origins permitidos"
    )
    
    # ============================================
    # CACHÉ
    # ============================================
    
    CACHE_BACKEND: str = Field("diskcache", description="Backend de caché")
    CACHE_CONFIG: CacheSettings = Field(default_factory=CacheSettings)
    
    # ============================================
    # LOGGING
    # ============================================
    
    LOG_LEVEL: str = Field("INFO", description="INFO, DEBUG, WARNING, ERROR")
    LOG_FORMAT: str = Field("json", description="json o text")
    LOG_TO_FILE: bool = Field(True, description="Guardar logs en archivo")
    LOG_FILE_NAME: str = Field("climapi.log")
    
    # ============================================
    # DATOS Y UBICACIONES
    # ============================================
    
    DEFAULT_LOCATION: str = Field("medellin", description="Ubicación por defecto")
    LOCATIONS: LocationSettings = Field(default_factory=LocationSettings)
    DEFAULT_TIMEZONE: str = "America/Bogota"
    
    # ============================================
    # OPEN-METEO (GRATUITO)
    # ============================================
    
    OPENMETEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    OPENMETEO_FORECAST_DAYS: int = 7
    OPENMETEO_HISTORICAL_DAYS: int = 90
    
    # ============================================
    # OPENWEATHERMAP
    # ============================================
    
    OPENWEATHER_API_KEY: Optional[str] = Field(None, description="API Key de OpenWeatherMap")
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5/"
    OPENWEATHER_UNITS: str = "metric"
    OPENWEATHER_TIMEOUT: int = 15
    
    # ============================================
    # METEOBLUE
    # https://my.meteoblue.com/packages/basic-15min_basic-3h_current_clouds-1h_sunmoon_moonlight-30min?apikey=igGRprBlUxkD89MK&lat=6.245&lon=-75.5715&asl=1405&format=json
    # ============================================
    
    METEOBLUE_API_KEY: Optional[str] = Field(None, description="API Key de Meteoblue")
    METEOBLUE_BASE_URL: str = "https://my.meteoblue.com"
    METEOBLUE_SHARED_SECRET: Optional[str] = Field(None, description="Shared Secret Meteoblue")
    METEOBLUE_ENDPOINT: str = "basic-15min_basic-3h_current_clouds-1h_sunmoon_moonlight-30min"
    METEOBLUE_FORECAST_DAYS: int = 7
    METEOBLUE_TIMEOUT: int = 20
    
    # ============================================
    # SIATA (LOCAL - MEDELLÍN)
    # ============================================
    
    SIATA_API_URL: str = "https://www.siata.gov.co"
    SIATA_OPERACIONAL_URL: str = "https://www.siata.gov.co/operacional/"
    SIATA_TIMEOUT: int = 15
    SIATA_RETRY_ATTEMPTS: int = 3
    
    # ============================================
    # IDEAM RADAR (AWS S3 - GRATUITO)
    # ============================================
    
    IDEAM_RADAR_BUCKET: str = "s3-radaresideam"
    IDEAM_RADAR_REGION: str = "us-east-1"
    IDEAM_RADAR_TIMEOUT: int = 30
    IDEAM_RADAR_SIGN_REQUEST: bool = False  # Acceso público
    
    # ============================================
    # NASA NSRDB (SOLAR - REQUIERE API KEY)
    # ============================================
    
    NSRDB_API_KEY: Optional[str] = Field(None, description="API Key de NSRDB NASA")
    NSRDB_BASE_URL: str = "https://developer.nrel.gov/api/nsrdb/v2/solar"
    NSRDB_TIMEOUT: int = 20
    
    # ============================================
    # NASA POWER (IRRADIANCIA - GRATUITO)
    # ============================================
    
    POWER_BASE_URL: str = "https://power.larc.nasa.gov/api/v1/aggregate"
    POWER_COMMUNITY: str = "SB"  # SB = Sustainable Bioenergy
    POWER_TIMEOUT: int = 20
    
    # ============================================
    # VALIDACIÓN Y TRANSFORMACIÓN
    # ============================================
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT debe ser uno de {allowed}")
        return v
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL debe ser uno de {allowed}")
        return v.upper()
    
    def ensure_directories(self):
        """Crea directorios necesarios si no existen."""
        for directory in [self.DATA_DIR, self.CACHE_DIR, self.LOG_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"


# Instancia global
settings = Settings()

# Crear directorios al importar
settings.ensure_directories()

if __name__ == "__main__":
    # Test de configuración
    print("🔧 Configuración de ClimAPI:")
    print(f"Proyecto: {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"Entorno: {settings.ENVIRONMENT}")
    print(f"Debug: {settings.DEBUG}")
    print(f"Data Dir: {settings.DATA_DIR}")
    print(f"Ubicaciones disponibles: {list(settings.LOCATIONS.__dict__.keys())}")
    print(f"TTL Caché: {settings.CACHE_CONFIG.model_dump()}")
