from fastapi import APIRouter
from typing import List, Dict, Any
from ...models import LocationInfo
from ...config import settings

router = APIRouter(prefix="/api/v1/locations", tags=["locations"])

@router.get("/default", response_model=LocationInfo)
async def get_default_location():
    """
    Retorna la ubicación por defecto (Medellín)
    """
    return LocationInfo(
        latitude=settings.DEFAULT_LAT,
        longitude=settings.DEFAULT_LON,
        timezone=settings.DEFAULT_TIMEZONE,
        city=settings.DEFAULT_CITY,
        country="Colombia"
    )

@router.get("/popular", response_model=List[LocationInfo])
async def get_popular_locations():
    """
    Retorna una lista de ubicaciones populares en Colombia
    """
    popular_locations = [
        {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota",
            "city": "Medellín",
            "country": "Colombia"
        },
        {
            "latitude": 4.711,
            "longitude": -74.072,
            "timezone": "America/Bogota",
            "city": "Bogotá",
            "country": "Colombia"
        },
        {
            "latitude": 10.964,
            "longitude": -74.796,
            "timezone": "America/Bogota",
            "city": "Barranquilla",
            "country": "Colombia"
        },
        {
            "latitude": 3.452,
            "longitude": -76.532,
            "timezone": "America/Bogota",
            "city": "Cali",
            "country": "Colombia"
        },
        {
            "latitude": 7.125,
            "longitude": -73.126,
            "timezone": "America/Bogota",
            "city": "Bucaramanga",
            "country": "Colombia"
        },
        {
            "latitude": 1.214,
            "longitude": -77.281,
            "timezone": "America/Bogota",
            "city": "Pasto",
            "country": "Colombia"
        },
        {
            "latitude": 9.304,
            "longitude": -75.144,
            "timezone": "America/Bogota",
            "city": "Sincelejo",
            "country": "Colombia"
        },
        {
            "latitude": 8.766,
            "longitude": -75.847,
            "timezone": "America/Bogota",
            "city": "Montería",
            "country": "Colombia"
        },
        {
            "latitude": 4.134,
            "longitude": -73.635,
            "timezone": "America/Bogota",
            "city": "Villavicencio",
            "country": "Colombia"
        },
        {
            "latitude": 6.253,
            "longitude": -75.564,
            "timezone": "America/Bogota",
            "city": "Envigado",
            "country": "Colombia"
        }
    ]
    
    return [LocationInfo(**location) for location in popular_locations]

@router.get("/search")
async def search_locations(query: str = "", limit: int = 10):
    """
    Busca ubicaciones por nombre (implementación básica)
    """
    # Esta es una implementación básica. En producción, se podría usar
    # una API de geocodificación como Nominatim o Google Places
    popular_locations = await get_popular_locations()
    
    if not query:
        return popular_locations[:limit]
    
    # Búsqueda simple por nombre de ciudad
    filtered_locations = [
        location for location in popular_locations 
        if query.lower() in location.city.lower()
    ]
    
    return filtered_locations[:limit]