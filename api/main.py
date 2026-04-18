"""
FastAPI Main Application
Clean, minimal, production-ready API.
"""
import logging
from datetime import datetime
from typing import Optional

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
    description="Clean Architecture Weather API with Strategy Pattern",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================
# Models
# ====================

class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"


class WeatherResponse(BaseModel):
    location: Location
    data: dict
    fetched_at: str


# ====================
# Initialize Service
# ====================

from services import get_weather_service

# ====================
# Endpoints
# ====================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ClimAPI v3.0 - Clean Architecture",
        "docs": "/docs",
        "version": "3.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check - verifies all sources."""
    service = get_weather_service()
    sources_status = service.get_sources_status()
    
    healthy_sources = sum(1 for s in sources_status if s.get("is_available", False))
    
    return {
        "status": "healthy" if healthy_sources > 0 else "degraded",
        "timestamp": datetime.now().isoformat(),
        "sources": {
            "total": len(sources_status),
            "available": healthy_sources,
            "details": sources_status
        }
    }


@app.get("/sources")
async def list_sources():
    """List all available weather sources."""
    service = get_weather_service()
    status = service.get_sources_status()
    
    return {
        "sources": [
            {
                "name": s["name"],
                "is_available": s.get("is_available", False),
                "is_free": s.get("is_free", False),
                "response_time": round(s.get("response_time", 0), 3)
            }
            for s in status
        ]
    }


@app.post("/weather", response_model=WeatherResponse)
async def get_weather(
    location: Location,
    source: Optional[str] = Query(None, description="Source name (open-meteo, siata, etc.)"),
    use_cache: bool = Query(True, description="Use cached data")
):
    """Get current weather for a location."""
    try:
        service = get_weather_service()
        
        weather_data = service.get_current_weather(
            lat=location.latitude,
            lon=location.longitude,
            source_name=source,
            use_cache=use_cache,
            timezone=location.timezone
        )
        
        return WeatherResponse(
            location=location,
            data=weather_data.model_dump() if hasattr(weather_data, 'model_dump') else {
                "timestamp": weather_data.timestamp.isoformat() if hasattr(weather_data.timestamp, 'isoformat') else str(weather_data.timestamp),
                "temperature": weather_data.temperature,
                "humidity": weather_data.humidity,
                "precipitation": weather_data.precipitation,
                "wind_speed": weather_data.wind_speed,
                "source": weather_data.source
            },
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
    service = get_weather_service()
    
    weather_data = service.get_current_weather(
        lat=lat,
        lon=lon,
        source_name=source,
        timezone=timezone
    )
    
    return {
        "location": {"latitude": lat, "longitude": lon, "timezone": timezone},
        "data": {
            "timestamp": weather_data.timestamp.isoformat() if hasattr(weather_data.timestamp, 'isoformat') else str(weather_data.timestamp),
            "temperature": weather_data.temperature,
            "humidity": weather_data.humidity,
            "precipitation": weather_data.precipitation,
            "wind_speed": weather_data.wind_speed,
            "source": weather_data.source
        },
        "fetched_at": datetime.now().isoformat()
    }


@app.get("/weather/forecast")
async def get_forecast(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(7, ge=1, le=16),
    source: Optional[str] = Query(None),
    timezone: str = Query("America/Bogota")
):
    """Get weather forecast."""
    service = get_weather_service()
    
    forecast_data = service.get_forecast(
        lat=lat,
        lon=lon,
        days=days,
        source_name=source,
        timezone=timezone
    )
    
    return {
        "location": {"latitude": lat, "longitude": lon, "timezone": timezone},
        "data": [
            {
                "timestamp": d.timestamp.isoformat() if hasattr(d.timestamp, 'isoformat') else str(d.timestamp),
                "temperature": d.temperature,
                "humidity": d.humidity,
                "precipitation": d.precipitation,
                "wind_speed": d.wind_speed,
                "source": d.source
            }
            for d in forecast_data
        ],
        "count": len(forecast_data),
        "fetched_at": datetime.now().isoformat()
    }


@app.get("/weather/historical")
async def get_historical(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    source: Optional[str] = Query(None),
    timezone: str = Query("America/Bogota")
):
    """Get historical weather data."""
    service = get_weather_service()
    
    try:
        from datetime import datetime as dt
        start = dt.strptime(start_date, "%Y-%m-%d")
        end = dt.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    historical_data = service.get_historical(
        lat=lat,
        lon=lon,
        start_date=start,
        end_date=end,
        source_name=source,
        timezone=timezone
    )
    
    return {
        "location": {"latitude": lat, "longitude": lon, "timezone": timezone},
        "start_date": start_date,
        "end_date": end_date,
        "data": [
            {
                "timestamp": d.timestamp.isoformat() if hasattr(d.timestamp, 'isoformat') else str(d.timestamp),
                "temperature": d.temperature,
                "humidity": d.humidity,
                "precipitation": d.precipitation,
                "wind_speed": d.wind_speed,
                "source": d.source
            }
            for d in historical_data
        ],
        "count": len(historical_data),
        "fetched_at": datetime.now().isoformat()
    }


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    service = get_weather_service()
    return service.cache.get_stats()


@app.delete("/cache")
async def clear_cache():
    """Clear the weather cache."""
    service = get_weather_service()
    service.clear_cache()
    return {"message": "Cache cleared"}


# Run directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)