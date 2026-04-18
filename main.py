"""
Backend FastAPI para Clima Dashboard

Este script:
1. Configura la API FastAPI con CORS
2. Define los endpoints para datos meteorológicos
3. Integra múltiples fuentes de datos
4. Proporciona documentación automática

ClimAPI - API de Datos Meteorológicos

Este módulo es el punto de entrada principal de la aplicación FastAPI que proporciona:
- Una API REST para consultar datos meteorológicos
- Integración con múltiples fuentes de datos
- Sistema de caché para mejorar el rendimiento
- Documentación automática con Swagger UI y ReDoc

Módulos principales:
- data_sources/: Fuentes de datos meteorológicos
- processing/: Procesamiento y transformación de datos
- backend/: Implementación de la API FastAPI
"""

import os
import pandas as pd
import asyncio
import json
import logging
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

from data_sources.meteoblue import MeteoBlueService, fetch_weather_sync
from data_sources.openweathermap import OpenWeatherMap
from processing.data_processor import DataProcessor
from data_sources.open_meteo import get_weather_data, validate_coordinates
from processing.transform import process_weather_data
from processing.storage import save_to_csv, CacheManager
from processing.data_diagnostics import DataDiagnostics
from processing.data_normalizer import DataNormalizer, DataValidator
from processing.data_quality_report import DataQualityReport
from processing.api_data_extractors import APIDataExtractor

from config.settings import settings
from data_sources.siata import SIATAClient
from data_sources.radar_ideam import RadarIDEAMClient

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar caché global
CACHE_TTL = int(os.getenv('CACHE_TTL_MINUTES', '15'))
CACHE_DIR = os.getenv('CACHE_DIR', 'cache')

cache_manager = CacheManager(ttl_minutes=CACHE_TTL)

# Crear directorios necesarios
Path(CACHE_DIR).mkdir(exist_ok=True)
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
    allow_origins=["http://localhost:3000"],  # Next.js frontend
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

# Instanciar clientes
METEOBLUE_CFG = {
    "api_key": os.getenv("METEOBLUE_API_KEY"),
    "base_url": os.getenv("METEOBLUE_BASE_URL", "https://my.meteoblue.com"),
    "shared_secret": os.getenv("METEOBLUE_SHARED_SECRET"),
    "endpoint": os.getenv("METEOBLUE_ENDPOINT", "/packages/basic-1h"),
    "ttl_seconds": int(os.getenv("METEOBLUE_TTL_SECONDS", "3600"))
}
meteoblue_client = MeteoBlueService(METEOBLUE_CFG)

OWM_CFG = {
    "api_key": settings.OPENWEATHER_API_KEY,
    "base_url": settings.OPENWEATHER_BASE_URL,
    "units": settings.OPENWEATHER_UNITS,
    "ttl_seconds": settings.CACHE_CONFIG.current_weather * 60
}
owm_client = OpenWeatherMap(OWM_CFG)

siata_client = SIATAClient({
    "api_url": settings.SIATA_API_URL,
    "operational_url": settings.SIATA_OPERACIONAL_URL,
    "timeout": settings.SIATA_TIMEOUT,
    "retry_attempts": settings.SIATA_RETRY_ATTEMPTS,
})
radar_client = RadarIDEAMClient({
    "bucket": settings.IDEAM_RADAR_BUCKET,
    "region": settings.IDEAM_RADAR_REGION
})

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _save_api_csv(filepath: Path, records: List[Dict[str, Any]], timestamp_key: str = "timestamp"):
    """
    Guarda una lista de records (dicts) como CSV con índice datetime UTC.
    """
    if not records:
        return
    df = pd.DataFrame(records)
    if timestamp_key in df.columns:
        df[timestamp_key] = pd.to_datetime(df[timestamp_key], utc=True, errors='coerce')
        df = df.dropna(subset=[timestamp_key])
        df = df.set_index(timestamp_key)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(filepath)

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
        "latitude": 6.244,
        "longitude": -75.581,
        "timezone": "America/Bogota",
        "city": "Medellín",
        "country": "Colombia"
    }
