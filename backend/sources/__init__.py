"""Weather data sources - all return standardized format."""

from backend.sources.open_meteo import get_weather as get_open_meteo
from backend.sources.openweathermap import get_weather as get_openweathermap
from backend.sources.meteoblue import get_weather as get_meteoblue
from backend.sources.siata import get_weather as get_siata
from backend.sources.radar_ideam import get_weather as get_radar_ideam

__all__ = [
    "get_open_meteo",
    "get_openweathermap", 
    "get_meteoblue",
    "get_siata",
    "get_radar_ideam",
]


def get_all_sources():
    """Return dict of all available source functions."""
    return {
        "open-meteo": get_open_meteo,
        "openweathermap": get_openweathermap,
        "meteoblue": get_meteoblue,
        "siata": get_siata,
        "ideam_radar": get_radar_ideam,
    }


# Priority order (first that works is used)
PRIORITY_SOURCES = [
    "open-meteo",      # FREE - always available
    "openweathermap",  # Requires API key
    "meteoblue",       # Requires API key
]