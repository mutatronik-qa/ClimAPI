"""
Módulo para guardar y cargar datos meteorológicos.

Este módulo proporciona funciones para persistir los DataFrames
en formato CSV y cargarlos posteriormente.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import diskcache as dc
import hashlib
import json
from functools import wraps


def save_to_csv(
    df: pd.DataFrame,
    filepath: str,
    append: bool = False,
    include_timestamp: bool = False
) -> str:
    """
    Guarda un DataFrame en un archivo CSV.
    
    Args:
        df: DataFrame a guardar
        filepath: Ruta del archivo CSV (puede incluir o no la extensión .csv)
        append: Si es True, agrega los datos al archivo existente. Si es False, sobrescribe
        include_timestamp: Si es True, agrega un timestamp al nombre del archivo
    
    Returns:
        str: Ruta completa del archivo guardado
    """
    # Asegurar que el archivo tenga extensión .csv
    if not filepath.endswith('.csv'):
        filepath += '.csv'
    
    # Agregar timestamp si se solicita
    if include_timestamp:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path_obj = Path(filepath)
        filepath = f"{path_obj.stem}_{timestamp}{path_obj.suffix}"
    
    # Crear directorio si no existe
    path_obj = Path(filepath)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    
    # Guardar el DataFrame
    if append and path_obj.exists():
        # Modo append: leer el archivo existente, concatenar y guardar
        df_existing = pd.read_csv(filepath, index_col=0, parse_dates=True)
        df_combined = pd.concat([df_existing, df])
        # Eliminar duplicados basados en el índice
        df_combined = df_combined[~df_combined.index.duplicated(keep='last')]
        df_combined = df_combined.sort_index()
        df_combined.to_csv(filepath)
    else:
        # Modo write: guardar directamente
        df.to_csv(filepath)
    
    return filepath


def load_from_csv(filepath: str) -> pd.DataFrame:
    """
    Carga un DataFrame desde un archivo CSV.
    
    Args:
        filepath: Ruta del archivo CSV a cargar
    
    Returns:
        pd.DataFrame: DataFrame cargado con el índice 'time' como datetime
    """
    if not filepath.endswith('.csv'):
        filepath += '.csv'
    
    # Verificar que el archivo existe
    path_obj = Path(filepath)
    if not path_obj.exists():
        raise FileNotFoundError(f"El archivo {filepath} no existe")
    
    # Cargar el DataFrame
    df = pd.read_csv(filepath, index_col=0, parse_dates=True)
    
    return df


import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, cache_dir="cache", ttl_minutes=15):
        self.cache = dc.Cache(cache_dir)
        self.ttl = timedelta(minutes=ttl_minutes)
        logger.info(f"CacheManager inicializado. Directorio: {cache_dir}, TTL: {ttl_minutes} minutos.")

    def _generate_key(self, prefix, *args, **kwargs):
        # Genera una clave única basada en los argumentos
        key_components = [prefix] + [str(arg) for arg in args] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return hashlib.md5("_".join(key_components).encode('utf-8')).hexdigest()

    def get(self, key):
        data = self.cache.get(key)
        if data:
            timestamp, value = data
            if datetime.now() - timestamp < self.ttl:
                logger.debug(f"Cache hit para la clave: {key}")
                return value
            else:
                logger.debug(f"Cache expirada para la clave: {key}")
                self.cache.delete(key)
        logger.debug(f"Cache miss para la clave: {key}")
        return None

    def set(self, key, value):
        self.cache.set(key, (datetime.now(), value))
        logger.debug(f"Datos guardados en caché para la clave: {key}")

    def get_weather_data(self, latitude, longitude, timezone):
        key = self._generate_key("weather_raw", latitude, longitude, timezone)
        cached_data = self.get(key)
        if cached_data:
            return json.loads(cached_data)
        return None

    def set_weather_data(self, latitude, longitude, timezone, data):
        key = self._generate_key("weather_raw", latitude, longitude, timezone)
        self.set(key, json.dumps(data))

    def get_processed_data(self, latitude, longitude, timezone):
        key = self._generate_key("weather_processed", latitude, longitude, timezone)
        cached_data = self.get(key)
        if cached_data is not None:
            try:
                # Asumiendo que el DataFrame se guarda como JSON o similar
                # y necesita ser reconstruido. Para simplificar, si se guarda
                # como string JSON, se convierte de nuevo a DataFrame.
                # Esto puede requerir un formato específico de serialización/deserialización.
                # Por ahora, un ejemplo simple si se guarda como dict y se convierte a DF.
                return pd.read_json(cached_data, orient='split')
            except Exception as e:
                logger.error(f"Error al deserializar DataFrame de caché: {e}")
                return None
        return None

    def set_processed_data(self, latitude, longitude, timezone, dataframe):
        key = self._generate_key("weather_processed", latitude, longitude, timezone)
        # Guardar DataFrame como JSON string para compatibilidad
        self.set(key, dataframe.to_json(orient='split'))

    def clear(self):
        self.cache.clear()
        logger.info("Caché limpiada.")
        return {"message": "Cache cleared", "timestamp": datetime.now().isoformat()}

    def get_stats(self):
        stats = {
            "entries": len(self.cache),
            "size": self.cache.volume(), # Retorna el tamaño en bytes
            "path": self.cache.directory,
            "ttl_minutes": self.ttl.total_seconds() / 60
        }
        logger.info(f"Estadísticas de caché: {stats}")
        return stats

def cache_weather_data(func):
    def wrapper(*args, **kwargs):
        # Asumiendo que el primer argumento es 'self' si es un método de clase,
        # o que los argumentos relevantes para la clave están en args/kwargs.
        # Para este ejemplo, simplificamos asumiendo que los args son lat, lon, tz.
        latitude = kwargs.get('latitude') or args[0]
        longitude = kwargs.get('longitude') or args[1]
        timezone = kwargs.get('timezone') or args[2] if len(args) > 2 else "America/Bogota"

        cache_manager = CacheManager() # Esto debería ser una instancia global o pasada

        cached_data = cache_manager.get_weather_data(latitude, longitude, timezone)
        if cached_data:
            return cached_data

        result = func(*args, **kwargs)
        cache_manager.set_weather_data(latitude, longitude, timezone, result)
        return result
    return wrapper

