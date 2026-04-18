"""Infrastructure adapters - sources."""

from infrastructure.adapters.sources.open_meteo import OpenMeteoAdapter
from infrastructure.adapters.sources.registry import SourceRegistry, initialize_default_sources

__all__ = ["OpenMeteoAdapter", "SourceRegistry", "initialize_default_sources"]