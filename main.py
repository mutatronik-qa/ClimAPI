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
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Agregar ruta correcta para importar config
sys.path.insert(0, str(Path(__file__).parent))

# Importar configuración
from app.config import settings

# Validar que la API Key esté disponible
if not settings.OPENWEATHER_API_KEY:
    raise ValueError("⚠️ OPENWEATHER_API_KEY no está definida en .env")

# Configuración de logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar módulos del proyecto
try:
    from data_sources.open_meteo import get_weather_data, validate_coordinates
    from processing.transform import process_weather_data
    from processing.storage import save_to_csv, CacheManager
except ModuleNotFoundError as e:
    logger.error(f"Error: No se encontró módulo: {e}")
    logger.error("Asegúrate de que todas las carpetas existan: data_sources/, processing/")
    raise

# Inicializar caché global
cache_manager = CacheManager(ttl_minutes=settings.CACHE_TTL_MINUTES)
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

# Configurar CORS con valores de settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class WeatherData(BaseModel):
    time: str
    temperature: float
    humidity: float
    precipitation: float
    wind_speed: float

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    timezone: str = settings.DEFAULT_TIMEZONE

class WeatherResponse(BaseModel):
    location: LocationRequest
    data: List[WeatherData]
    source: str
    timestamp: str

# Endpoints
@app.get("/", tags=["root"])
async def root():
    return {"message": "Clima Dashboard API", "version": "1.0.0"}

@app.get("/api/v1/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "clima-dashboard-api",
        "api_key_configured": bool(settings.OPENWEATHER_API_KEY)
    }

@app.post("/api/v1/weather/current", response_model=WeatherResponse, tags=["weather"])
async def get_current_weather(location: LocationRequest):
    """Obtiene datos meteorológicos actuales para una ubicación específica"""
    try:
        validate_coordinates(location.latitude, location.longitude)
        
        cached_df = cache_manager.get_processed_data(
            location.latitude, 
            location.longitude, 
            location.timezone
        )
        
        if cached_df is not None:
            logger.info("📦 Usando datos desde caché")
            df = cached_df
            source = "Open-Meteo (Cached)"
        else:
            logger.info("🌐 Obteniendo datos frescos desde API")
            api_response = get_weather_data(
                latitude=location.latitude,
                longitude=location.longitude,
                timezone=location.timezone
            )
            df = process_weather_data(api_response)
            cache_manager.set_processed_data(
                location.latitude, 
                location.longitude, 
                location.timezone, 
                df
            )
            source = "Open-Meteo"
        
        weather_data = []
        for index, row in df.head(24).iterrows():
            weather_data.append(WeatherData(
                time=index.isoformat(),
                temperature=float(row['temperatura_c']),
                humidity=float(row['humedad_porcentaje']),
                precipitation=float(row['precipitacion_mm']),
                wind_speed=float(row['velocidad_viento_kmh'])
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
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/v1/cache/stats", tags=["cache"])
async def get_cache_stats():
    return cache_manager.get_stats()

@app.delete("/api/v1/cache", tags=["cache"])
async def clear_cache():
    cache_manager.clear()
    return {"message": "Caché limpiada"}

@app.get("/api/v1/locations/default", tags=["locations"])
async def get_default_location():
    return {
        "latitude": settings.DEFAULT_LAT,
        "longitude": settings.DEFAULT_LON,
        "timezone": settings.DEFAULT_TIMEZONE,
        "city": settings.DEFAULT_CITY
    }

def load_config(config_path: str = "config/settings.json") -> dict:
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"No se encontró {config_path}, usando valores por defecto")
        return {
            "location": {
                "latitude": settings.DEFAULT_LAT,
                "longitude": settings.DEFAULT_LON,
                "timezone": settings.DEFAULT_TIMEZONE
            }
        }

def main():
    print("=" * 60)
    print("🌤️  Sistema de Consumo de Datos Meteorológicos")
    print("=" * 60)
    
    config = load_config()
    location = config.get("location", {})
    
    latitude = location.get("latitude", settings.DEFAULT_LAT)
    longitude = location.get("longitude", settings.DEFAULT_LON)
    timezone = location.get("timezone", settings.DEFAULT_TIMEZONE)
    
    print(f"📍 Ubicación: Lat {latitude}, Lon {longitude}")
    print(f"🕐 Zona horaria: {timezone}\n")
    
    try:
        validate_coordinates(latitude, longitude)
        api_response = get_weather_data(latitude, longitude, timezone)
        df = process_weather_data(api_response)
        save_to_csv(df, "data/weather_data.csv")
        
        print("✅ Proceso completado")
        print(f"🌡️  Temp promedio: {df['temperatura_c'].mean():.2f} °C")
        print(f"💧 Humedad promedio: {df['humedad_porcentaje'].mean():.2f} %")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn
        print("🚀 Iniciando servidor FastAPI...")
        print("📖 Docs: http://localhost:8000/docs")
        uvicorn.run(app, host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
    else:
        main()