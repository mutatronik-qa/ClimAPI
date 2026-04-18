"""
Configuración centralizada con lazy loading.

Proporciona acceso a configuración de forma perezosa,
evitando cargar módulos pesados al inicio.
"""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)


class LazySettings:
    """
    Configuración lazy que solo carga lo necesario.
    """
    
    _instance: Optional['LazySettings'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._settings: Dict[str, Any] = {}
        self._load_env()
        self._ensure_directories()
        self._initialized = True
    
    def _load_env(self):
        """Carga variables de entorno con valores por defecto."""
        # TTL
        self._settings["CACHE_TTL_MINUTES"] = int(os.getenv("CACHE_TTL_MINUTES", "15"))
        self._settings["CACHE_DIR"] = os.getenv("CACHE_DIR", "cache")
        
        # Directorios
        self._settings["DATA_DIR"] = "data"
        self._settings["LOG_DIR"] = "logs"
        
        # Open-Meteo (gratuito)
        self._settings["OPENMETEO_BASE_URL"] = os.getenv(
            "OPENMETEO_BASE_URL", 
            "https://api.open-meteo.com/v1"
        )
        
        # OpenWeatherMap (requiere API key)
        self._settings["OPENWEATHER_API_KEY"] = os.getenv("OPENWEATHER_API_KEY")
        self._settings["OPENWEATHER_BASE_URL"] = os.getenv(
            "OPENWEATHER_BASE_URL",
            "https://api.openweathermap.org/data/2.5/"
        )
        
        # MeteoBlue (freemium)
        self._settings["METEOBLUE_API_KEY"] = os.getenv("METEOBLUE_API_KEY")
        self._settings["METEOBLUE_BASE_URL"] = os.getenv(
            "METEOBLUE_BASE_URL",
            "https://my.meteoblue.com"
        )
        
        # SIATA (Colombia)
        self._settings["SIATA_API_URL"] = os.getenv(
            "SIATA_API_URL",
            "https://www.siata.gov.co"
        )
        
        # IDEAM Radar
        self._settings["IDEAM_RADAR_BUCKET"] = os.getenv(
            "IDEAM_RADAR_BUCKET",
            "s3-radaresideam"
        )
        
        # App settings
        self._settings["APP_NAME"] = os.getenv("APP_NAME", "ClimAPI")
        self._settings["DEBUG"] = os.getenv("DEBUG", "false").lower() == "true"
        
        logger.debug(f"⚙️ Configuración cargada desde entorno")
    
    def _ensure_directories(self):
        """Crea directorios necesarios."""
        for dir_name in ["data", "cache", "logs"]:
            Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    def __getattr__(self, name: str) -> Any:
        """Acceso lazy a configuración."""
        if name not in self._settings:
            logger.warning(f"Configuración '{name}' no encontrada, retornando None")
            return None
        return self._settings[name]
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene configuración con valor por defecto."""
        return self._settings.get(key, default)
    
    def get_location(self, name: str = "medellin") -> Dict[str, Any]:
        """Obtiene coordenadas de ubicación predefinida."""
        locations = {
            "medellin": {
                "name": "Medellín",
                "latitude": 6.2442,
                "longitude": -75.5812,
                "timezone": "America/Bogota"
            },
            "bogota": {
                "name": "Bogotá",
                "latitude": 4.7110,
                "longitude": -74.0721,
                "timezone": "America/Bogota"
            },
            "cali": {
                "name": "Cali",
                "latitude": 3.4516,
                "longitude": -76.5320,
                "timezone": "America/Bogota"
            }
        }
        return locations.get(name.lower(), locations["medellin"])
    
    def get_cache_ttl(self, data_type: str = "default") -> int:
        """Obtiene TTL específico por tipo de dato."""
        ttls = {
            "default": 15,
            "current_weather": 15,
            "forecast": 60,
            "historical": 1440,
            "radar": 10,
            "siata": 15
        }
        return ttls.get(data_type, 15)
    
    @property
    def data_dir(self) -> str:
        return self._settings.get("DATA_DIR", "data")
    
    @property
    def cache_dir(self) -> str:
        return self._settings.get("CACHE_DIR", "cache")
    
    @property
    def cache_ttl_minutes(self) -> int:
        return self._settings.get("CACHE_TTL_MINUTES", 15)


# Instancia global lazy
_settings: Optional[LazySettings] = None


def get_settings() -> LazySettings:
    """Obtiene la instancia global de configuración."""
    global _settings
    if _settings is None:
        _settings = LazySettings()
    return _settings


# Acceso directo a propiedades comunes
def get_data_dir() -> str:
    return get_settings().data_dir


def get_cache_dir() -> str:
    return get_settings().cache_dir


def get_cache_ttl() -> int:
    return get_settings().cache_ttl_minutes


def get_location(name: str = "medellin") -> Dict[str, Any]:
    return get_settings().get_location(name)


# Alias para compatibilidad
class Settings:
    """Clase de compatibilidad con código existente."""
    
    def __getattr__(self, name: str):
        return get_settings().__getattr__(name)


settings = Settings()