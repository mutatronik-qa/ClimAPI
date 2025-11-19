from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class WeatherData(BaseModel):
    """Modelo para datos meteorológicos individuales"""
    time: str = Field(..., description="Timestamp en formato ISO")
    temperature: float = Field(..., description="Temperatura en Celsius")
    humidity: float = Field(..., description="Humedad en porcentaje")
    precipitation: float = Field(..., description="Precipitación en mm")
    wind_speed: float = Field(..., description="Velocidad del viento en km/h")
    
    class Config:
        json_schema_extra = {
            "example": {
                "time": "2023-12-01T12:00:00",
                "temperature": 22.5,
                "humidity": 65.0,
                "precipitation": 0.0,
                "wind_speed": 12.3
            }
        }

class LocationRequest(BaseModel):
    """Modelo para solicitudes de ubicación"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitud")
    longitude: float = Field(..., ge=-180, le=180, description="Longitud")
    timezone: str = Field(default="America/Bogota", description="Zona horaria")
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 6.244,
                "longitude": -75.581,
                "timezone": "America/Bogota"
            }
        }

class WeatherResponse(BaseModel):
    """Modelo para respuesta de datos meteorológicos"""
    location: LocationRequest
    data: List[WeatherData]
    source: str = Field(..., description="Fuente de los datos")
    timestamp: str = Field(..., description="Timestamp de la respuesta")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location": {
                    "latitude": 6.244,
                    "longitude": -75.581,
                    "timezone": "America/Bogota"
                },
                "data": [
                    {
                        "time": "2023-12-01T12:00:00",
                        "temperature": 22.5,
                        "humidity": 65.0,
                        "precipitation": 0.0,
                        "wind_speed": 12.3
                    }
                ],
                "source": "Open-Meteo",
                "timestamp": "2023-12-01T12:00:00"
            }
        }

class LocationInfo(BaseModel):
    """Modelo para información de ubicación"""
    latitude: float
    longitude: float
    timezone: str
    city: str
    country: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 6.244,
                "longitude": -75.581,
                "timezone": "America/Bogota",
                "city": "Medellín",
                "country": "Colombia"
            }
        }

class HealthResponse(BaseModel):
    """Modelo para respuesta de health check"""
    status: str
    service: str
    timestamp: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "service": "clima-dashboard-api",
                "timestamp": "2023-12-01T12:00:00"
            }
        }

class CacheStats(BaseModel):
    """Modelo para estadísticas de caché"""
    entries: int
    size: int
    path: str
    ttl_minutes: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "entries": 150,
                "size": 2048576,
                "path": "cache",
                "ttl_minutes": 15
            }
        }