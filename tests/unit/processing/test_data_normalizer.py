"""
Pruebas unitarias para processing/data_normalizer.py

Verifica:
- Normalización de datos de diferentes APIs
- Validación de valores y rangos
- Conversión de unidades
- Manejo de valores nulos/inválidos
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np

# Añadir el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from processing.data_normalizer import (
    DataNormalizer,
    DataValidator,
    TemperatureUnit,
    WindSpeedUnit,
    PressureUnit
)


class TestDataValidator:
    """Pruebas para DataValidator."""

    def test_validate_temperature_celsius_valido(self):
        """Temperatura Celsius válida debe retornar el valor."""
        result = DataValidator.validate_temperature(25.0, TemperatureUnit.CELSIUS)
        assert result == 25.0

    def test_validate_temperature_fahrenheit_conversion(self):
        """Temperatura Fahrenheit debe convertirse a Celsius."""
        result = DataValidator.validate_temperature(77.0, TemperatureUnit.FAHRENHEIT)
        assert result == pytest.approx(25.0, abs=0.1)

    def test_validate_temperature_kelvin_conversion(self):
        """Temperatura Kelvin debe convertirse a Celsius."""
        result = DataValidator.validate_temperature(298.15, TemperatureUnit.KELVIN)
        assert result == pytest.approx(25.0, abs=0.1)

    def test_validate_temperature_fuera_rango(self):
        """Temperatura fuera de rango debe retornar None."""
        result = DataValidator.validate_temperature(-100.0, TemperatureUnit.CELSIUS)
        assert result is None

    def test_validate_temperature_none(self):
        """Valor None debe retornar None."""
        result = DataValidator.validate_temperature(None, TemperatureUnit.CELSIUS)
        assert result is None

    def test_validate_humidity_valida(self):
        """Humedad válida debe retornar el valor."""
        result = DataValidator.validate_humidity(70.0)
        assert result == 70.0

    def test_validate_humidity_fuera_rango(self):
        """Humedad fuera de rango debe retornar None."""
        result = DataValidator.validate_humidity(150.0)
        assert result is None

    def test_validate_precipitation_valida(self):
        """Precipitación válida debe retornar el valor."""
        result = DataValidator.validate_precipitation(5.0)
        assert result == 5.0

    def test_validate_precipitation_negativa(self):
        """Precipitación negativa debe retornar 0.0."""
        result = DataValidator.validate_precipitation(-1.0)
        assert result == 0.0

    def test_validate_wind_speed_kmh_valido(self):
        """Velocidad del viento km/h válida debe retornar el valor."""
        result = DataValidator.validate_wind_speed(10.0, WindSpeedUnit.KMH)
        assert result == 10.0

    def test_validate_wind_speed_ms_conversion(self):
        """Velocidad del viento m/s debe convertirse a km/h."""
        result = DataValidator.validate_wind_speed(5.0, WindSpeedUnit.MS)
        assert result == 18.0

    def test_validate_wind_speed_fuera_rango(self):
        """Velocidad del viento fuera de rango debe retornar None."""
        result = DataValidator.validate_wind_speed(300.0, WindSpeedUnit.KMH)
        assert result is None

    def test_validate_pressure_hpa_valido(self):
        """Presión hPa válida debe retornar el valor."""
        result = DataValidator.validate_pressure(1013.0, PressureUnit.HPA)
        assert result == 1013.0

    def test_validate_pressure_mmhg_conversion(self):
        """Presión mmHg debe convertirse a hPa."""
        result = DataValidator.validate_pressure(760.0, PressureUnit.MMHG)
        assert result == pytest.approx(1013.25, abs=0.1)

    def test_validate_wind_direction_valida(self):
        """Dirección del viento válida debe normalizarse."""
        result = DataValidator.validate_wind_direction(450.0)  # 450° -> 90°
        assert result == 90.0

    def test_validate_percentage_valida(self):
        """Porcentaje válido debe retornar el valor."""
        result = DataValidator.validate_percentage(75.0)
        assert result == 75.0

    def test_validate_percentage_fuera_rango(self):
        """Porcentaje fuera de rango debe retornar None."""
        result = DataValidator.validate_percentage(150.0)
        assert result is None


class TestDataNormalizer:
    """Pruebas para DataNormalizer."""

    def test_normalize_openmeteo_exito(self, sample_openmeteo_response):
        """Normaliza respuesta Open-Meteo correctamente."""
        df = DataNormalizer.normalize_openmeteo(
            sample_openmeteo_response,
            lat=6.244,
            lon=-75.581,
            city="Medellín"
        )

        assert not df.empty
        assert len(df) == 3
        assert df.index.name == "timestamp"
        assert "temperatura_c" in df.columns
        assert "humedad_porcentaje" in df.columns
        assert "precipitacion_mm" in df.columns
        assert "velocidad_viento_kmh" in df.columns

        # Verificar valores
        assert df["temperatura_c"].iloc[0] == 25.0
        assert df["humedad_porcentaje"].iloc[0] == 70.0
        assert df["precipitacion_mm"].iloc[0] == 0.0
        assert df["velocidad_viento_kmh"].iloc[0] == 5.0

        # Verificar metadata
        assert df["source"].iloc[0] == "open-meteo"
        assert df["latitude"].iloc[0] == 6.244
        assert df["longitude"].iloc[0] == -75.581
        assert df["city"].iloc[0] == "Medellín"

    def test_normalize_openmeteo_sin_datos(self):
        """Respuesta sin datos hourly debe retornar DataFrame vacío."""
        response_sin_datos = {
            "latitude": 6.244,
            "longitude": -75.581,
            "hourly": {"time": []}
        }

        df = DataNormalizer.normalize_openmeteo(response_sin_datos, 6.244, -75.581)
        assert df.empty

    def test_normalize_openmeteo_con_valores_invalidos(self):
        """Valores inválidos deben ser limpiados."""
        response_invalida = {
            "latitude": 6.244,
            "longitude": -75.581,
            "hourly": {
                "time": ["2024-01-01T00:00:00Z"],
                "temperature_2m": [-100.0],  # Inválido
                "relative_humidity_2m": [70.0],
                "precipitation": [0.0],
                "wind_speed_10m": [5.0]
            }
        }

        df = DataNormalizer.normalize_openmeteo(response_invalida, 6.244, -75.581)
        assert not df.empty
        assert pd.isna(df["temperatura_c"].iloc[0])  # Debe ser NaN

    def test_normalize_openweathermap_exito(self, sample_openweathermap_response):
        """Normaliza respuesta OpenWeatherMap correctamente."""
        df = DataNormalizer.normalize_openweathermap(
            sample_openweathermap_response,
            city="Medellín"
        )

        assert not df.empty
        assert len(df) == 1
        assert df.index.name == "timestamp"
        assert "temperatura_c" in df.columns
        assert "humedad_porcentaje" in df.columns
        assert "precipitacion_mm" in df.columns
        assert "velocidad_viento_kmh" in df.columns

        # Verificar valores (conversión de unidades)
        assert df["temperatura_c"].iloc[0] == 25.0
        assert df["humedad_porcentaje"].iloc[0] == 70.0
        assert df["precipitacion_mm"].iloc[0] == 0.0
        assert df["velocidad_viento_kmh"].iloc[0] == 18.0  # 5 m/s -> 18 km/h

        # Verificar metadata
        assert df["source"].iloc[0] == "openweathermap"
        assert df["latitude"].iloc[0] == -75.581  # Nota: coord.lon
        assert df["longitude"].iloc[0] == 6.244   # Nota: coord.lat
        assert df["city"].iloc[0] == "Medellín"

    def test_normalize_openweathermap_sin_rain(self):
        """OpenWeatherMap sin datos de lluvia debe manejar correctamente."""
        response_sin_rain = {
            "coord": {"lon": -75.581, "lat": 6.244},
            "main": {"temp": 25.0, "humidity": 70.0, "pressure": 1013.0},
            "wind": {"speed": 5.0, "deg": 180.0},
            "clouds": {"all": 20.0},
            "dt": 1704067200
        }

        df = DataNormalizer.normalize_openweathermap(response_sin_rain)
        assert df["precipitacion_mm"].iloc[0] == 0.0

    def test_normalize_meteoblue_exito(self):
        """Normaliza datos MeteoBlue correctamente."""
        meteoblue_data = {
            "time": ["2024-01-01T00:00:00Z"],
            "temperature": [25.0],
            "humidity": [70.0],
            "precipitation": [0.0],
            "wind_speed": [5.0],
            "wind_direction": [180.0],
            "pressure": [1013.0],
            "cloudcover": [20.0],
            "dew_point": [18.0],
            "visibility": [10000.0],
            "solar_radiation": [0.0]
        }

        df = DataNormalizer.normalize_meteoblue(meteoblue_data, 6.244, -75.581)
        assert not df.empty
        assert df["source"].iloc[0] == "meteoblue"
        assert df["temperatura_c"].iloc[0] == 25.0