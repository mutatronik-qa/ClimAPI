"""
FastAPI Main Application - Clean, minimal, production-ready.
"""
import logging
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ClimAPI - Weather Service",
    description="Simple weather API with multiple sources",
    version="2.0.0",
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

# Models
class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"


class WeatherResponse(BaseModel):
    location: Location
    data: dict
    fetched_at: str


# Import service
from backend.weather_service import get_weather_service, WeatherService

# Get service
service = get_weather_service()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ClimAPI v2.0",
        "docs": "/docs",
        "version": "2.0.0"
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "climapi",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/sources")
async def list_sources():
    """List all available weather sources."""
    status = service.get_sources_status()
    
    return {
        "sources": [
            {
                "name": s["name"],
                "status": s["status"],
                "response_time": round(s["response_time"], 2)
            }
            for s in status
        ]
    }


@app.post("/weather", response_model=WeatherResponse)
async def get_weather(
    location: Location,
    source: Optional[str] = Query(None, description="Specific source (open-meteo, openweathermap, etc.)"),
    use_cache: bool = Query(True, description="Use cached data")
):
    """
    Get weather data for a location.
    
    - If `source` is specified: returns data from that source only
    - If `source` is not specified: calls all sources and returns merged result
    """
    try:
        result = service.get_weather(
            lat=location.latitude,
            lon=location.longitude,
            source=source,
            use_cache=use_cache,
            timezone=location.timezone
        )
        
        return WeatherResponse(
            location=location,
            data=result,
            fetched_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting weather: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/weather/current")
async def get_current_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    source: Optional[str] = Query(None),
    timezone: str = Query("America/Bogota")
):
    """Get current weather (GET method)."""
    try:
        result = service.get_weather(
            lat=lat,
            lon=lon,
            source=source,
            timezone=timezone
        )
        
        return {
            "location": {"latitude": lat, "longitude": lon, "timezone": timezone},
            "data": result,
            "fetched_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return {
        "cached_entries": len(service._cache),
        "cache_ttl": service.cache_ttl
    }


@app.delete("/cache")
async def clear_cache():
    """Clear the weather cache."""
    service.clear_cache()
    return {"message": "Cache cleared"}


# Run directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)