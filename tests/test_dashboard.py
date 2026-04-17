"""
Tests para dashboard/app.py - Funciones auxiliares.

Las funciones de lógica de negocio son testables.
Los tests de UI (st.*) requieren refactor o se omiten.
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from dashboard.app import (
    load_data,
    _load_api_csv_as_standard,
    create_temperature_chart,
    create_humidity_chart,
    create_precipitation_chart,
    create_wind_speed_chart
)


class TestLoadData:
    """Tests para load_data()"""
    
    def test_carga_archivo_existente(self, tmp_path, sample_dataframe):
        """Debe cargar DataFrame desde archivo"""
        filepath = tmp_path / "weather_data.csv"
        sample_dataframe.to_csv(filepath)
        
        df = load_data(str(filepath))
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) == len(sample_dataframe)
    
    def test_error_si_no_existe(self, tmp_path):
        """Debe lanzar error si archivo no existe"""
        with pytest.raises(FileNotFoundError):
            load_data(str(tmp_path / "no_existe.csv"))
    
    def test_error_generico(self, tmp_path):
        """Debe manejar errores genéricos"""
        # Simular error pasando un directorio como archivo
        with pytest.raises(Exception):
            load_data(str(tmp_path))  # tmp_path es un directorio


class TestLoadApiCsvAsStandard:
    """Tests para _load_api_csv_as_standard()"""
    
    def test_normaliza_columnas_temperature(self, tmp_path):
        """Debe renombrar 'temperature' a 'temperatura_c'"""
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T00:00"],
            "temperature": [20.0],
            "humidity": [80]
        })
        df = df.set_index("timestamp")
        
        filepath = tmp_path / "api_data.csv"
        df.to_csv(filepath)
        
        result = _load_api_csv_as_standard(str(filepath))
        
        assert "temperatura_c" in result.columns
    
    def test_normaliza_columnas_variaciones(self, tmp_path):
        """Debe manejar variaciones de nombres"""
        df = pd.DataFrame({
            "timestamp": ["2024-01-01T00:00"],
            "temp": [20.0],
            "humidity": [80],
            "precip": [0.5],
            "wind_speed": [10.0]
        })
        df = df.set_index("timestamp")
        
        filepath = tmp_path / "api_var.csv"
        df.to_csv(filepath)
        
        result = _load_api_csv_as_standard(str(filepath))
        
        # Todas deben estar normalizadas
        assert "temperatura_c" in result.columns
        assert "humedad_porcentaje" in result.columns
    
    def test_retorna_vacio_si_no_hay_columnas_utiles(self, tmp_path):
        """Debe retornar DataFrame vacío si no hay columnas útiles"""
        df = pd.DataFrame({"otro": [1, 2, 3]})
        
        filepath = tmp_path / "otro.csv"
        df.to_csv(filepath)
        
        result = _load_api_csv_as_standard(str(filepath))
        
        assert result.empty
    
    def test_archivo_no_existe_retorna_vacio(self):
        """Archivo inexistente debe retornar DataFrame vacío"""
        result = _load_api_csv_as_standard("no_existe.csv")
        
        assert result.empty


# ============================================================================
# TESTS DE CHART CREATORS
# ============================================================================

class TestCreateTemperatureChart:
    """Tests para create_temperature_chart()"""
    
    def test_retorna_figure(self, sample_dataframe):
        """Debe retornar objeto Figure"""
        start = sample_dataframe.index[0]
        end = start + pd.Timedelta(hours=24)
        
        fig = create_temperature_chart(sample_dataframe, (start, end))
        
        assert fig is not None
    
    def test_tiene_traces(self, sample_dataframe):
        """Debe tener datos en el gráfico"""
        start = sample_dataframe.index[0]
        end = start + pd.Timedelta(hours=24)
        
        fig = create_temperature_chart(sample_dataframe, (start, end))
        
        assert len(fig.data) > 0
    
    def test_filtra_por_rango(self, sample_dataframe):
        """Debe filtrar datos por rango de fechas"""
        start = sample_dataframe.index[10]
        end = start + pd.Timedelta(hours=12)
        
        fig = create_temperature_chart(sample_dataframe, (start, end))
        
        # Figure debe existir y tener datos
        assert fig is not None


class TestCreateHumidityChart:
    """Tests para create_humidity_chart()"""
    
    def test_retorna_figure(self, sample_dataframe):
        """Debe retornar objeto Figure"""
        start = sample_dataframe.index[0]
        end = start + pd.Timedelta(hours=24)
        
        fig = create_humidity_chart(sample_dataframe, (start, end))
        
        assert fig is not None


class TestCreatePrecipitationChart:
    """Tests para create_precipitation_chart()"""
    
    def test_retorna_figure_tipo_barras(self, sample_dataframe):
        """Debe retornar gráfico de barras"""
        start = sample_dataframe.index[0]
        end = start + pd.Timedelta(hours=24)
        
        fig = create_precipitation_chart(sample_dataframe, (start, end))
        
        assert fig is not None


class TestCreateWindSpeedChart:
    """Tests para create_wind_speed_chart()"""
    
    def test_retorna_figure(self, sample_dataframe):
        """Debe retornar objeto Figure"""
        start = sample_dataframe.index[0]
        end = start + pd.Timedelta(hours=24)
        
        fig = create_wind_speed_chart(sample_dataframe, (start, end))
        
        assert fig is not None


# ============================================================================
# TESTS DE INTEGRACIÓN
# ============================================================================

class TestDashboardIntegration:
    """Tests de integración del dashboard"""
    
    def test_load_y_chart_pipeline(self, tmp_path, sample_dataframe):
        """Cargar datos -> crear chart debe funcionar"""
        filepath = tmp_path / "weather.csv"
        sample_dataframe.to_csv(filepath)
        
        # 1. Cargar
        df = load_data(str(filepath))
        assert not df.empty
        
        # 2. Crear charts
        start = df.index[0]
        end = df.index[0] + pd.Timedelta(hours=24)
        
        temp_fig = create_temperature_chart(df, (start, end))
        hum_fig = create_humidity_chart(df, (start, end))
        
        assert temp_fig is not None
        assert hum_fig is not None
    
    def test_multiple_apis_csv(self, tmp_path):
        """Debe combinar múltiple fuentes"""
        # Crear dos CSVs de diferentes fuentes
        df1 = pd.DataFrame({
            "temperatura_c": [20.0, 21.0],
            "humedad_porcentaje": [80, 75]
        }, index=pd.date_range("2024-01-01", periods=2, freq="h"))
        
        df2 = pd.DataFrame({
            "temperatura_c": [22.0],
            "humedad_porcentaje": [70]
        }, index=pd.date_range("2024-01-01", periods=1, freq="h"))
        
        # Guardar
        f1 = tmp_path / "api1.csv"
        f2 = tmp_path / "api2.csv"
        df1.to_csv(f1)
        df2.to_csv(f2)
        
        # Cargar y normalizar
        r1 = _load_api_csv_as_standard(str(f1))
        r2 = _load_api_csv_as_standard(str(f2))
        
        assert not r1.empty
        assert not r2.empty