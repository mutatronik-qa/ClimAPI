"""
Módulo para consumir datos de la API Open-Meteo
API Gratuita sin límite de rate limiting
"""

import requests
import logging
from typing import Dict, Any, Tuple
from datetime import datetime
from pydantic import BaseModel, validator

logger = logging.getLogger(__name__)

class WeatherDataRaw(BaseModel):
    """Modelo para datos crudos de Open-Meteo"""
    latitude: float
    longitude: float
    generationtime_ms: float
    utc_offset_seconds: int
    timezone: str
    hourly: Dict[str, Any]
    
    @validator('latitude')
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError('Latitud debe estar entre -90 y 90')
        return v
    
    @validator('longitude')
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError('Longitud debe estar entre -180 y 180')
        return v

def validate_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """
    Valida que las coordenadas sean válidas
    
    Args:
        latitude: Latitud (-90 a 90)
        longitude: Longitud (-180 a 180)
    
    Returns:
        Tupla (latitude, longitude) validada
    
    Raises:
        ValueError: Si las coordenadas son inválidas
    """
    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitud inválida: {latitude}. Debe estar entre -90 y 90")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitud inválida: {longitude}. Debe estar entre -180 y 180")
    
    return latitude, longitude

def get_weather_data(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
    hourly_vars: list = None,
    days: int = 10
) -> Dict[str, Any]:
    """
    Obtiene datos meteorológicos de Open-Meteo
    
    Args:
        latitude: Latitud de la ubicación
        longitude: Longitud de la ubicación
        timezone: Zona horaria (por defecto "auto")
        hourly_vars: Variables horarias a obtener
        days: Días de pronóstico (1-16)
    
    Returns:
        Dict con datos meteorológicos completos
    
    Raises:
        Exception: Si hay error en la API
    """
    
    if hourly_vars is None:
        hourly_vars = [
            "temperature_2m",
            "relative_humidity_2m",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "visibility"
        ]
    
    # Validar coordenadas
    validate_coordinates(latitude, longitude)
    
    # Construir URL
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
        "hourly": ",".join(hourly_vars),
        "forecast_days": min(days, 16)  # Máximo 16 días
    }
    
    try:
        logger.info(f"🌐 Solicitando datos para Lat: {latitude}, Lon: {longitude}")
        
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Validar estructura
        WeatherDataRaw(**data)
        
        logger.info(f"✅ Datos obtenidos exitosamente")
        return data
        
    except requests.exceptions.Timeout:
        logger.error("⏱️ Timeout: La API tardó demasiado en responder")
        raise TimeoutError("API Open-Meteo tardó demasiado en responder")
        
    except requests.exceptions.ConnectionError:
        logger.error("🔌 Error de conexión con Open-Meteo")
        raise ConnectionError("No se pudo conectar a Open-Meteo")
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ Error HTTP: {e.response.status_code}")
        raise Exception(f"Error en API Open-Meteo: {e.response.status_code}")
        
    except Exception as e:
        logger.error(f"❌ Error inesperado: {str(e)}")
        raise

def get_weather_by_city_name(
    city_name: str,
    timezone: str = "auto"
) -> Dict[str, Any]:
    """
    Obtiene datos meteorológicos usando nombre de ciudad
    (requiere geocodificación)
    
    Args:
        city_name: Nombre de la ciudad
        timezone: Zona horaria
    
    Returns:
        Dict con datos meteorológicos
    """
    
    # Geocodificar ciudad
    geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "es",
        "format": "json"
    }
    
    try:
        logger.info(f"🔍 Geocodificando ciudad: {city_name}")
        response = requests.get(geocode_url, params=params, timeout=10)
        response.raise_for_status()
        
        results = response.json().get("results", [])
        
        if not results:
            raise ValueError(f"Ciudad no encontrada: {city_name}")
        
        location = results[0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        timezone = location.get("timezone", timezone)
        
        logger.info(f"✅ Ciudad encontrada: {location.get('name')}, {location.get('country')}")
        
        # Obtener datos meteorológicos
        return get_weather_data(latitude, longitude, timezone)
        
    except Exception as e:
        logger.error(f"❌ Error geocodificando: {str(e)}")
        raise

