"""
Módulo para almacenamiento en caché y persistencia de datos
"""

import pandas as pd
import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib

logger = logging.getLogger(__name__)

class CacheManager:
    """Gestor de caché en memoria y disco"""
    
    def __init__(self, ttl_minutes: int = 15, cache_dir: str = "cache"):
        self.ttl_minutes = ttl_minutes
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_cache: Dict[str, tuple] = {}
        
        logger.info(f"📦 CacheManager inicializado (TTL: {ttl_minutes} min)")
    
    def _get_cache_key(self, latitude: float, longitude: float, timezone: str) -> str:
        """Genera clave de caché única"""
        key_str = f"{latitude}_{longitude}_{timezone}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_processed_data(
        self, 
        latitude: float, 
        longitude: float, 
        timezone: str
    ) -> Optional[pd.DataFrame]:
        """
        Obtiene datos del caché si están frescos
        
        Args:
            latitude: Latitud
            longitude: Longitud
            timezone: Zona horaria
        
        Returns:
            DataFrame si existe y es fresco, None si no
        """
        
        cache_key = self._get_cache_key(latitude, longitude, timezone)
        
        # Verificar caché en memoria
        if cache_key in self.memory_cache:
            df, timestamp = self.memory_cache[cache_key]
            age = datetime.now() - timestamp
            
            if age < timedelta(minutes=self.ttl_minutes):
                logger.info(f"📦 Datos en caché válidos ({age.seconds}s de antigüedad)")
                return df
            else:
                logger.info(f"⏰ Caché expirado ({age.seconds}s)")
                del self.memory_cache[cache_key]
        
        # Verificar caché en disco
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        if cache_file.exists():
            try:
                df = pd.read_parquet(cache_file)
                file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
                
                if file_age < timedelta(minutes=self.ttl_minutes):
                    logger.info(f"💾 Datos recuperados de disco ({file_age.seconds}s de antigüedad)")
                    self.memory_cache[cache_key] = (df, datetime.now())
                    return df
                else:
                    logger.info(f"⏰ Caché en disco expirado")
                    cache_file.unlink()
            except Exception as e:
                logger.error(f"❌ Error leyendo caché: {e}")
        
        return None
    
    def set_processed_data(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        df: pd.DataFrame
    ) -> None:
        """
        Guarda datos en caché
        
        Args:
            latitude: Latitud
            longitude: Longitud
            timezone: Zona horaria
            df: DataFrame a guardar
        """
        
        cache_key = self._get_cache_key(latitude, longitude, timezone)
        
        # Guardar en memoria
        self.memory_cache[cache_key] = (df, datetime.now())
        
        # Guardar en disco
        try:
            cache_file = self.cache_dir / f"{cache_key}.parquet"
            df.to_parquet(cache_file)
            logger.info(f"💾 Datos guardados en caché")
        except Exception as e:
            logger.error(f"❌ Error guardando caché: {e}")
    
    def clear(self) -> None:
        """Limpia todo el caché"""
        self.memory_cache.clear()
        
        for file in self.cache_dir.glob("*.parquet"):
            file.unlink()
        
        logger.info("🗑️ Caché limpiado")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del caché"""
        cache_files = list(self.cache_dir.glob("*.parquet"))
        
        return {
            "cache_entries": len(self.memory_cache),
            "disk_files": len(cache_files),
            "cache_dir": str(self.cache_dir),
            "ttl_minutes": self.ttl_minutes
        }

def save_to_csv(df: pd.DataFrame, filepath: str) -> None:
    """
    Guarda DataFrame en CSV
    
    Args:
        df: DataFrame a guardar
        filepath: Ruta del archivo
    """
    
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(filepath)
        logger.info(f"✅ Archivo guardado: {filepath}")
    except Exception as e:
        logger.error(f"❌ Error guardando CSV: {e}")
        raise

def save_to_json(data: Dict[str, Any], filepath: str) -> None:
    """
    Guarda datos en JSON
    
    Args:
        data: Dict a guardar
        filepath: Ruta del archivo
    """
    
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        logger.info(f"✅ Archivo guardado: {filepath}")
    except Exception as e:
        logger.error(f"❌ Error guardando JSON: {e}")
        raise

