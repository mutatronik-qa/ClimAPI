"""
Implementación de Open-Meteo como fuente de datos.

API gratuita sin rate limiting.
Usa la clase base BaseWeatherSource.
"""

import requests
import logging
from typing import Dict, Any, Optional
import pandas as pd
from datetime import datetime

from core.source_base import BaseWeatherSource
from processing.data_normalizer import DataNormalizer

logger = logging.getLogger(__name__)


class OpenMeteoSource(BaseWeatherSource):
    """
    Fuente de datos Open-Meteo.
    API gratuita sin necesidad de API key.
    """
    
    name = "open-meteo"
    base_url = "https://api.open-meteo.com/v1/forecast"
    requires_api_key = False
    is_free = True
    ttl_default = 900  # 15 minutos
    
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self._timeout = self.config.get("timeout", 10)
    
    def _fetch_raw(self, latitude: float, longitude: float, **kwargs) -> Dict[str, Any]:
        """
        Obtiene datos crudos de Open-Meteo.
        
        Variables solicitadas:
        - temperature_2m: Temperatura a 2m
        - relative_humidity_2m: Humedad relativa
        - precipitation: Precipitación
        - weather_code: Código de clima
        - wind_speed_10m: Velocidad del viento
        - wind_direction_10m: Dirección del viento
        - surface_pressure: Presión superficial
        - cloud_cover: Nubosidad
        - dew_point_2m: Punto de rocío
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": kwargs.get("timezone", "auto"),
            "hourly": ",".join([
                "temperature_2m",
                "relative_humidity_2m", 
                "precipitation",
                "weather_code",
                "wind_speed_10m",
                "wind_direction_10m",
                "surface_pressure",
                "cloud_cover",
                "dew_point_2m"
            ]),
            "forecast_days": min(kwargs.get("days", 7), 16)
        }
        
        response = requests.get(self.base_url, params=params, timeout=self._timeout)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"✅ Datos obtenidos de Open-Meteo para {latitude}, {longitude}")
        
        return data
    
    def _normalize(self, raw_data: Dict, latitude: float, longitude: float, **kwargs) -> Dict[str, Any]:
        """
        Normaliza los datos al esquema unificado.
        """
        hourly = raw_data.get("hourly", {})
        times = hourly.get("time", [])
        
        if not times:
            return {"data": [], "source": self.name, "timestamp": datetime.now().isoformat()}
        
        df = pd.DataFrame({
            "timestamp": pd.to_datetime(times, utc=True),
            "temperatura_c": hourly.get("temperature_2m", []),
            "humedad_porcentaje": hourly.get("relative_humidity_2m", []),
            "precipitacion_mm": hourly.get("precipitation", []),
            "velocidad_viento_kmh": [v * 3.6 if v else None for v in hourly.get("wind_speed_10m", [])],
            "direccion_viento_grados": hourly.get("wind_direction_10m", []),
            "presion_hpa": hourly.get("surface_pressure", []),
            "nubosidad_porcentaje": hourly.get("cloud_cover", []),
            "punto_rocio_c": hourly.get("dew_point_2m", []),
        })
        
        df["source"] = self.name
        df["latitude"] = latitude
        df["longitude"] = longitude
        
        return {
            "data": df.to_dict(orient="records"),
            "source": self.name,
            "timestamp": datetime.now().isoformat(),
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": kwargs.get("timezone", "America/Bogota")
            }
        }
    
    def fetch_forecast(self, latitude: float, longitude: float, days: int = 7, **kwargs) -> Dict[str, Any]:
        """
        Override para obtener pronóstico diario.
        """
        # Open-Meteo ya incluye forecast en la respuesta hourly
        return self.fetch_current(latitude, longitude, days=days, **kwargs)
    
    def get_current_conditions(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Obtiene solo las condiciones actuales (última hora).
        """
        data = self.fetch_current(latitude, longitude, days=1)
        
        if data.get("data"):
            return data["data"][-1]  # Último registro
        
        return {}


# Auto-registro en el factory
from core.source_base import WeatherSourceFactory
WeatherSourceFactory.register(OpenMeteoSource, "open-meteo")


# Alias para compatibilidad con código existente
def get_weather_data(
    latitude: float,
    longitude: float,
    timezone: str = "auto",
    hourly_vars: list = None,
    days: int = 10
) -> Dict[str, Any]:
    """
    Función de compatibilidad con código existente.
    Obtiene datos meteorológicos de Open-Meteo.
    """
    source = OpenMeteoSource()
    return source.fetch_current(latitude, longitude, timezone=timezone, days=days)


def validate_coordinates(latitude: float, longitude: float):
    """
    Valida coordenadas geográficas.
    """
    if not -90 <= latitude <= 90:
        raise ValueError(f"Latitud inválida: {latitude}")
    if not -180 <= longitude <= 180:
        raise ValueError(f"Longitud inválida: {longitude}")
    return True