"""
Núcleo de ClimAPI - Punto de entrada con lazy loading.

Este módulo proporciona acceso lazy a todas las funcionalidades
del proyecto, evitando la carga de módulos pesados al inicio.

Uso:
    from core import get_weather, list_sources, get_cache
    
    # Obtener datos meteorológicos
    data = get_weather("open-meteo", lat=6.244, lon=-75.581)
    
    # Listar fuentes disponibles
    sources = list_sources()
    
    # Obtener instancia de caché
    cache = get_cache()
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _ensure_cache():
    """Inicializa el caché solo cuando se necesita."""
    from core.cache import get_cache
    return get_cache()


def _ensure_sources():
    """Inicializa las fuentes de datos."""
    from core.source_base import WeatherSourceFactory
    
    # Registrar fuentes disponibles
    if not WeatherSourceFactory._sources:
        try:
            from data_sources.open_meteo_source import OpenMeteoSource
            WeatherSourceFactory.register(OpenMeteoSource, "open-meteo")
        except ImportError as e:
            logger.warning(f"Error importando OpenMeteoSource: {e}")
    
    return WeatherSourceFactory


def list_sources() -> List[Dict[str, Any]]:
    """
    Lista todas las fuentes de datos disponibles.
    """
    factory = _ensure_sources()
    sources = factory.get_all_names()
    
    # Información de cada fuente
    result = []
    for name in sources:
        source_class = factory._sources.get(name)
        if source_class:
            result.append({
                "name": name,
                "requires_api_key": getattr(source_class, "requires_api_key", False),
                "is_free": getattr(source_class, "is_free", True),
                "ttl_default": getattr(source_class, "ttl_default", 900)
            })
    return result


def get_source(name: str, **config) -> Optional[Any]:
    """
    Obtiene una fuente de datos específica.
    
    Args:
        name: Nombre de la fuente (open-meteo, openweathermap, meteoblue, etc.)
        **config: Configuración específica de la fuente
    
    Returns:
        Instancia de la fuente de datos o None
    """
    factory = _ensure_sources()
    return factory.create(name, **config)


def get_weather(
    source: str,
    latitude: float,
    longitude: float,
    timezone: str = "America/Bogota",
    **kwargs
) -> Dict[str, Any]:
    """
    Obtiene datos meteorológicos de una fuente específica.
    
    Args:
        source: Nombre de la fuente de datos
        latitude: Latitud
        longitude: Longitud
        timezone: Zona horaria
        **kwargs: Parámetros adicionales
    
    Returns:
        Dict con datos meteorológicos
    """
    source_instance = get_source(source)
    
    if source_instance is None:
        raise ValueError(f"Fuente no encontrada: {source}")
    
    # Intentar obtener del caché primero
    cache = _ensure_cache()
    cache_key = f"weather_{source}_{latitude}_{longitude}_{timezone}"
    
    cached_data = cache.get_json(cache_key)
    if cached_data:
        logger.info(f"📦 Usando datos en caché para {source}")
        return cached_data
    
    # Obtener datos frescos
    data = source_instance.fetch_current(latitude, longitude, timezone=timezone, **kwargs)
    
    # Guardar en caché
    cache.set_json(cache_key, data, ttl_type="current_weather")
    
    return data


def get_forecast(
    source: str,
    latitude: float,
    longitude: float,
    days: int = 7,
    timezone: str = "America/Bogota"
) -> Dict[str, Any]:
    """
    Obtiene pronóstico meteorológico.
    """
    source_instance = get_source(source)
    
    if source_instance is None:
        raise ValueError(f"Fuente no encontrada: {source}")
    
    cache = _ensure_cache()
    cache_key = f"forecast_{source}_{latitude}_{longitude}_{days}_{timezone}"
    
    cached_data = cache.get_json(cache_key)
    if cached_data:
        return cached_data
    
    data = source_instance.fetch_forecast(latitude, longitude, days=days, timezone=timezone)
    
    cache.set_json(cache_key, data, ttl_type="forecast")
    
    return data


def get_cache():
    """Obtiene la instancia del caché."""
    return _ensure_cache()


def get_stats() -> Dict:
    """Obtiene estadísticas del sistema."""
    cache = _ensure_cache()
    return {
        "cache": cache.get_stats(),
        "sources": list_sources()
    }


# Lazy imports para funciones principales
__all__ = [
    "list_sources",
    "get_source",
    "get_weather",
    "get_forecast",
    "get_cache",
    "get_stats"
]