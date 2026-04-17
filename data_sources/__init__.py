# src/data_sources/__init__.py
"""Módulo de fuentes de datos meteorológicas."""

from .siata import SIATAClient
from .open_meteo import get_weather_data
from .openweathermap import OpenWeatherMap
from .meteoblue import MeteoBlueService

__all__ = [
    "SIATAClient",
    "RadarIDEAMClient",
    "get_weather_data",
    "OpenWeatherMap",
    "MeteoBlueService",
]


def __getattr__(name: str):
    if name == "RadarIDEAMClient":
        from .radar_ideam import RadarIDEAMClient
        return RadarIDEAMClient
    raise AttributeError(f"module {__name__} has no attribute {name}")