@app.get("/api/v1/weather/siata")
async def get_siata_weather(lat: float, lon: float):
    data = siata_client.get_weather_current()
    return {"data": data, "source": "siata"}

@app.get("/api/v1/radar/latest")
async def get_latest_radar():
    data = radar_client.get_latest_scan()
    return {"data": data, "source": "ideam_radar"}

def load_config(config_path: str = "config/settings.json") -> dict:
    """
    Carga la configuración desde un archivo JSON.
    
    Args:
        config_path: Ruta al archivo de configuración
    
    Returns:
        dict: Diccionario con la configuración
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"⚠️  Advertencia: No se encontró el archivo de configuración {config_path}")
        print("   Usando valores por defecto.")
        return {
            "location": {
                "latitude": 6.244,
                "longitude": -75.581,
                "timezone": "America/Bogota"
            },
            "data": {
                "output_directory": "data",
                "default_filename": "weather_data.csv"
            }
        }
    except json.JSONDecodeError as e:
        print(f"❌ Error al leer el archivo de configuración: {e}")
        sys.exit(1)


# Añadir import seguro del analizador de notebooks
try:
    from scripts.ipynb_analyzer import analyze_notebooks  # type: ignore
except Exception as e:
    logger.warning(f"No se pudo importar analizador de notebooks: {e}")
    analyze_notebooks = None

def main():
    """
    Función principal que orquesta todo el flujo del proyecto.
    """
    print("=" * 60)
    print("🌤️  Sistema de Consumo de Datos Meteorológicos")
    print("=" * 60)
    print()
    
    # 0. Analizar notebooks
    if analyze_notebooks is not None:
        print("🔎 Paso 0: Analizando notebooks (ejecución segura)...")
        try:
            nb_results = analyze_notebooks(folder=".", execute_safe=True)
            total_exported = sum(len(r['exported']) for r in nb_results)
            if total_exported > 0:
                print(f"   ✓ Se exportaron {total_exported} datasets desde notebooks")
        except Exception as e:
            logger.warning(f"Error al analizar notebooks: {e}")
        print()
    
    # 1. Cargar configuración
    print("📋 Paso 1: Cargando configuración...")
    config = load_config()
    location = config.get("location", {})
    
    latitude = location.get("latitude", 6.244)
    longitude = location.get("longitude", -75.581)
    timezone = location.get("timezone", "America/Bogota")
    city = location.get("city", "Medellín")
    
    print(f"   ✓ Ubicación: {city} (Lat {latitude}, Lon {longitude})")
    print()
    
    # 2. Validar coordenadas
    print("🔍 Paso 2: Validando coordenadas...")
    try:
        validate_coordinates(latitude, longitude)
        print("   ✓ Coordenadas válidas")
    except ValueError as e:
        print(f"   ❌ Error: {e}")
        sys.exit(1)
    print()
    
    # 3. NUEVO: Extraer datos de cada API por separado
    print("🌐 Paso 3: Extrayendo datos de cada API (por separado)...")
    extractor = APIDataExtractor(Path("data/raw_api_data"))
    
    extraction_results = extractor.extract_all(
        lat=latitude,
        lon=longitude,
        city=city,
        owm_api_key=settings.OPENWEATHER_API_KEY
    )
    
    # Mostrar resumen de extracción
    print("\n📋 Resumen de extracción por API:")
    for api_name, result in extraction_results.items():
        meta = result["metadata"]
        if meta.get("status") == "success":
            records = meta.get("records", 0)
            print(f"   ✓ {api_name}: {records} registros")
        elif meta.get("status") == "empty":
            print(f"   ⚠️  {api_name}: DataFrame vacío")
        elif meta.get("status") == "not_found":
            print(f"   ℹ️  {api_name}: No disponible")
        else:
            print(f"   ❌ {api_name}: {meta.get('error', 'Error desconocido')}")
    print()
    
    # 4. Combinar y normalizar datos
    print("🔄 Paso 4: Combinando datos de múltiples APIs...")
    
    sources_data = {}
    for api_name, result in extraction_results.items():
        df = result["dataframe"]
        if not df.empty:
            sources_data[api_name] = df
    
    if not sources_data:
        print("   ❌ No se obtuvieron datos de ninguna fuente")
        sys.exit(1)
    
    try:
        df_combined = DataNormalizer.combine_sources(sources_data)
        print(f"   ✓ Datos combinados: {len(df_combined)} registros únicos")
    except Exception as e:
        print(f"   ❌ Error al combinar fuentes: {e}")
        logger.error(f"Error combinando fuentes: {e}", exc_info=True)
        df_combined = list(sources_data.values())[0]
    
    print()
    
    # 5. Validar y reparar calidad de datos
    print("📊 Paso 5: Validando y reparando calidad de datos...")
    
    df_repaired, repair_actions = DataDiagnostics.validate_and_repair(df_combined)
    if repair_actions:
        print("   🔧 Acciones de reparación:")
        for action in repair_actions:
            print(f"      • {action}")
    
    df_combined = df_repaired
    
    # Validar esquema
    is_valid, errors = DataNormalizer.validate_dataframe(df_combined)
    if is_valid:
        print("   ✓ Validación de esquema exitosa")
    else:
        print(f"   ⚠️  Errores de esquema:")
        for error in errors:
            print(f"      • {error}")
    
    # Generar reporte de calidad
    try:
        quality_report = DataQualityReport.generate(df_combined, "combined")
        summary = quality_report.get("summary", {})
        missing_pct = summary.get("missing_data_percent", 0)
        overall_quality = summary.get("overall_quality", "Unknown")
        
        print(f"   ✓ Calidad: {overall_quality} (Completitud: {missing_pct:.2f}%)")
        
        # Guardar reporte
        report_file = Path("data/data_quality_report.json")
        report_file.parent.mkdir(parents=True, exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(quality_report, f, indent=2, default=str)
        print(f"   ✓ Reporte guardado en: {report_file}")
    except Exception as e:
        print(f"   ❌ Error generando reporte: {e}")
        logger.error(f"Error en reporte de calidad: {e}", exc_info=True)
    
    print()
    
    # 6. Guardar datos normalizados
    print("💾 Paso 6: Guardando datos normalizados...")
    try:
        output_path = Path("data/weather_data_normalized.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_combined.to_csv(output_path, index=False)
        print(f"   ✓ Datos guardados en: {output_path}")
        print(f"   ✓ Registros: {len(df_combined)}")
        print(f"   ✓ Columnas: {len(df_combined.columns)}")
    except Exception as e:
        print(f"   ❌ Error al guardar: {e}")
        logger.error(f"Error guardando datos: {e}", exc_info=True)
    
    print()
    
    # 7. Resumen final
    print("=" * 60)
    print("✅ Proceso completado exitosamente!")
    print("=" * 60)
    print()
    print("📊 Archivos generados:")
    print("   Datos por API (raw):")
    for api in ["open-meteo", "openweathermap", "siata"]:
        api_dir = Path(f"data/raw_api_data/{api}")
        if api_dir.exists():
            csv_files = list(api_dir.glob("*.csv"))
            if csv_files:
                print(f"      • {api}: {len(csv_files)} archivos CSV")
    
    print("\n   Datos consolidados:")
    print("      • data/weather_data_normalized.csv")
    print("      • data/raw_api_data/reports/ (reportes por API)")
    print()
    print("🚀 Para ejecutar las pruebas:")
    print("   pytest tests/test_api_data_sources.py -v")
    print()
    print("🚀 Para ver el dashboard:")
    print("   streamlit run dashboard/app.py")
    print()


# Nuevo endpoint para MeteoBlue (actual / forecast)
@app.get("/api/v1/weather/meteoblue", tags=["weather"])
async def get_meteoblue_weather(
    lat: float,
    lon: float,
    mode: str = "current",
    days: int = 7
):
    """
    Endpoint que expone MeteoBlue:
    - mode=current -> resumen actual
    - mode=forecast -> resumen diario para `days`
    """
    try:
        location = {"lat": lat, "lon": lon, "id": f"{lat},{lon}"}
        if mode == "forecast":
            resp = await meteoblue_client.get_forecast(location, days=days)
            return {"source": "meteoblue", "mode": "forecast", "data": resp}
        resp = await meteoblue_client.get_current(location)
        return {"source": "meteoblue", "mode": "current", "data": resp}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"MeteoBlue error: {e}")
        raise HTTPException(status_code=500, detail="Error al obtener datos de MeteoBlue")


@app.get("/api/v1/weather/openweathermap", tags=["weather"])
async def fetch_openweathermap(city: str = Query(..., description="Ciudad (p.ej. Medellín)")):
    """
    Obtiene datos actuales de OpenWeatherMap, guarda CSV por API y retorna JSON normalizado.
    """
    loop = asyncio.get_running_loop()
    try:
        # OpenWeatherMap client es sync; ejecutarlo en executor
        raw = await loop.run_in_executor(None, owm_client.get_weather_data, city)
        # guardar CSV con un solo registro
        rec = {
            "timestamp": raw.get("timestamp"),
            "temperature": raw.get("temperature"),
            "humidity": raw.get("humidity"),
            "wind_speed": raw.get("wind_speed"),
            "location": raw.get("location")
        }
        _save_api_csv(DATA_DIR / "openweathermap.csv", [rec])
        return {"source": "openweathermap", "data": raw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/weather/meteoblue/save", tags=["weather"])
async def fetch_and_save_meteoblue(lat: float = Query(...), lon: float = Query(...), mode: str = "current", days: int = 7):
    """
    Obtiene datos MeteoBlue (current o forecast), guarda CSV específico de la API.
    """
    location = {"lat": lat, "lon": lon, "id": f"{lat},{lon}"}
    try:
        if mode == "forecast":
            resp = await meteoblue_client.get_forecast(location, days=days)
            # normalizar days -> registros (date -> timestamp noon)
            records = []
            for d in resp.get("days", []):
                date = d.get("date")
                ts = f"{date}T12:00:00"
                records.append({"timestamp": ts, "temp_max": d.get("temp_max"), "temp_min": d.get("temp_min"), "precipitation": d.get("precipitation")})
            _save_api_csv(DATA_DIR / "meteoblue.csv", records)
            return {"source": "meteoblue", "mode": "forecast", "data": resp}
        resp = await meteoblue_client.get_current(location)
        rec = {"timestamp": resp.get("timestamp"), "temperature": resp.get("temperature"), "humidity": resp.get("humidity"), "location": resp.get("location")}
        _save_api_csv(DATA_DIR / "meteoblue.csv", [rec])
        return {"source": "meteoblue", "mode": "current", "data": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/weather/radar", tags=["weather"])
async def fetch_radar_ideam(lat: float = Query(...), lon: float = Query(...)):
    """
    Endpoint placeholder para RADAR IDEAM. Si existe módulo data_sources.radar_ideam con fetch_weather
    lo usará y guardará CSV; si no, devuelve 501.
    """
    try:
        try:
            from data_sources.radar_ideam import fetch_weather as radar_fetch  # type: ignore
        except Exception:
            raise HTTPException(status_code=501, detail="RADAR IDEAM no implementado en el proyecto.")
        data = radar_fetch(lat, lon)
        # intentar extraer registros y guardar
        records = []
        if isinstance(data, dict) and "data" in data:
            payload = data["data"]
            # si payload es lista de hourly records
            if isinstance(payload, list):
                for rec in payload:
                    ts = rec.get("timestamp") or rec.get("time") or rec.get("date")
                    records.append({"timestamp": ts, **{k: v for k, v in rec.items() if k != "timestamp"}})
        _save_api_csv(DATA_DIR / "radar_ideam.csv", records)
        return {"source": "radar_ideam", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        import uvicorn
        print("🚀 Iniciando servidor FastAPI...")
        print("📖 Documentación disponible en: http://localhost:8000/docs")
        uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        import subprocess
        print("🌐 Abriendo dashboard Streamlit...")
        subprocess.run(["streamlit", "run", "dashboard/app.py"])
    else:
        main()

def sanitize_filename(filename: str) -> str:
    """
    Reemplaza caracteres no válidos para nombres de archivos en Windows.
    """
    return filename.replace(":", "_").replace("\\", "_").replace("/", "_")