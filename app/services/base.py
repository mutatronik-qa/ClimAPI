"""
Servicio base para clientes de APIs meteorológicas.

Provee:
- Gestión de configuración
- Integración con sistema de caché (intenta usar app.processors.cache_manager)
- Helpers async para set/get cache (fallback in-memory si no existe implementacion externa)
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

# Intentar importar funciones de cache externas (varias rutas posibles)
try:
    # Ruta preferida si existe un módulo de cache asíncrono
    from app.processors.cache_manager import cache_get as external_cache_get, cache_set as external_cache_set  # type: ignore
    async def cache_get(key: str) -> Optional[Any]:
        return await external_cache_get(key)
    async def cache_set(key: str, value: Any, ttl: int):
        return await external_cache_set(key, value, ttl)
    logger.debug("Usando cache externa: app.processors.cache_manager")
except Exception:
    try:
        # Intento por la ruta processing (sin async): envolver en executor
        from processing.storage import CacheManager  # type: ignore
        _sync_cache = CacheManager(ttl_minutes=15, cache_dir="cache")
        loop = asyncio.get_event_loop()
        async def cache_get(key: str) -> Optional[Any]:
            def _get():
                # CacheManager no expone get por clave arbitraria; usar memory_cache si existe
                mem = getattr(_sync_cache, "memory_cache", {})
                return mem.get(key, (None, None))[0] if key in mem else None
            return await loop.run_in_executor(None, _get)
        async def cache_set(key: str, value: Any, ttl: int):
            def _set():
                # Guardar en memory_cache para compatibilidad mínima
                _sync_cache.memory_cache[key] = (value, datetime.utcnow())
            return await loop.run_in_executor(None, _set)
        logger.debug("Usando processing.storage.CacheManager como backend de cache (adaptado)")
    except Exception:
        # Fallback en memoria totalmente async
        _LOCAL_CACHE: Dict[str, Dict[str, Any]] = {}
        async def cache_get(key: str) -> Optional[Any]:
            entry = _LOCAL_CACHE.get(key)
            if not entry:
                return None
            if datetime.utcnow() > entry["expires_at"]:
                del _LOCAL_CACHE[key]
                return None
            return entry["value"]
        async def cache_set(key: str, value: Any, ttl: int):
            _LOCAL_CACHE[key] = {
                "value": value,
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
            }
        logger.debug("Usando fallback de cache en memoria")

class BaseService:
    """
    Clase base para servicios externos. Provee:
      - self.config
      - _get_cache / _set_cache async
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self._default_ttl = int(self.config.get("ttl_seconds", 900))

    async def _get_cache(self, key: str) -> Optional[Any]:
        try:
            return await cache_get(key)
        except Exception as e:
            logger.debug(f"_get_cache fallo: {e}")
            return None

    async def _set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
        try:
            ttl_use = int(ttl) if ttl is not None else self._default_ttl
            await cache_set(key, value, ttl_use)
        except Exception as e:
            logger.debug(f"_set_cache fallo: {e}")
            return