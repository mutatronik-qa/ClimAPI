"""Application use cases."""

from application.use_cases.weather import (
    GetCurrentWeather,
    GetForecast,
    GetHistoricalWeather,
)
from application.use_cases.combine import (
    CombineWeatherSources,
    GenerateQualityReport,
)

__all__ = [
    "GetCurrentWeather",
    "GetForecast",
    "GetHistoricalWeather",
    "CombineWeatherSources",
    "GenerateQualityReport",
]