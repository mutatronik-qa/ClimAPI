"""
Backend FastAPI para Clima Dashboard

Este script:
1. Configura la API FastAPI con CORS
2. Define los endpoints para datos meteorológicos
3. Integra múltiples fuentes de datos
4. Proporciona documentación automática
"""

import pandas as pd
import numpy as np
import requests
import json
import os
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

# Importar configuración local
from .config import settings

# Agregar el directorio raíz al path para importar módulos existentes
sys.path.append(str(Path(__file__).parent.parent.parent))

from data_sources.open_meteo import get_weather_data, validate_coordinates
from processing.transform import process_weather_data
from processing.storage import save_to_csv, CacheManager

# Configuración de logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar caché global
cache_manager = CacheManager(ttl_minutes=settings.CACHE_TTL_MINUTES)

# Crear directorios necesarios
Path(settings.CACHE_DIR).mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)

# Crear aplicación FastAPI
app = FastAPI(
    title="Clima Dashboard API",
    description="API para dashboard meteorológico con múltiples fuentes de datos",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para respuestas
class WeatherData(BaseModel):
    time: str
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    timezone: str = "America/Bogota"

class WeatherResponse(BaseModel):
    location: LocationRequest
    data: List[WeatherData]
    source: str
    timestamp: str

# Endpoints de la API
@app.get("/", tags=["root"])
async def root():
    return {"message": "Clima Dashboard API", "version": "1.0.0"}

@app.get("/api/v1/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "service": "clima-dashboard-api"}

@app.post("/api/v1/weather/current", response_model=WeatherResponse, tags=["weather"])
async def get_current_weather(location: LocationRequest):
    """
    Obtiene datos meteorológicos actuales para una ubicación específica
    """
    try:
        # Validar coordenadas
        validate_coordinates(location.latitude, location.longitude)
        
        # Intentar obtener datos procesados de caché
        cached_df = cache_manager.get_processed_data(
            location.latitude, 
            location.longitude, 
            location.timezone
        )
        
        if cached_df is not None:
            logger.info("Usando datos desde caché")
            df = cached_df
            source = "Open-Meteo (Cached)"
        else:
            logger.info("Obteniendo datos frescos desde API")
            # Obtener datos de la API
            api_response = get_weather_data(
                latitude=location.latitude,
                longitude=location.longitude,
                timezone=location.timezone
            )
            
            # Procesar datos
            df = process_weather_data(api_response)
            
            # Guardar en caché
            cache_manager.set_processed_data(
                location.latitude, 
                location.longitude, 
                location.timezone, 
                df
            )
            source = "Open-Meteo"
        
        # Convertir a formato de respuesta
        weather_data = []
        for index, row in df.head(24).iterrows():  # Últimas 24 horas
            weather_data.append(WeatherData(
                time=index.isoformat(),
                temperature=row['temperatura_c'],
                humidity=row['humedad_porcentaje'],
                precipitation=row['precipitacion_mm'],
                wind_speed=row['velocidad_viento_kmh']
            ))
        
        return WeatherResponse(
            location=location,
            data=weather_data,
            source=source,
            timestamp=datetime.now().isoformat()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener datos: {str(e)}")

@app.get("/api/v1/cache/stats", tags=["cache"])
async def get_cache_stats():
    """
    Obtiene estadísticas del sistema de caché
    """
    return cache_manager.get_stats()

@app.delete("/api/v1/cache", tags=["cache"])
async def clear_cache():
    """
    Limpia toda la caché
    """
    cache_manager.clear()
    return {"message": "Caché limpiada exitosamente"}

@app.get("/api/v1/locations/default", tags=["locations"])
async def get_default_location():
    """
    Retorna la ubicación por defecto (Medellín)
    """
    return {
        "latitude": settings.DEFAULT_LAT,
        "longitude": settings.DEFAULT_LON,
        "timezone": settings.DEFAULT_TIMEZONE,
        "city": settings.DEFAULT_CITY,
        "country": "Colombia"
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("🚀 Clima Dashboard Backend - FastAPI")
    print("=" * 60)
    print(f"🌐 Servidor iniciado en: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 Documentación Swagger: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"📖 Documentación ReDoc: http://{settings.HOST}:{settings.PORT}/redoc")
    print(f"🔍 Health Check: http://{settings.HOST}:{settings.PORT}/api/v1/health")
    print(f"💾 Caché TTL: {settings.CACHE_TTL_MINUTES} minutos")
    print(f"📊 Modo {'desarrollo' if settings.DEBUG else 'producción'}")
    print("=" * 60)
    
    # Iniciar servidor
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )