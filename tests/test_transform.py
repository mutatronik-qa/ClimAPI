"""
Tests para processing/transform.py

Funciones testeadas:
- json_to_dataframe()
- clean_and_standardize()
- process_weather_data()
"""

import pytest
import pandas as pd
from datetime import datetime
import numpy as np

from processing.transform import (
    json_to_dataframe,
    clean_and_standardize,
    process_weather_data
)


class TestJsonToDataframe:
    """Tests para json_to_dataframe()"""
    
    def test_convierte_response_a_dataframe(self, sample_api_response):
        """Verifica conversión básica de JSON a DataFrame"""
        df = json_to_dataframe(sample_api_response)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_api_response["hourly"]["time"])
        assert "time" in df.columns
    
    def test_extrae_todas_las_columnas(self, sample_api_response):
        """Verifica que se extraen todas las variables"""
        df = json_to_dataframe(sample_api_response)
        
        expected_cols = [
            "time", "temperature_2m", "relative_humidity_2m", 
            "precipitation", "weather_code", "wind_speed_10m", "visibility"
        ]
        for col in expected_cols:
            assert col in df.columns
    
    def test_error_si_no_hay_hourly(self):
        """Debe lanzar error si no hay datos hourly"""
        with pytest.raises(ValueError, match="datos horarios"):
            json_to_dataframe({})


class TestCleanAndStandardize:
    """Tests para clean_and_standardize()"""
    
    def test_convierte_time_a_indice(self, sample_api_response):
        """La columna 'time' debe convertirse en índice"""
        df_raw = json_to_dataframe(sample_api_response)
        df = clean_and_standardize(df_raw)
        
        assert isinstance(df.index, pd.DatetimeIndex)
    
    def test_renombra_columnas(self, sample_api_response):
        """Verifica renombrado de columnas a español"""
        df_raw = json_to_dataframe(sample_api_response)
        df = clean_and_standardize(df_raw)
        
        assert "temperatura_c" in df.columns
        assert "humedad_porcentaje" in df.columns
        assert "precipitacion_mm" in df.columns
        assert "velocidad_viento_kmh" in df.columns
    
    def test_elimina_filas_con_temperature_nula(self):
        """Debe eliminar filas donde temperatura es None"""
        df_with_nulls = pd.DataFrame({
            "time": ["2024-01-01T00:00", "2024-01-01T01:00", "2024-01-01T02:00"],
            "temperature_2m": [20.0, None, 22.0],
            "relative_humidity_2m": [80, 75, 70],
            "precipitation": [0.0, 0.0, 0.0],
            "wind_speed_10m": [10.0, 11.0, 12.0]
        })
        
        df = clean_and_standardize(df_with_nulls)
        
        # Solo debe quedar 2 filas (sin la null)
        assert len(df) == 2
        assert df["temperatura_c"].notna().all()
    
    def test_redondea_a_dos_decimales(self, sample_api_response):
        """Valores deben redondearse a 2 decimales"""
        df_raw = json_to_dataframe(sample_api_response)
        df = clean_and_standardize(df_raw)
        
        # Verificar que valores son float con máximo 2 decimales
        for col in ["temperatura_c", "humedad_porcentaje"]:
            decimals = df[col].astype(str).str.split(".").str[-1].str.len().fillna(0)
            assert decimals.max() <= 2


class TestProcessWeatherData:
    """Tests para process_weather_data() - función principal"""
    
    def test_proceso_completo(self, sample_api_response):
        """Verifica flujo completo de procesamiento"""
        df = process_weather_data(sample_api_response)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 48
        assert_dataframe_schema(df)
    
    def test_output_schema_correcto(self, sample_api_response):
        """El schema del output debe ser el esperado"""
        df = process_weather_data(sample_api_response)
        
        # Verificar columnas exactas
        expected = ["temperatura_c", "humedad_porcentaje", "precipitacion_mm", "velocidad_viento_kmh"]
        assert list(df.columns) == expected
    
    def test_index_es_datetime(self, sample_api_response):
        """El índice debe ser datetime"""
        df = process_weather_data(sample_api_response)
        
        assert pd.api.types.is_datetime64_any_dtype(df.index)


# ============================================================================
# HELPERS
# ============================================================================

def assert_dataframe_schema(df: pd.DataFrame):
    """Verifica schema esperado del DataFrame."""
    expected_cols = ["temperatura_c", "humedad_porcentaje", "precipitacion_mm", "velocidad_viento_kmh"]
    for col in expected_cols:
        assert col in df.columns, f"Columna faltante: {col}"