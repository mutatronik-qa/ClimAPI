import sys
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, HTTPException

# Agregar el directorio raíz al path para importar módulos existentes
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from processing.storage import CacheManager

from ...models import HealthResponse, CacheStats
from ...config import settings

router = APIRouter(prefix="/api/v1", tags=["health", "cache"])

# Inicializar caché
cache_manager = CacheManager(ttl_minutes=settings.CACHE_TTL_MINUTES)

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Verifica el estado del servicio
    """
    return HealthResponse(
        status="healthy",
        service="clima-dashboard-api",
        timestamp=datetime.now().isoformat()
    )

@router.get("/cache/stats", response_model=CacheStats)
async def get_cache_stats():
    """
    Obtiene estadísticas del sistema de caché
    """
    stats = cache_manager.get_stats()
    return CacheStats(
        entries=stats["entries"],
        size=stats["size"],
        path=stats["path"],
        ttl_minutes=stats["ttl_minutes"]
    )

@router.delete("/cache")
async def clear_cache():
    """
    Limpia toda la caché
    """
    try:
        result = cache_manager.clear()
        return {
            "message": "Caché limpiada exitosamente",
            "timestamp": result["timestamp"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar caché: {str(e)}")

@router.get("/status")
async def get_service_status():
    """
    Obtiene el estado completo del servicio incluyendo caché
    """
    try:
        cache_stats = cache_manager.get_stats()
        
        return {
            "service": "clima-dashboard-api",
            "status": "healthy",
            "version": "1.0.0",
            "cache": {
                "entries": cache_stats["entries"],
                "size_mb": round(cache_stats["size"] / (1024 * 1024), 2),
                "ttl_minutes": cache_stats["ttl_minutes"]
            },
            "config": {
                "default_location": {
                    "city": settings.DEFAULT_CITY,
                    "latitude": settings.DEFAULT_LAT,
                    "longitude": settings.DEFAULT_LON
                },
                "cache_ttl_minutes": settings.CACHE_TTL_MINUTES,
                "debug_mode": settings.DEBUG
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estado: {str(e)}")