"""
Módulo para procesar y transformar datos meteorológicos
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Mapeo de códigos WMO a descripciones
WMO_CODES = {
    0: "Cielo despejado",
    1: "Nublado parcialmente",
    2: "Nublado parcialmente",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna densa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    71: "Nieve ligera",
    73: "Nieve moderada",
    75: "Nieve intensa",
    77: "Granos de nieve",
    80: "Chubascos de lluvia ligeros",
    81: "Chubascos de lluvia moderados",
    82: "Chubascos de lluvia intensos",
    85: "Chubascos de nieve ligeros",
    86: "Chubascos de nieve intensos",
    95: "Tormenta",
    96: "Tormenta con granizo ligero",
    99: "Tormenta con granizo"
}

def process_weather_data(api_response: Dict[str, Any]) -> pd.DataFrame:
    """
    Procesa datos crudos de Open-Meteo a DataFrame limpio
    
    Args:
        api_response: Respuesta cruda de la API
    
    Returns:
        DataFrame con datos procesados
    """
    
    try:
        logger.info("⚙️ Procesando datos meteorológicos...")
        
        # Extraer datos
        hourly = api_response.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        humidity = hourly.get("relative_humidity_2m", [])
        precipitation = hourly.get("precipitation", [])
        weather_code = hourly.get("weather_code", [])
        wind_speed = hourly.get("wind_speed_10m", [])
        visibility = hourly.get("visibility", [])
        
        # Crear DataFrame
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(times),
            "temperatura_c": np.array(temps, dtype=float),
            "humedad_porcentaje": np.array(humidity, dtype=float),
            "precipitacion_mm": np.array(precipitation, dtype=float),
            "codigo_clima": np.array(weather_code, dtype=int),
            "velocidad_viento_kmh": np.array(wind_speed, dtype=float),
            "visibilidad_m": np.array(visibility, dtype=float)
        })
        
        # Agregar descripción del clima
        df["descripcion_clima"] = df["codigo_clima"].map(
            lambda x: WMO_CODES.get(x, "Desconocido")
        )
        
        # Establecer timestamp como índice
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        
        logger.info(f"✅ {len(df)} registros procesados")
        
        return df
        
    except KeyError as e:
        logger.error(f"❌ Campo faltante en respuesta: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Error procesando datos: {str(e)}")
        raise

def calculate_statistics(df: pd.DataFrame) -> Dict[str, float]:
    """
    Calcula estadísticas de los datos meteorológicos
    
    Args:
        df: DataFrame con datos procesados
    
    Returns:
        Dict con estadísticas
    """
    
    return {
        "temp_promedio": float(df["temperatura_c"].mean()),
        "temp_maxima": float(df["temperatura_c"].max()),
        "temp_minima": float(df["temperatura_c"].min()),
        "humedad_promedio": float(df["humedad_porcentaje"].mean()),
        "precipitacion_total": float(df["precipitacion_mm"].sum()),
        "viento_promedio": float(df["velocidad_viento_kmh"].mean()),
        "viento_maximo": float(df["velocidad_viento_kmh"].max())
    }

def aggregate_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega datos cada hora"""
    return df.resample('H').mean()

def aggregate_by_day(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega datos cada día"""
    return df.resample('D').agg({
        "temperatura_c": ["mean", "max", "min"],
        "humedad_porcentaje": "mean",
        "precipitacion_mm": "sum",
        "velocidad_viento_kmh": "mean"
    })

def detect_anomalies(df: pd.DataFrame, column: str, threshold: float = 2.0) -> pd.DataFrame:
    """
    Detecta anomalías usando Z-score
    
    Args:
        df: DataFrame
        column: Columna a analizar
        threshold: Umbral de Z-score (default 2.0)
    
    Returns:
        DataFrame con columna de anomalías
    """
    
    mean = df[column].mean()
    std = df[column].std()
    
    df["anomalia"] = np.abs((df[column] - mean) / std) > threshold
    
    return df

