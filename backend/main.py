"""
FastAPI Main Application - Consolidated
Minimal - only defines endpoints, uses weather_service.
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
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ClimAPI",
    description="Weather API - Single source of truth",
    version="3.0.0",
    docs_url="/docs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import service (single source of truth)
from backend.weather_service import get_service


# ====================
# Models
# ====================

class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = "America/Bogota"


# ====================
# Endpoints
# ====================

@app.get("/")
async def root():
    return {"message": "ClimAPI v3.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    """Check health of all sources."""
    service = get_service()
    status = service.get_sources_status()

    available = sum(1 for s in status if s.get("available"))

    return {
        "status": "healthy" if available > 0 else "degraded",
        "timestamp": datetime.now().isoformat(),
        "sources": {
            "total": len(status),
            "available": available,
            "details": status
        }
    }


@app.get("/sources")
async def list_sources():
    """List all available sources."""
    service = get_service()
    status = service.get_sources_status()

    return {
        "sources": [
            {
                "name": s["name"],
                "available": s["available"],
                "response_time": round(s["response_time"], 3)
            }
            for s in status
        ]
    }


@app.post("/weather")
async def get_weather(
    location: Location,
    source: Optional[str] = Query(None, description="Source name"),
    use_cache: bool = Query(True)
):
    """Get weather for a location."""
    service = get_service()

    try:
        result = service.get_weather(
            lat=location.latitude,
            lon=location.longitude,
            source=source,
            use_cache=use_cache,
            timezone=location.timezone
        )

        return {
            "location": location.model_dump(),
            "data": result,
            "fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/weather/current")
async def get_current_weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    source: Optional[str] = Query(None),
    timezone: str = Query("America/Bogota")
):
    """Get current weather (GET method)."""
    service = get_service()

    result = service.get_weather(lat, lon, source, timezone=timezone)

    return {
        "location": {"latitude": lat, "longitude": lon, "timezone": timezone},
        "data": result,
        "fetched_at": datetime.now().isoformat()
    }


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    service = get_service()
    return service.cache.stats()


@app.delete("/cache")
async def clear_cache():
    """Clear the cache."""
    service = get_service()
    service.clear_cache()
    return {"message": "Cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)