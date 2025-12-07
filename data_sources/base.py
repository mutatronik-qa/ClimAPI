"""
Servicio base para clientes de APIs meteorológicas.

Este módulo define la clase base que todos los servicios de APIs
externas deben heredar. Proporciona funcionalidad común como:
    - Gestión de configuración
    - Acceso a caché compartido
    - Utilidades para peticiones HTTP

Clases:
    BaseService: Clase base abstracta para servicios

Patrón de diseño:
    - Template Method: Define estructura común
    - Dependency Injection: Recibe configuración externa
"""

from typing import Dict, Any, Optional
from app.processors.cache_manager import cache_get, cache_set
import asyncio

class BaseService:
    """
    Servicio base que provee utilidades comunes para todos los clientes de APIs.
    
    Esta clase proporciona funcionalidad compartida por todos los servicios
    que consumen APIs externas (OpenWeatherMap, MeteoBlue, SIATA, etc.).
    
    Funcionalidades:
        - Almacenamiento de configuración
        - Acceso al sistema de caché global
        - Métodos helper para operaciones comunes
    
    Atributos:
        config: Diccionario con configuración específica del servicio
                (API keys, URLs, timeouts, etc.)
    
    Uso:
        class MiServicio(BaseService):
            async def get_data(self, location):
                cached = await self._get_cache(f"mi_servicio:{location}")
                if cached:
                    return cached
                # ... obtener datos de API ...
                await self._set_cache(key, data, ttl=900)
                return data
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa el servicio con su configuración.
        
        Args:
            config: Diccionario con configuración del servicio.
                   Debe incluir: api_key, base_url, ttl_seconds, etc.
        """
        self.config = config or {}  # Usar dict vacío si config es None

    async def _get_cache(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del caché global.
        
        Args:
            key: Clave única para identificar los datos en caché
        
        Returns:
            Datos almacenados en caché o None si no existen o expiraron
        
        Ejemplo:
            cached_weather = await self._get_cache("openweather:medellin")
        """
        return await cache_get(key)

    async def _set_cache(self, key: str, value: Any, ttl: int):
        """
        Almacena un valor en el caché global con tiempo de expiración.
        
        Args:
            key: Clave única para identificar los datos
            value: Datos a almacenar (debe ser serializable)
            ttl: Tiempo de vida en segundos
        
        Ejemplo:
            await self._set_cache("openweather:medellin", weather_data, ttl=900)
        """
        await cache_set(key, value, ttl)