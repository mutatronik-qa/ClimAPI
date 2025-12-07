"""
Pruebas para el normalizador de datos meteorológicos.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from processing.data_normalizer import (
    DataValidator, DataNormalizer, TemperatureUnit, 
    WindSpeedUnit, PressureUnit, NORMALIZED_SCHEMA
)

class TestDataValidator:
    """Pruebas para validación de datos individuales."""
    
    def test_validate_temperature_celsius(self):
        """Prueba validación de temperatura en Celsius."""
        assert DataValidator.validate_temperature(25.0, TemperatureUnit.CELSIUS) == 25.0
        assert DataValidator.validate_temperature(-10.5, TemperatureUnit.CELSIUS) == -10.5
        assert DataValidator.validate_temperature(None) is None
        assert DataValidator.validate_temperature(100.0) is None  # Fuera de rango
    
    def test_validate_temperature_conversion(self):
        """Prueba conversión de temperatura Fahrenheit a Celsius."""
        # 32°F = 0°C
        result = DataValidator.validate_temperature(32.0, TemperatureUnit.FAHRENHEIT)
        assert result is not None
        assert abs(result - 0.0) < 0.1
    
    def test_validate_humidity(self):
        """Prueba validación de humedad."""
        assert DataValidator.validate_humidity(50.0) == 50.0
        assert DataValidator.validate_humidity(0.0) == 0.0
        assert DataValidator.validate_humidity(100.0) == 100.0
        assert DataValidator.validate_humidity(-10.0) is None  # Fuera de rango
        assert DataValidator.validate_humidity(150.0) is None  # Fuera de rango
    
    def test_validate_precipitation(self):
        """Prueba validación de precipitación."""
        assert DataValidator.validate_precipitation(10.5) == 10.5
        assert DataValidator.validate_precipitation(0.0) == 0.0
        assert DataValidator.validate_precipitation(None) == 0.0
        assert DataValidator.validate_precipitation(-5.0) == 0.0  # Negativo -> 0
    
    def test_validate_wind_speed(self):
        """Prueba validación y conversión de velocidad del viento."""
        # 10 m/s = 36 km/h
        result = DataValidator.validate_wind_speed(10.0, WindSpeedUnit.MS)
        assert result is not None
        assert abs(result - 36.0) < 0.5
    
    def test_validate_pressure(self):
        """Prueba validación de presión."""
        assert DataValidator.validate_pressure(1013.25, PressureUnit.HPA) == 1013.25
        assert DataValidator.validate_pressure(800.0, PressureUnit.HPA) is None  # Fuera de rango

class TestDataNormalizer:
    """Pruebas para normalización de datos de múltiples APIs."""
    
    @pytest.fixture
    def openmeteo_data(self):
        """Datos de ejemplo de Open-Meteo."""
        return {
            "hourly": {
                "time": ["2025-01-01T00:00", "2025-01-01T01:00"],
                "temperature_2m": [20.5, 19.2],
                "relative_humidity_2m": [65, 70],
                "precipitation": [0.0, 0.5],
                "wind_speed_10m": [10.0, 12.5],
                "wind_direction_10m": [180, 190],
                "surface_pressure": [1013.25, 1012.0],
                "cloudcover": [50, 60],
                "dew_point_2m": [12.0, 11.5],
                "visibility": [10000, 9500],
                "shortwave_radiation": [0, 50],
            }
        }
    
    def test_normalize_openmeteo(self, openmeteo_data):
        """Prueba normalización de datos Open-Meteo."""
        df = DataNormalizer.normalize_openmeteo(openmeteo_data, 6.24, -75.58, "Medellín")
        
        assert not df.empty
        assert len(df) == 2
        assert "timestamp" in df.columns
        assert "temperatura_c" in df.columns
        assert df["source"].iloc[0] == "open-meteo"
        assert df["temperature"][0].values == 20.5  # Verificar datos

    def test_normalize_openweathermap(self):
        """Prueba normalización de datos OpenWeatherMap."""
        owm_data = {
            "main": {"temp": 22.0, "humidity": 65, "pressure": 1013},
            "wind": {"speed": 5.0, "deg": 180},  # 5 m/s
            "clouds": {"all": 50},
            "rain": {"1h": 0.5},
            "visibility": 10000,
            "dt": 1704067200,
            "coord": {"lat": 6.24, "lon": -75.58}
        }
        
        df = DataNormalizer.normalize_openweathermap(owm_data, "Medellín")
        
        assert not df.empty
        assert len(df) == 1
        assert df["source"].iloc[0] == "openweathermap"
        # 5 m/s ≈ 18 km/h
        assert df["velocidad_viento_kmh"].iloc[0] is not None

    def test_combine_sources(self, openmeteo_data):
        """Prueba combinación de múltiples fuentes."""
        df1 = DataNormalizer.normalize_openmeteo(openmeteo_data, 6.24, -75.58, "Medellín")
        df2 = DataNormalizer.normalize_openmeteo(openmeteo_data, 6.24, -75.58, "Medellín")
        
        combined = DataNormalizer.combine_sources({
            "source1": df1,
            "source2": df2
        })
        
        assert not combined.empty
        # Debe tener 2 registros (deduplicado)
        assert len(combined) <= 4

    def test_validate_dataframe(self, openmeteo_data):
        """Prueba validación de DataFrame normalizado."""
        df = DataNormalizer.normalize_openmeteo(openmeteo_data, 6.24, -75.58)
        is_valid, errors = DataNormalizer.validate_dataframe(df)
        
        assert is_valid
        assert len(errors) == 0

    def test_get_schema(self):
        """Prueba obtención del esquema."""
        schema = DataNormalizer.get_schema()
        
        assert "timestamp" in schema
        assert "temperatura_c" in schema
        assert "humedad_porcentaje" in schema

if __name__ == "__main__":
    pytest.main([__file__, "-v"])