"""Infrastructure layer - adapters and implementations."""

from infrastructure.adapters.sources.open_meteo import OpenMeteoAdapter
from infrastructure.adapters.sources.registry import SourceRegistry, initialize_default_sources
from infrastructure.adapters.cache.file_cache import FileCacheAdapter, MemoryCacheAdapter
from infrastructure.adapters.storage.csv_storage import CSVStorageAdapter, ParquetStorageAdapter
from infrastructure.adapters.processing.weather_processor import WeatherDataProcessor, DataQualityAnalyzer

__all__ = [
    "OpenMeteoAdapter",
    "SourceRegistry",
    "initialize_default_sources",
    "FileCacheAdapter",
    "MemoryCacheAdapter",
    "CSVStorageAdapter",
    "ParquetStorageAdapter",
    "WeatherDataProcessor",
    "DataQualityAnalyzer",
]