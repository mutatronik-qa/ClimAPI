"""
Gestor de plugins para fuentes de datos climáticas.

Implementa un sistema de carga perezosa (lazy loading) que permite
agregar nuevas fuentes de datos sin modificar código existente.

Patrón: Plugin / Strategy
"""

import importlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class WeatherDataSource(ABC):
    """Interfaz base para todas las fuentes de datos."""
    
    name: str = ""
    requires_api_key: bool = False
    is_free: bool = True
    ttl_default: int = 900  # 15 minutos
    
    @abstractmethod
    def fetch_current(self, latitude: float, longitude: float, **kwargs) -> Dict[str, Any]:
        """Obtiene datos meteorológicos actuales."""
        pass
    
    @abstractmethod
    def fetch_forecast(self, latitude: float, longitude: float, days: int = 7, **kwargs) -> Dict[str, Any]:
        """Obtiene pronóstico meteorológico."""
        pass
    
    def validate_config(self) -> bool:
        """Valida que la configuración necesaria esté disponible."""
        return True


class DataSourceRegistry:
    """
    Registro central de fuentes de datos.
    Implementa carga perezosa y validación de plugins.
    """
    
    _sources: Dict[str, Type[WeatherDataSource]] = {}
    _instances: Dict[str, WeatherDataSource] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, source_class: Type[WeatherDataSource], name: Optional[str] = None):
        """Registra una nueva fuente de datos."""
        source_name = name or source_class.name
        cls._sources[source_name] = source_class
        logger.info(f"📦 Registrado fuente: {source_name}")
    
    @classmethod
    def get(cls, name: str, **config) -> Optional[WeatherDataSource]:
        """Obtiene una instancia de fuente de datos (lazy load)."""
        if name not in cls._sources:
            logger.warning(f"Fuente no encontrada: {name}")
            return None
        
        # Crear instancia si no existe (singleton por configuración)
        if name not in cls._instances:
            cls._instances[name] = cls._sources[name](**config)
        
        return cls._instances[name]
    
    @classmethod
    def list_sources(cls) -> List[Dict[str, Any]]:
        """Lista todas las fuentes disponibles."""
        return [
            {
                "name": name,
                "requires_api_key": src.requires_api_key,
                "is_free": src.is_free,
                "ttl_default": src.ttl_default
            }
            for name, src in cls._sources.items()
        ]
    
    @classmethod
    def auto_discover(cls, base_path: str = "data_sources"):
        """Descubre automáticamente fuentes de datos."""
        if cls._initialized:
            return
        
        base = Path(base_path)
        if not base.exists():
            logger.warning(f"Directorio de fuentes no encontrado: {base_path}")
            return
        
        for file in base.glob("*.py"):
            if file.stem.startswith("_") or file.stem == "base":
                continue
            
            try:
                module = importlib.import_module(f"{base_path}.{file.stem}")
                
                # Buscar clases que hereden de WeatherDataSource
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type) 
                        and issubclass(attr, WeatherDataSource) 
                        and attr is not WeatherDataSource
                    ):
                        cls.register(attr)
                
                cls._initialized = True
                logger.info(f"🔍 Descubiertas {len(cls._sources)} fuentes de datos")
                
            except Exception as e:
                logger.warning(f"Error cargando {file.stem}: {e}")


def register_source(source_class: Type[WeatherDataSource]):
    """Decorador para registrar fuentes de datos."""
    DataSourceRegistry.register(source_class)
    return source_class