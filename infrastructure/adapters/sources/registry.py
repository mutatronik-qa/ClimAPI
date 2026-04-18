"""Weather source registry - manages all available sources."""
from typing import Optional, Dict, Type
import logging

from domain.interfaces.sources import WeatherDataSource
from infrastructure.adapters.sources.open_meteo import OpenMeteoAdapter

logger = logging.getLogger(__name__)


class SourceRegistry:
    """
    Registry for weather data sources.
    
    Manages registration and retrieval of weather sources.
    Follows the Service Locator pattern.
    """
    
    _sources: Dict[str, WeatherDataSource] = {}
    _source_classes: Dict[str, Type[WeatherDataSource]] = {}
    
    @classmethod
    def register(cls, source: WeatherDataSource) -> None:
        """Register a source instance."""
        cls._sources[source.name] = source
        logger.info(f"Registered weather source: {source.name}")
    
    @classmethod
    def register_class(cls, name: str, source_class: Type[WeatherDataSource]) -> None:
        """Register a source class for lazy instantiation."""
        cls._source_classes[name] = source_class
        logger.info(f"Registered weather source class: {name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[WeatherDataSource]:
        """Get a source by name."""
        if name in cls._sources:
            return cls._sources[name]
        
        if name in cls._source_classes:
            source = cls._source_classes[name]()
            cls._sources[name] = source
            return source
        
        return None
    
    @classmethod
    def get_all(cls) -> list[WeatherDataSource]:
        """Get all registered sources."""
        return list(cls._sources.values())
    
    @classmethod
    def list_sources(cls) -> list[dict]:
        """List all available sources with their info."""
        result = []
        for source in cls._sources.values():
            result.append({
                "name": source.name,
                "display_name": source.info.display_name,
                "requires_api_key": source.info.requires_api_key,
                "is_free": source.info.is_free
            })
        return result
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered sources."""
        cls._sources.clear()
        cls._source_classes.clear()


def initialize_default_sources() -> None:
    """Initialize default weather sources."""
    SourceRegistry.register(OpenMeteoAdapter())
    
    logger.info("Default sources initialized")