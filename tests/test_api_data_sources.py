"""
Pruebas unitarias para validar el procesamiento de datos de cada API.
Verifica que cada API devuelve datos correctamente formateados y normalizados.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from data_sources.open_meteo import get_weather_data, validate_coordinates
from data_sources.openweathermap import OpenWeatherMap
from processing.data_normalizer import DataNormalizer, DataValidator
from processing.data_diagnostics import DataDiagnostics


class TestOpenMeteoAPI:
    """Pruebas para la API Open-Meteo."""
    
    @pytest.fixture
    def mock_openmeteo_response(self):
        """Respuesta simulada de Open-Meteo."""
        return {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota",
            "hourly": {
                "time": [
                    "2025-01-01T00:00",
                    "2025-01-01T01:00",
                    "2025-01-01T02:00",
                ],
                "temperature_2m": [20.5, 19.2, 18.1],
                "relative_humidity_2m": [65, 70, 75],
                "precipitation": [0.0, 0.5, 1.2],
                "wind_speed_10m": [10.0, 12.5, 15.0],
                "wind_direction_10m": [180, 190, 200],
                "surface_pressure": [1013.25, 1012.0, 1011.5],
                "cloudcover": [50, 60, 70],
                "dew_point_2m": [12.0, 11.5, 10.8],
                "visibility": [10000, 9500, 9000],
                "shortwave_radiation": [0, 50, 100],
            }
        }
    
    def test_validate_coordinates_valid(self):
        """Prueba validación de coordenadas válidas."""
        # No debe lanzar excepción
        validate_coordinates(6.244, -75.581)
        validate_coordinates(0, 0)
        validate_coordinates(-90, 180)
        validate_coordinates(90, -180)
    
    def test_validate_coordinates_invalid(self):
        """Prueba validación de coordenadas inválidas."""
        with pytest.raises(ValueError):
            validate_coordinates(91, 0)  # Latitud > 90
        
        with pytest.raises(ValueError):
            validate_coordinates(0, 181)  # Longitud > 180
        
        with pytest.raises(ValueError):
            validate_coordinates(-91, 0)  # Latitud < -90
    
    @patch('requests.get')
    def test_get_weather_data_valid_response(self, mock_get, mock_openmeteo_response):
        """Prueba obtención de datos de Open-Meteo con respuesta válida."""
        mock_response = Mock()
        mock_response.json.return_value = mock_openmeteo_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        response = get_weather_data(6.244, -75.581, "America/Bogota")
        
        assert response is not None
        assert "hourly" in response
        assert "time" in response["hourly"]
        assert len(response["hourly"]["time"]) == 3
        assert len(response["hourly"]["temperature_2m"]) == 3
    
    def test_normalize_openmeteo_data(self, mock_openmeteo_response):
        """Prueba normalización de datos Open-Meteo."""
        df = DataNormalizer.normalize_openmeteo(
            mock_openmeteo_response, 
            6.244, 
            -75.581, 
            "Medellín"
        )
        
        # Verificar estructura
        assert not df.empty
        assert len(df) == 3
        assert "timestamp" in df.columns
        assert "temperatura_c" in df.columns
        assert "humedad_porcentaje" in df.columns
        assert "velocidad_viento_kmh" in df.columns
        
        # Verificar tipos
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])
        assert pd.api.types.is_numeric_dtype(df["temperatura_c"])
        
        # Verificar valores
        assert df["temperatura_c"].iloc[0] == 20.5
        assert df["humedad_porcentaje"].iloc[0] == 65.0
        assert df["source"].iloc[0] == "open-meteo"
    
    def test_openmeteo_data_quality(self, mock_openmeteo_response):
        """Prueba calidad de datos normalizados de Open-Meteo."""
        df = DataNormalizer.normalize_openmeteo(
            mock_openmeteo_response, 
            6.244, 
            -75.581, 
            "Medellín"
        )
        
        is_valid, errors = DataNormalizer.validate_dataframe(df)
        # Debería pasar validación básica
        assert not errors or len(errors) == 0


class TestOpenWeatherMapAPI:
    """Pruebas para la API OpenWeatherMap."""
    
    @pytest.fixture
    def mock_owm_response(self):
        """Respuesta simulada de OpenWeatherMap."""
        return {
            "coord": {"lon": -75.581, "lat": 6.244},
            "weather": [
                {
                    "id": 803,
                    "main": "Clouds",
                    "description": "broken clouds",
                    "icon": "04d"
                }
            ],
            "main": {
                "temp": 22.5,
                "feels_like": 21.8,
                "temp_min": 20.0,
                "temp_max": 25.0,
                "pressure": 1013,
                "humidity": 65,
                "sea_level": 1013,
                "grnd_level": 1000
            },
            "visibility": 10000,
            "wind": {
                "speed": 5.0,  # m/s
                "deg": 180
            },
            "clouds": {"all": 50},
            "dt": 1704067200,
            "sys": {
                "type": 1,
                "id": 8701,
                "country": "CO",
                "sunrise": 1704085800,
                "sunset": 1704128400
            },
            "timezone": -18000,
            "id": 3674958,
            "name": "Medellín",
            "cod": 200,
            "rain": {"1h": 0.5}
        }
    
    def test_normalize_openweathermap_data(self, mock_owm_response):
        """Prueba normalización de datos OpenWeatherMap."""
        df = DataNormalizer.normalize_openweathermap(
            mock_owm_response, 
            "Medellín"
        )
        
        # Verificar estructura
        assert not df.empty
        assert len(df) == 1
        assert "timestamp" in df.columns
        assert "temperatura_c" in df.columns
        assert "humedad_porcentaje" in df.columns
        
        # Verificar valores
        assert df["temperatura_c"].iloc[0] == 22.5
        assert df["humedad_porcentaje"].iloc[0] == 65.0
        assert df["source"].iloc[0] == "openweathermap"
        
        # Verificar conversión de velocidad (5 m/s -> 18 km/h)
        wind_kmh = df["velocidad_viento_kmh"].iloc[0]
        assert wind_kmh is not None
        assert abs(wind_kmh - 18.0) < 1.0  # Aproximadamente 18 km/h
    
    def test_owm_wind_speed_conversion(self, mock_owm_response):
        """Prueba conversión de unidades de velocidad del viento."""
        df = DataNormalizer.normalize_openweathermap(mock_owm_response)
        
        # 5 m/s * 3.6 = 18 km/h
        expected_wind = 5.0 * 3.6
        actual_wind = df["velocidad_viento_kmh"].iloc[0]
        
        assert actual_wind is not None
        assert abs(actual_wind - expected_wind) < 0.1


class TestDataValidation:
    """Pruebas para validación de datos de todas las APIs."""
    
    def test_validate_temperature_range(self):
        """Prueba validación de rangos de temperatura."""
        # Válido
        assert DataValidator.validate_temperature(20.0) == 20.0
        assert DataValidator.validate_temperature(-10.0) == -10.0
        assert DataValidator.validate_temperature(50.0) == 50.0
        
        # Inválido
        assert DataValidator.validate_temperature(100.0) is None  # Fuera de rango
        assert DataValidator.validate_temperature(-60.0) is None  # Fuera de rango
    
    def test_validate_humidity_range(self):
        """Prueba validación de rango de humedad."""
        assert DataValidator.validate_humidity(50.0) == 50.0
        assert DataValidator.validate_humidity(0.0) == 0.0
        assert DataValidator.validate_humidity(100.0) == 100.0
        
        assert DataValidator.validate_humidity(-10.0) is None
        assert DataValidator.validate_humidity(150.0) is None
    
    def test_validate_precipitation(self):
        """Prueba validación de precipitación."""
        assert DataValidator.validate_precipitation(10.0) == 10.0
        assert DataValidator.validate_precipitation(0.0) == 0.0
        assert DataValidator.validate_precipitation(None) == 0.0
        
        assert DataValidator.validate_precipitation(-5.0) == 0.0  # Negativo -> 0
    
    def test_validate_wind_speed(self):
        """Prueba validación de velocidad del viento."""
        # Válido
        assert DataValidator.validate_wind_speed(10.0) == 10.0
        assert DataValidator.validate_wind_speed(0.0) == 0.0
        
        # Inválido
        assert DataValidator.validate_wind_speed(250.0) is None  # Fuera de rango


class TestDataComparison:
    """Pruebas para comparación de datos entre APIs."""
    
    @pytest.fixture
    def sample_dataframes(self):
        """Crea DataFrames de prueba para múltiples APIs."""
        now = pd.Timestamp.now(tz='UTC')
        
        df_openmeteo = pd.DataFrame({
            "timestamp": [now, now + timedelta(hours=1)],
            "temperatura_c": [20.5, 19.2],
            "humedad_porcentaje": [65.0, 70.0],
            "precipitacion_mm": [0.0, 0.5],
            "velocidad_viento_kmh": [10.0, 12.5],
            "source": ["open-meteo", "open-meteo"],
        })
        
        df_owm = pd.DataFrame({
            "timestamp": [now],
            "temperatura_c": [22.5],
            "humedad_porcentaje": [65.0],
            "precipitacion_mm": [0.5],
            "velocidad_viento_kmh": [18.0],
            "source": ["openweathermap"],
        })
        
        return {
            "open-meteo": df_openmeteo,
            "openweathermap": df_owm
        }
    
    def test_combine_multiple_sources(self, sample_dataframes):
        """Prueba combinación de datos de múltiples APIs."""
        combined = DataNormalizer.combine_sources(sample_dataframes)
        
        assert not combined.empty
        assert len(combined) >= 2  # Al menos 2 registros
        assert "source" in combined.columns
        assert combined["source"].nunique() == 2  # Dos fuentes distintas
    
    def test_temperature_comparison(self, sample_dataframes):
        """Prueba comparación de temperaturas entre APIs."""
        combined = DataNormalizer.combine_sources(sample_dataframes)
        
        # Open-Meteo: 20.5°C
        # OpenWeatherMap: 22.5°C (diferencia de 2°C)
        temperatures = combined["temperatura_c"].dropna().values
        assert len(temperatures) > 0
        assert max(temperatures) - min(temperatures) <= 10  # Diferencia razonable


class TestDataDiagnostics:
    """Pruebas para diagnóstico de datos."""
    
    def test_find_numeric_columns(self):
        """Prueba detección de columnas numéricas."""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=3),
            "temperature_2m": [20.5, 19.2, 18.1],
            "relative_humidity_2m": [65, 70, 75],
            "wind_speed_10m": [10.0, 12.5, 15.0],
            "city": ["Medellín", "Medellín", "Medellín"]
        })
        
        numeric_by_cat = DataDiagnostics.find_numeric_columns(df)
        
        assert "temperatura" in numeric_by_cat
        assert "humedad" in numeric_by_cat
        assert "viento" in numeric_by_cat
    
    def test_auto_normalize_columns(self):
        """Prueba normalización automática de columnas."""
        df = pd.DataFrame({
            "timestamp": ["2025-01-01T00:00", "2025-01-01T01:00"],
            "temperature_2m": [20.5, 19.2],
            "relative_humidity_2m": [65, 70],
        })
        
        df_normalized, mapping = DataDiagnostics.auto_normalize_columns(df)
        
        assert not df_normalized.empty
        assert pd.api.types.is_datetime64_any_dtype(df_normalized["timestamp"])
        assert "timestamp" in mapping or "timestamp" in df_normalized.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])