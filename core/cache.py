"""
Sistema de caché unificado con TTL configurable.

Proporciona:
- Caché en disco usando diskcache
- TTL por tipo de dato
- Serialización de DataFrames
- Métricas de uso

Patrón: Singleton / Proxy
"""

import diskcache as dc
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuración de caché."""
    ttl_minutes: int = 15
    cache_dir: str = "cache"
    max_size_mb: int = 500
    
    # TTLs específicos por tipo de dato
    current_weather_ttl: int = 15
    forecast_ttl: int = 60
    historical_ttl: int = 1440
    radar_ttl: int = 10
    siata_ttl: int = 15


class CacheMetrics:
    """Métricas de uso del caché."""
    
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0
    
    def to_dict(self) -> Dict:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "errors": self.errors,
            "hit_rate_percent": round(self.hit_rate, 2)
        }


class UnifiedCache:
    """
    Caché unificado con soporte para DataFrames y TTL específico.
    
    Uso:
        cache = UnifiedCache()
        
        # Guardar DataFrame
        cache.set_dataframe("weather_medellin", df, ttl=15)
        
        # Obtener DataFrame
        df = cache.get_dataframe("weather_medellin")
        
        # Guardar JSON
        cache.set_json("forecast", forecast_data, ttl=60)
        
        # Obtener JSON
        data = cache.get_json("forecast")
    """
    
    _instance: Optional['UnifiedCache'] = None
    
    def __new__(cls, config: Optional[CacheConfig] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: Optional[CacheConfig] = None):
        if self._initialized:
            return
        
        self.config = config or CacheConfig()
        self._cache = dc.Cache(self.config.cache_dir)
        self._metrics = CacheMetrics()
        
        # Crear directorio si no existe
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)
        
        self._initialized = True
        logger.info(f"🗃️ Caché inicializado: {self.config.cache_dir}, TTL={self.config.ttl_minutes}m")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Genera clavehash única."""
        components = [prefix] + [str(a) for a in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return hashlib.md5("_".join(components).encode()).hexdigest()
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """Verifica si una entrada ha expirado."""
        return datetime.now() - timestamp > timedelta(minutes=self.config.ttl_minutes)
    
    def _get_ttl_for_type(self, data_type: str) -> int:
        """Obtiene TTL específico por tipo de dato."""
        type_ttls = {
            "current_weather": self.config.current_weather_ttl,
            "forecast": self.config.forecast_ttl,
            "historical": self.config.historical_ttl,
            "radar": self.config.radar_ttl,
            "siata": self.config.siata_ttl,
        }
        return type_ttls.get(data_type, self.config.ttl_minutes)
    
    def get(self, key: str) -> Optional[Tuple[datetime, Any]]:
        """Obtiene valor del caché verificando TTL."""
        try:
            data = self._cache.get(key)
            if data is None:
                self._metrics.misses += 1
                return None
            
            timestamp, value = data
            
            # Verificar TTL específico si el dato tiene metadata
            if isinstance(data, dict) and "ttl_type" in data:
                ttl = self._get_ttl_for_type(data["ttl_type"])
                if datetime.now() - timestamp > timedelta(minutes=ttl):
                    self._cache.delete(key)
                    self._metrics.misses += 1
                    return None
            
            self._metrics.hits += 1
            return (timestamp, value)
            
        except Exception as e:
            logger.error(f"Error leyendo caché: {e}")
            self._metrics.errors += 1
            return None
    
    def set(self, key: str, value: Any, ttl_type: Optional[str] = None):
        """Guarda valor en caché con timestamp."""
        try:
            ttl = self._get_ttl_for_type(ttl_type) if ttl_type else self.config.ttl_minutes
            
            # Empaquetar con metadata de TTL
            if ttl_type:
                data = (datetime.now(), value, {"ttl_type": ttl_type, "ttl_minutes": ttl})
            else:
                data = (datetime.now(), value)
            
            self._cache.set(key, data)
            self._metrics.sets += 1
            
        except Exception as e:
            logger.error(f"Error guardando en caché: {e}")
            self._metrics.errors += 1
    
    def get_dataframe(self, key: str) -> Optional[Any]:
        """Obtiene DataFrame del caché."""
        result = self.get(key)
        if result is None:
            return None
        
        _, value = result
        
        try:
            if isinstance(value, str):
                # JSON serializado
                import pandas as pd
                return pd.read_json(value, orient='split')
            return value
        except Exception as e:
            logger.warning(f"Error deserializando DataFrame: {e}")
            return None
    
    def set_dataframe(self, key: str, df: Any, ttl_type: str = "current_weather"):
        """Guarda DataFrame en caché."""
        try:
            import pandas as pd
            serialized = df.to_json(orient='split')
            self.set(key, serialized, ttl_type=ttl_type)
        except Exception as e:
            logger.error(f"Error serializando DataFrame: {e}")
    
    def get_json(self, key: str) -> Optional[Dict]:
        """Obtiene JSON del caché."""
        result = self.get(key)
        if result is None:
            return None
        _, value = result
        
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return value if isinstance(value, dict) else None
    
    def set_json(self, key: str, data: Dict, ttl_type: str = "current_weather"):
        """Guarda JSON en caché."""
        try:
            serialized = json.dumps(data, default=str)
            self.set(key, serialized, ttl_type=ttl_type)
        except Exception as e:
            logger.error(f"Error serializando JSON: {e}")
    
    def delete(self, key: str):
        """Elimina entrada del caché."""
        try:
            self._cache.delete(key)
            self._metrics.deletes += 1
        except Exception as e:
            logger.error(f"Error eliminando del caché: {e}")
    
    def clear(self):
        """Limpia todo el caché."""
        self._cache.clear()
        logger.info("🗑️ Caché limpiado")
    
    def get_stats(self) -> Dict:
        """Obtiene estadísticas del caché."""
        cache_stats = self._cache._con.execute(
            "SELECT key, size FROM Cache WHERE size > 0"
        ).fetchall()
        
        return {
            "metrics": self._metrics.to_dict(),
            "entries": len(self._cache),
            "volume_bytes": self._cache.volume(),
            "directory": str(self._cache.directory),
            "config": {
                "ttl_minutes": self.config.ttl_minutes,
                "cache_dir": self.config.cache_dir
            }
        }


# Instancia global
_cache: Optional[UnifiedCache] = None


def get_cache(config: Optional[CacheConfig] = None) -> UnifiedCache:
    """Obtiene instancia global del caché."""
    global _cache
    if _cache is None:
        _cache = UnifiedCache(config)
    return _cache


def clear_cache():
    """Limpia el caché global."""
    if _cache:
        _cache.clear()