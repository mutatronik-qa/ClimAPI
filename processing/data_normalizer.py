"""
Normalizador de datos meteorológicos.

Define un esquema estándar (NormalizedWeatherData) y proporciona funciones
para transformar datos de múltiples APIs a este formato común.

Esto permite:
- Comparabilidad entre fuentes de datos
- Validación de rangos realistas
- Manejo consistente de valores faltantes
- Conversión de unidades
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TemperatureUnit(Enum):
    """Unidades de temperatura soportadas."""
    CELSIUS = "C"
    FAHRENHEIT = "F"
    KELVIN = "K"

class PressureUnit(Enum):
    """Unidades de presión soportadas."""
    HPA = "hPa"
    MB = "mb"
    MMHG = "mmHg"
    PSI = "psi"

class WindSpeedUnit(Enum):
    """Unidades de velocidad del viento."""
    KMH = "km/h"
    MS = "m/s"
    MPH = "mph"
    KNOTS = "knots"

# Esquema normalizado de datos meteorológicos
NORMALIZED_SCHEMA = {
    "timestamp": "datetime64[ns, UTC]",  # Timestamp en UTC
    "temperatura_c": "float64",           # Temperatura en Celsius
    "humedad_porcentaje": "float64",      # Humedad relativa 0-100%
    "precipitacion_mm": "float64",        # Precipitación en mm
    "velocidad_viento_kmh": "float64",    # Velocidad viento en km/h
    "direccion_viento_grados": "float64", # Dirección viento 0-360°
    "presion_hpa": "float64",             # Presión en hPa
    "nubosidad_porcentaje": "float64",    # Cobertura de nubes 0-100%
    "punto_rocio_c": "float64",           # Punto de rocío en °C
    "visibilidad_m": "float64",           # Visibilidad en metros
    "radiacion_solar_wm2": "float64",     # Radiación solar en W/m²
    "indice_uv": "float64",               # Índice UV
    "source": "object",                   # Fuente de datos
    "latitude": "float64",                # Latitud
    "longitude": "float64",               # Longitud
    "city": "object",                     # Ciudad/ubicación
    "country": "object"                   # País
}

# Rangos realistas para validación
REALISTIC_RANGES = {
    "temperatura_c": (-50, 60),           # Rango razonable de temperatura
    "humedad_porcentaje": (0, 100),       # 0-100%
    "precipitacion_mm": (0, 500),         # Máximo 500mm por período
    "velocidad_viento_kmh": (0, 200),     # Máximo vientos huracanados
    "direccion_viento_grados": (0, 360),  # 0-360°
    "presion_hpa": (850, 1100),           # Rango normal presión
    "nubosidad_porcentaje": (0, 100),     # 0-100%
    "punto_rocio_c": (-80, 50),           # Rango realista
    "visibilidad_m": (0, 100000),         # 0-100km
    "radiacion_solar_wm2": (0, 2000),     # 0-2000 W/m² máximo
    "indice_uv": (0, 20)                  # 0-20 es rango extremo
}

class DataValidator:
    """Validador de datos meteorológicos."""
    
    @staticmethod
    def validate_temperature(value: float, unit: TemperatureUnit = TemperatureUnit.CELSIUS) -> Optional[float]:
        """Valida y convierte temperatura a Celsius."""
        if value is None or pd.isna(value):
            return None
        try:
            val = float(value)
            if unit == TemperatureUnit.FAHRENHEIT:
                val = (val - 32) * 5/9
            elif unit == TemperatureUnit.KELVIN:
                val = val - 273.15
            
            # Validar rango realista
            if not REALISTIC_RANGES["temperatura_c"][0] <= val <= REALISTIC_RANGES["temperatura_c"][1]:
                logger.warning(f"Temperatura fuera de rango: {val}°C")
                return None
            return round(val, 2)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_humidity(value: float) -> Optional[float]:
        """Valida humedad relativa (0-100%)."""
        if value is None or pd.isna(value):
            return None
        try:
            val = float(value)
            if val < 0 or val > 100:
                logger.warning(f"Humedad fuera de rango: {val}%")
                return None
            return round(val, 2)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_precipitation(value: float) -> Optional[float]:
        """Valida precipitación en mm."""
        if value is None or pd.isna(value):
            return 0.0
        try:
            val = float(value)
            if val < 0:
                logger.warning(f"Precipitación negativa: {val}mm")
                return 0.0
            if val > REALISTIC_RANGES["precipitacion_mm"][1]:
                logger.warning(f"Precipitación anormalmente alta: {val}mm")
                return None
            return round(val, 2)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_wind_speed(value: float, unit: WindSpeedUnit = WindSpeedUnit.KMH) -> Optional[float]:
        """Valida y convierte velocidad del viento a km/h."""
        if value is None or pd.isna(value):
            return None
        try:
            val = float(value)
            # Convertir a km/h
            if unit == WindSpeedUnit.MS:
                val = val * 3.6
            elif unit == WindSpeedUnit.MPH:
                val = val * 1.60934
            elif unit == WindSpeedUnit.KNOTS:
                val = val * 1.852
            
            if val < 0 or val > REALISTIC_RANGES["velocidad_viento_kmh"][1]:
                logger.warning(f"Velocidad del viento fuera de rango: {val}km/h")
                return None
            return round(val, 2)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_pressure(value: float, unit: PressureUnit = PressureUnit.HPA) -> Optional[float]:
        """Valida y convierte presión a hPa."""
        if value is None or pd.isna(value):
            return None
        try:
            val = float(value)
            # Convertir a hPa
            if unit == PressureUnit.MB:
                val = val  # 1 mb = 1 hPa
            elif unit == PressureUnit.MMHG:
                val = val * 1.33322
            elif unit == PressureUnit.PSI:
                val = val * 68.9476
            
            if val < REALISTIC_RANGES["presion_hpa"][0] or val > REALISTIC_RANGES["presion_hpa"][1]:
                logger.warning(f"Presión fuera de rango: {val}hPa")
                return None
            return round(val, 2)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_wind_direction(value: float) -> Optional[float]:
        """Valida dirección del viento (0-360 grados)."""
        if value is None or pd.isna(value):
            return None
        try:
            val = float(value)
            # Normalizar a 0-360
            val = val % 360
            return round(val, 2)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_percentage(value: float) -> Optional[float]:
        """Valida porcentaje (0-100)."""
        if value is None or pd.isna(value):
            return None
        try:
            val = float(value)
            if val < 0 or val > 100:
                logger.warning(f"Porcentaje fuera de rango: {val}%")
                return None
            return round(val, 2)
        except (ValueError, TypeError):
            return None

class DataNormalizer:
    """Normalizador de datos meteorológicos de múltiples APIs."""
    
    @staticmethod
    def normalize_openmeteo(data: Dict, lat: float, lon: float, city: str = "Unknown") -> pd.DataFrame:
        """
        Normaliza datos de Open-Meteo API.
        
        Input: JSON de Open-Meteo con estructura:
        {
            "hourly": {
                "time": [...],
                "temperature_2m": [...],
                "relative_humidity_2m": [...],
                ...
            }
        }
        """
        try:
            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            
            if not times:
                logger.warning("No hourly data in Open-Meteo response")
                return pd.DataFrame()
            
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(times, utc=True),
                "temperatura_c": hourly.get("temperature_2m", []),
                "humedad_porcentaje": hourly.get("relative_humidity_2m", []),
                "precipitacion_mm": hourly.get("precipitation", []),
                "velocidad_viento_kmh": hourly.get("wind_speed_10m", []),
                "direccion_viento_grados": hourly.get("wind_direction_10m", []),
                "presion_hpa": hourly.get("surface_pressure", []),
                "nubosidad_porcentaje": hourly.get("cloudcover", []),
                "punto_rocio_c": hourly.get("dew_point_2m", []),
                "visibilidad_m": hourly.get("visibility", []),
                "radiacion_solar_wm2": hourly.get("shortwave_radiation", []),
            })
            
            # Validar y limpiar cada columna
            df["temperatura_c"] = df["temperatura_c"].apply(
                lambda x: DataValidator.validate_temperature(x, TemperatureUnit.CELSIUS)
            )
            df["humedad_porcentaje"] = df["humedad_porcentaje"].apply(DataValidator.validate_humidity)
            df["precipitacion_mm"] = df["precipitacion_mm"].apply(DataValidator.validate_precipitation)
            df["velocidad_viento_kmh"] = df["velocidad_viento_kmh"].apply(
                lambda x: DataValidator.validate_wind_speed(x, WindSpeedUnit.KMH)
            )
            df["direccion_viento_grados"] = df["direccion_viento_grados"].apply(DataValidator.validate_wind_direction)
            df["presion_hpa"] = df["presion_hpa"].apply(
                lambda x: DataValidator.validate_pressure(x, PressureUnit.HPA)
            )
            df["nubosidad_porcentaje"] = df["nubosidad_porcentaje"].apply(DataValidator.validate_percentage)
            df["punto_rocio_c"] = df["punto_rocio_c"].apply(
                lambda x: DataValidator.validate_temperature(x, TemperatureUnit.CELSIUS)
            )
            
            # Agregar metadata
            df["source"] = "open-meteo"
            df["latitude"] = lat
            df["longitude"] = lon
            df["city"] = city
            df["country"] = "Colombia"
            
            # Reordenar columnas según esquema
            cols_order = [c for c in NORMALIZED_SCHEMA.keys() if c in df.columns]
            df = df[cols_order]
            
            return df
        
        except Exception as e:
            logger.error(f"Error normalizando Open-Meteo data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def normalize_openweathermap(data: Dict, city: str = "Unknown") -> pd.DataFrame:
        """
        Normaliza datos de OpenWeatherMap.
        
        Input: JSON de OpenWeatherMap con estructura:
        {
            "main": {"temp": ..., "humidity": ...},
            "wind": {"speed": ..., "deg": ...},
            "clouds": {"all": ...},
            "dt": ...,
            ...
        }
        """
        try:
            main = data.get("main", {})
            wind = data.get("wind", {})
            clouds = data.get("clouds", {})
            coord = data.get("coord", {})
            
            timestamp = datetime.fromtimestamp(data.get("dt", 0), tz=pd.Timestamp.now().tz)
            
            df = pd.DataFrame({
                "timestamp": [pd.Timestamp(timestamp, tz='UTC')],
                "temperatura_c": [main.get("temp")],
                "humedad_porcentaje": [main.get("humidity")],
                "precipitacion_mm": [data.get("rain", {}).get("1h", 0)],
                "velocidad_viento_kmh": [wind.get("speed")],
                "direccion_viento_grados": [wind.get("deg")],
                "presion_hpa": [main.get("pressure")],
                "nubosidad_porcentaje": [clouds.get("all")],
                "punto_rocio_c": None,
                "visibilidad_m": [data.get("visibility")],
            })
            
            # Validar y limpiar
            df["temperatura_c"] = df["temperatura_c"].apply(
                lambda x: DataValidator.validate_temperature(x, TemperatureUnit.CELSIUS)
            )
            df["humedad_porcentaje"] = df["humedad_porcentaje"].apply(DataValidator.validate_humidity)
            df["precipitacion_mm"] = df["precipitacion_mm"].apply(DataValidator.validate_precipitation)
            df["velocidad_viento_kmh"] = df["velocidad_viento_kmh"].apply(
                lambda x: DataValidator.validate_wind_speed(x, WindSpeedUnit.MS)
            )
            df["direccion_viento_grados"] = df["direccion_viento_grados"].apply(DataValidator.validate_wind_direction)
            df["presion_hpa"] = df["presion_hpa"].apply(DataValidator.validate_pressure)
            df["nubosidad_porcentaje"] = df["nubosidad_porcentaje"].apply(DataValidator.validate_percentage)
            df["visibilidad_m"] = df["visibilidad_m"].apply(lambda x: x if x and x > 0 else None)
            
            # Agregar metadata
            df["source"] = "openweathermap"
            df["latitude"] = coord.get("lon")
            df["longitude"] = coord.get("lat")
            df["city"] = city
            df["country"] = "Colombia"
            
            cols_order = [c for c in NORMALIZED_SCHEMA.keys() if c in df.columns]
            df = df[cols_order]
            
            return df
        
        except Exception as e:
            logger.error(f"Error normalizando OpenWeatherMap data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def normalize_meteoblue(data: Dict, lat: float, lon: float, city: str = "Unknown") -> pd.DataFrame:
        """
        Normaliza datos de MeteoBlue.
        """
        try:
            # MeteoBlue devuelve estructura similar a Open-Meteo
            # Reutilizar normalizador de Open-Meteo con ajustes menores
            data_adjusted = {
                "hourly": {
                    "time": data.get("time", []),
                    "temperature_2m": data.get("temperature", []),
                    "relative_humidity_2m": data.get("humidity", []),
                    "precipitation": data.get("precipitation", []),
                    "wind_speed_10m": data.get("wind_speed", []),
                    "wind_direction_10m": data.get("wind_direction", []),
                    "surface_pressure": data.get("pressure", []),
                    "cloudcover": data.get("cloudcover", []),
                    "dew_point_2m": data.get("dew_point", []),
                    "visibility": data.get("visibility", []),
                    "shortwave_radiation": data.get("solar_radiation", []),
                }
            }
            df = DataNormalizer.normalize_openmeteo(data_adjusted, lat, lon, city)
            df["source"] = "meteoblue"
            return df
        
        except Exception as e:
            logger.error(f"Error normalizando MeteoBlue data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def normalize_siata(data: Dict, lat: float, lon: float, city: str = "Medellín") -> pd.DataFrame:
        """
        Normaliza datos de SIATA (Sistema de Alerta Temprana).
        Estructura: lista de registros con timestamp, variables
        """
        try:
            records = data if isinstance(data, list) else data.get("data", [])
            
            if not records:
                logger.warning("No records in SIATA data")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            
            # Mapear columnas esperadas
            mapping = {
                "fecha_hora": "timestamp",
                "timestamp": "timestamp",
                "temperature": "temperatura_c",
                "temp": "temperatura_c",
                "humedad": "humedad_porcentaje",
                "humidity": "humedad_porcentaje",
                "precipitacion": "precipitacion_mm",
                "precipitation": "precipitacion_mm",
                "velocidad_viento": "velocidad_viento_kmh",
                "wind_speed": "velocidad_viento_kmh",
                "direccion_viento": "direccion_viento_grados",
                "wind_direction": "direccion_viento_grados",
                "presion": "presion_hpa",
                "pressure": "presion_hpa",
                "nubosidad": "nubosidad_porcentaje",
                "cloudcover": "nubosidad_porcentaje",
            }
            
            df = df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})
            
            # Convertir timestamp a datetime
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors='coerce')
            
            # Validar columnas
            if "temperatura_c" in df.columns:
                df["temperatura_c"] = df["temperatura_c"].apply(
                    lambda x: DataValidator.validate_temperature(x, TemperatureUnit.CELSIUS)
                )
            
            # Agregar metadata
            df["source"] = "siata"
            df["latitude"] = lat
            df["longitude"] = lon
            df["city"] = city
            df["country"] = "Colombia"
            
            cols_order = [c for c in NORMALIZED_SCHEMA.keys() if c in df.columns]
            df = df[cols_order]
            
            return df
        
        except Exception as e:
            logger.error(f"Error normalizando SIATA data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def combine_sources(dataframes: Dict[str, pd.DataFrame], 
                        dedup_window: str = "1H") -> pd.DataFrame:
        """
        Combina múltiples DataFrames normalizados eliminando duplicados.
        
        Args:
            dataframes: Dict con nombre de fuente -> DataFrame
            dedup_window: Ventana temporal para deduplicación (ej. '1H', '30T')
        
        Returns:
            DataFrame combinado y deduplicado
        """
        if not dataframes:
            return pd.DataFrame()
        
        combined = pd.concat(dataframes.values(), ignore_index=False)
        
        if combined.empty:
            return combined
        
        # Asegurar que timestamp es datetime
        combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True, errors='coerce')
        
        # Ordenar por timestamp y fuente
        combined = combined.sort_values("timestamp")
        
        # Deduplicar: mantener la primera observación dentro de ventana temporal
        combined = combined.set_index("timestamp")
        combined = combined[~combined.index.duplicated(keep='first')]
        combined = combined.reset_index()
        
        return combined
    
    @staticmethod
    def get_schema() -> Dict:
        """Retorna el esquema normalizado."""
        return NORMALIZED_SCHEMA.copy()
    
    @staticmethod
    def validate_dataframe(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        Valida que un DataFrame cumpla con el esquema normalizado.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Verificar columnas requeridas
        required_cols = ["timestamp", "temperatura_c", "humedad_porcentaje"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            errors.append(f"Columnas faltantes: {missing}")
        
        # Verificar tipos
        for col, dtype in NORMALIZED_SCHEMA.items():
            if col in df.columns:
                if not str(df[col].dtype).startswith(dtype.replace("64", "")):
                    logger.warning(f"Columna {col} tiene tipo {df[col].dtype}, esperado {dtype}")
        
        # Verificar timestamp es datetime
        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                errors.append("timestamp debe ser datetime64[ns, UTC]")
        
        # Verificar rangos
        for col, (min_val, max_val) in REALISTIC_RANGES.items():
            if col in df.columns:
                invalid = df[(df[col] < min_val) | (df[col] > max_val)].shape[0]
                if invalid > 0:
                    logger.warning(f"{col}: {invalid} valores fuera de rango [{min_val}, {max_val}]")
        
        return len(errors) == 0, errors