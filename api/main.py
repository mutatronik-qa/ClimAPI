"""
API REST de ClimAPI con FastAPI.

Endpoints:
- /api/v1/health - Health check
- /api/v1/weather/current - Datos actuales
- /api/v1/weather/forecast - Pronóstico
- /api/v1/sources - Lista de fuentes
- /api/v1/cache - Gestión de caché
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    timezone: str = "America/Bogota"


class WeatherData(BaseModel):
    time: str
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float


class WeatherResponse(BaseModel):
    location: LocationRequest
    data: List[WeatherData]
    source: str
    timestamp: str


def create_app() -> FastAPI:
    """Factory para crear la aplicación FastAPI."""
    
    app = FastAPI(
        title="ClimAPI",
        description="API meteorológica con múltiples fuentes de datos",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {"message": "ClimAPI v1.0.0", "docs": "/docs"}
    
    @app.get("/api/v1/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "climapi"}
    
    @app.get("/api/v1/sources")
    async def list_sources():
        """Lista todas las fuentes de datos disponibles."""
        from core import list_sources as core_list_sources
        return {"sources": core_list_sources()}
    
    @app.get("/api/v1/cache/stats")
    async def cache_stats():
        """Estadísticas del caché."""
        from core import get_cache
        cache = get_cache()
        return cache.get_stats()
    
    @app.delete("/api/v1/cache")
    async def clear_cache():
        """Limpia el caché."""
        from core import get_cache
        cache = get_cache()
        cache.clear()
        return {"message": "Caché limpiado"}
    
    @app.post("/api/v1/weather/current", response_model=WeatherResponse)
    async def get_current_weather(location: LocationRequest):
        """Obtiene datos meteorológicos actuales."""
        from core import get_weather, get_source
        
        # Validar coordenadas
        if not -90 <= location.latitude <= 90:
            raise HTTPException(status_code=400, detail="Latitud inválida")
        if not -180 <= location.longitude <= 180:
            raise HTTPException(status_code=400, detail="Longitud inválida")
        
        # Usar Open-Meteo por defecto (gratuito)
        try:
            source = get_source("open-meteo")
            data = source.fetch_current(
                location.latitude,
                location.longitude,
                timezone=location.timezone
            )
            
            # Convertir a formato de respuesta
            weather_items = []
            for item in data.get("data", [])[:24]:
                weather_items.append(WeatherData(
                    time=item.get("time", ""),
                    temperature=item.get("temperature", 0),
                    humidity=item.get("humidity", 0),
                    precipitation=item.get("precipitation", 0),
                    wind_speed=item.get("wind_speed", 0)
                ))
            
            return WeatherResponse(
                location=location,
                data=weather_items,
                source="open-meteo",
                timestamp=data.get("timestamp", "")
            )
            
        except Exception as e:
            logger.error(f"Error obteniendo datos: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/v1/weather/{source}")
    async def get_weather_by_source(
        source: str,
        lat: float = Query(...),
        lon: float = Query(...),
        days: int = Query(7, ge=1, le=16)
    ):
        """Obtiene datos de una fuente específica."""
        from core import get_source, get_forecast
        
        try:
            source_instance = get_source(source)
            if source_instance is None:
                raise HTTPException(status_code=404, detail=f"Fuente no encontrada: {source}")
            
            data = source_instance.fetch_current(lat, lon)
            return {"source": source, "data": data}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


# App instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)