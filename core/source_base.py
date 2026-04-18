"""
Clase base abstracta para fuentes de datos meteorológicos.

Implementa el patrón Strategy y Template Method para definir
la estructura común de todas las fuentes de datos.

Características:
- Caché automático con TTL configurable
- Normalización de datos al esquema unificado
- Manejo de errores centralizado
- Métricas de uso
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import logging
import pandas as pd
import hashlib

logger = logging.getLogger(__name__)


class BaseWeatherSource(ABC):
    """
    Clase base para todas las fuentes de datos meteorológicos.
    
    Proporciona:
    - Integración automática con caché
    - Normalización de datos
    - Validación de configuración
    - Métricas de uso
    
    Uso:
        class MiFuente(BaseWeatherSource):
            name = "mi-fuente"
            requires_api_key = True
            is_free = False
            
            def _fetch_raw(self, lat, lon, **kwargs):
                # Implementar llamada a API
                pass
            
            def _normalize(self, raw_data) -> pd.DataFrame:
                # Implementar normalización
                pass
    """
    
    name: str = ""
    base_url: str = ""
    requires_api_key: bool = False
    api_key_env: str = ""  # Variable de entorno para API key
    is_free: bool = True
    ttl_default: int = 900  # 15 minutos
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa la fuente con configuración opcional.
        
        Args:
            config: Diccionario con configuración específica
        """
        self.config = config or {}
        self._cache_ttl = self.config.get("ttl_seconds", self.ttl_default)
        self._metrics = {
            "requests": 0,
            "errors": 0,
            "cache_hits": 0,
            "last_request": None
        }
    
    @property
    def api_key(self) -> Optional[str]:
        """Obtiene la API key desde configuración o variable de entorno."""
        if self.config.get("api_key"):
            return self.config.get("api_key")
        
        import os
        if self.api_key_env:
            return os.getenv(self.api_key_env)
        
        return None
    
    def validate_config(self) -> Tuple[bool, str]:
        """
        Valida la configuración necesaria.
        
        Returns:
            (is_valid, error_message)
        """
        if self.requires_api_key and not self.api_key:
            return False, f"Se requiere API key (variable: {self.api_key_env})"
        return True, ""
    
    def _get_cache_key(self, lat: float, lon: float, **kwargs) -> str:
        """Genera clave de caché única."""
        params = f"{lat}_{lon}_{kwargs.get('timezone', 'default')}"
        key_str = f"{self.name}_{params}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Obtiene datos desde el caché global."""
        from core.cache import get_cache
        
        cache = get_cache()
        cached = cache.get_json(f"{self.name}_{key}")
        
        if cached:
            self._metrics["cache_hits"] += 1
            logger.debug(f"Cache hit para {self.name}:{key}")
            return cached
        
        return None
    
    def _save_to_cache(self, key: str, data: Dict):
        """Guarda datos en el caché global."""
        from core.cache import get_cache
        
        cache = get_cache()
        cache.set_json(f"{self.name}_{key}", data, ttl_type="current_weather")
    
    def fetch_current(
        self, 
        latitude: float, 
        longitude: float, 
        force_refresh: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Obtiene datos actuales con caché automático.
        
        Args:
            latitude: Latitud
            longitude: Longitud
            force_refresh: Ignora el caché y obtiene datos frescos
            **kwargs: Parámetros adicionales
        
        Returns:
            Dict con datos meteorológicos normalizados
        """
        self._metrics["requests"] += 1
        
        # Validar configuración
        is_valid, error = self.validate_config()
        if not is_valid:
            raise ValueError(f"Configuración inválida para {self.name}: {error}")
        
        # Generar clave de caché
        cache_key = self._get_cache_key(latitude, longitude, **kwargs)
        
        # Intentar obtener desde caché
        if not force_refresh:
            cached_data = self._get_from_cache(cache_key)
            if cached_data:
                self._metrics["cache_hits"] += 1
                return cached_data
        
        # Obtener datos frescos
        try:
            raw_data = self._fetch_raw(latitude, longitude, **kwargs)
            normalized = self._normalize(raw_data, latitude, longitude, **kwargs)
            
            # Guardar en caché
            self._save_to_cache(cache_key, normalized)
            
            self._metrics["last_request"] = datetime.now().isoformat()
            return normalized
            
        except Exception as e:
            self._metrics["errors"] += 1
            logger.error(f"Error en {self.name}.fetch_current: {e}")
            raise
    
    def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Obtiene datos de pronóstico.
        
        Por defecto usa fetch_current. Las subclases pueden
        sobrescribir este método para optimizar.
        """
        return self.fetch_current(latitude, longitude, **kwargs)
    
    @abstractmethod
    def _fetch_raw(self, latitude: float, longitude: float, **kwargs) -> Dict[str, Any]:
        """
        Método abstracto que cada fuente debe implementar.
        Realiza la llamada a la API externa.
        
        Args:
            latitude: Latitud
            longitude: Longitud
            **kwargs: Parámetros específicos de la fuente
        
        Returns:
            Dict con respuesta cruda de la API
        """
        pass
    
    @abstractmethod
    def _normalize(self, raw_data: Dict, latitude: float, longitude: float, **kwargs) -> Dict[str, Any]:
        """
        Normaliza los datos crudos al esquema unificado.
        
        Args:
            raw_data: Datos crudos de la API
            latitude: Latitud
            longitude: Longitud
            **kwargs: Parámetros adicionales
        
        Returns:
            Dict con datos normalizados
        """
        pass
    
    def get_metrics(self) -> Dict:
        """Retorna métricas de uso de la fuente."""
        return {
            "name": self.name,
            "is_free": self.is_free,
            "requires_api_key": self.requires_api_key,
            "metrics": self._metrics
        }


class WeatherSourceFactory:
    """
    Factory para crear instancias de fuentes de datos.
    
    Uso:
        factory = WeatherSourceFactory()
        
        # Crear fuente específica
        source = factory.create("open-meteo", config={...})
        
        # Obtener todas las fuentes gratuitas
        free_sources = factory.get_free_sources()
    """
    
    _sources: Dict[str, type] = {}
    
    @classmethod
    def register(cls, source_class: type, name: Optional[str] = None):
        """Registra una clase de fuente."""
        source_name = name or getattr(source_class, "name", source_class.__name__)
        cls._sources[source_name] = source_class
        logger.info(f"✅ Registrada fuente: {source_name}")
    
    @classmethod
    def create(cls, name: str, **config) -> Optional[BaseWeatherSource]:
        """Crea una instancia de fuente por nombre."""
        if name not in cls._sources:
            logger.warning(f"Fuente no registrada: {name}")
            return None
        
        return cls._sources[name](config)
    
    @classmethod
    def get_free_sources(cls) -> List[str]:
        """Lista fuentes gratuitas."""
        return [
            name for name, cls in cls._sources.items() 
            if getattr(cls, "is_free", True)
        ]
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """Lista todos los nombres de fuentes."""
        return list(cls._sources.keys())


# Auto-registro de fuentes del proyecto
def _auto_register_sources():
    """Registra automáticamente las fuentes existentes."""
    WeatherSourceFactory.register(
        __import__("data_sources.open_meteo", fromlist=["OpenMeteoSource"]).OpenMeteoSource,
        "open-meteo"
    )
    
    WeatherSourceFactory.register(
        __import__("data_sources.openweathermap", fromlist=["OpenWeatherMapSource"]).OpenWeatherMapSource,
        "openweathermap"
    )

from typing import Optional