import sys
from pathlib import Path
from typing import List
from fastapi import APIRouter, HTTPException
from datetime import datetime

# Agregar el directorio raíz al path para importar módulos existentes
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

from data_sources.open_meteo import get_weather_data, validate_coordinates
from processing.transform import process_weather_data
from processing.storage import CacheManager

from ...models import WeatherData, WeatherResponse, LocationRequest
from ...config import settings

router = APIRouter(prefix="/api/v1/weather", tags=["weather"])

# Inicializar caché
cache_manager = CacheManager(ttl_minutes=settings.CACHE_TTL_MINUTES)

@router.post("/current", response_model=WeatherResponse)
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
            print(" Usando datos desde caché")
            df = cached_df
            source = "Open-Meteo (Cached)"
        else:
            print(" Obteniendo datos frescos desde API")
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
        weather_data: List[WeatherData] = []
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

@router.get("/forecast")
async def get_weather_forecast(
    latitude: float,
    longitude: float,
    timezone: str = "America/Bogota",
    days: int = 7
):
    """
    Obtiene pronóstico meteorológico para los próximos días
    """
    try:
        # Validar coordenadas
        validate_coordinates(latitude, longitude)
        
        # Obtener datos de pronóstico
        api_response = get_weather_data(
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            forecast_days=days
        )
        
        # Procesar datos
        df = process_weather_data(api_response)
        
        # Convertir a formato de respuesta
        forecast_data = []
        for index, row in df.iterrows():
            forecast_data.append({
                "time": index.isoformat(),
                "temperature": row['temperatura_c'],
                "humidity": row['humedad_porcentaje'],
                "precipitation": row['precipitacion_mm'],
                "wind_speed": row['velocidad_viento_kmh']
            })
        
        return {
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone
            },
            "forecast": forecast_data,
            "source": "Open-Meteo",
            "timestamp": datetime.now().isoformat()
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener pronóstico: {str(e)}")