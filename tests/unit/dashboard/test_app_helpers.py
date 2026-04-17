"""
Pruebas unitarias para helpers de dashboard/app.py

Verifica:
- Carga de datos desde CSV
- Normalización de columnas en CSVs de API
- Funciones de fetch para MeteoBlue
- Funciones de creación de gráficos (sin ejecutar Streamlit)
"""

import os
import sys
import pytest
import pandas as pd
from unittest.mock import patch, Mock

# Añadir el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dashboard.app import (
    load_data,
    _load_api_csv_as_standard,
    fetch_meteoblue_points,
    create_temperature_chart,
    create_humidity_chart,
    create_precipitation_chart,
    create_wind_speed_chart
)


class TestLoadData:
    """Pruebas para load_data."""

    @patch('dashboard.app.load_from_csv')
    def test_load_data_exito(self, mock_load_csv, sample_dataframe):
        """Carga datos correctamente desde CSV."""
        mock_load_csv.return_value = sample_dataframe

        result = load_data("data/weather_data.csv")
        assert not result.empty
        assert "temperatura_c" in result.columns
        mock_load_csv.assert_called_once_with("data/weather_data.csv")

    @patch('dashboard.app.load_from_csv')
    def test_load_data_archivo_no_encontrado(self, mock_load_csv):
        """Archivo no encontrado debe mostrar error y detener."""
        mock_load_csv.side_effect = FileNotFoundError()

        with pytest.raises(SystemExit):  # st.stop() detiene la ejecución
            load_data("archivo_inexistente.csv")


class TestLoadApiCsvAsStandard:
    """Pruebas para _load_api_csv_as_standard."""

    def test_load_api_csv_as_standard_con_columnas_validas(self, tmp_path):
        """Normaliza CSV con columnas válidas."""
        csv_content = """timestamp,temperature,humidity,wind_speed,precipitation
2024-01-01T00:00:00Z,25.0,70.0,5.0,0.0
2024-01-01T01:00:00Z,26.0,75.0,6.0,0.5"""

        csv_file = tmp_path / "api_data.csv"
        csv_file.write_text(csv_content)

        df = _load_api_csv_as_standard(str(csv_file))

        assert not df.empty
        assert len(df) == 2
        assert "temperatura_c" in df.columns
        assert "humedad_porcentaje" in df.columns
        assert "velocidad_viento_kmh" in df.columns
        assert "precipitacion_mm" in df.columns

        # Verificar valores
        assert df["temperatura_c"].iloc[0] == 25.0
        assert df["humedad_porcentaje"].iloc[0] == 70.0

    def test_load_api_csv_as_standard_sin_columnas_validas(self, tmp_path):
        """CSV sin columnas válidas debe retornar DataFrame vacío."""
        csv_content = """fecha,valor
2024-01-01,100"""

        csv_file = tmp_path / "api_data.csv"
        csv_file.write_text(csv_content)

        df = _load_api_csv_as_standard(str(csv_file))
        assert df.empty

    def test_load_api_csv_as_standard_archivo_no_existe(self):
        """Archivo inexistente debe retornar DataFrame vacío."""
        df = _load_api_csv_as_standard("archivo_inexistente.csv")
        assert df.empty

    def test_load_api_csv_as_standard_con_timestamp_index(self, tmp_path):
        """Maneja correctamente timestamp como índice."""
        csv_content = """timestamp,temp,humidity
2024-01-01T00:00:00Z,25.0,70.0"""

        csv_file = tmp_path / "api_data.csv"
        csv_file.write_text(csv_content)

        df = _load_api_csv_as_standard(str(csv_file))
        assert isinstance(df.index, pd.DatetimeIndex)


class TestFetchMeteobluePoints:
    """Pruebas para fetch_meteoblue_points."""

    @patch('dashboard.app.requests.get')
    def test_fetch_meteoblue_points_current_exito(self, mock_get):
        """Obtiene puntos actuales correctamente."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "timestamp": "2024-01-01T12:00:00Z",
                "temperature": 25.0,
                "location": "Medellín"
            }
        }
        mock_get.return_value = mock_response

        points = fetch_meteoblue_points(mode="current")

        assert len(points) == 1
        assert points[0]["timestamp"] == "2024-01-01T12:00:00Z"
        assert points[0]["temperature"] == 25.0
        assert points[0]["location"] == "Medellín"

    @patch('dashboard.app.requests.get')
    def test_fetch_meteoblue_points_forecast_exito(self, mock_get):
        """Obtiene puntos de forecast correctamente."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "data": {
                "days": [
                    {"date": "2024-01-01", "temp_max": 25.0, "location_id": "Medellín"},
                    {"date": "2024-01-02", "temp_max": 26.0, "location_id": "Medellín"}
                ]
            }
        }
        mock_get.return_value = mock_response

        points = fetch_meteoblue_points(mode="forecast")

        assert len(points) == 2
        assert points[0]["timestamp"] == "2024-01-01T12:00:00"
        assert points[0]["temperature"] == 25.0
        assert points[1]["timestamp"] == "2024-01-02T12:00:00"
        assert points[1]["temperature"] == 26.0

    @patch('dashboard.app.requests.get')
    def test_fetch_meteoblue_points_error(self, mock_get):
        """Error en request debe retornar lista vacía."""
        mock_get.side_effect = Exception("Network error")

        points = fetch_meteoblue_points()
        assert points == []


class TestChartFunctions:
    """Pruebas para funciones de creación de gráficos."""

    def test_create_temperature_chart(self, sample_dataframe):
        """Crea gráfico de temperatura correctamente."""
        date_range = (sample_dataframe.index[0], sample_dataframe.index[-1])

        fig = create_temperature_chart(sample_dataframe, date_range)

        assert fig is not None
        assert fig.data[0].name == "temperatura_c"
        assert "Temperatura (°C)" in fig.layout.title.text

    def test_create_humidity_chart(self, sample_dataframe):
        """Crea gráfico de humedad correctamente."""
        date_range = (sample_dataframe.index[0], sample_dataframe.index[-1])

        fig = create_humidity_chart(sample_dataframe, date_range)

        assert fig is not None
        assert "Humedad Relativa (%)" in fig.layout.title.text

    def test_create_precipitation_chart(self, sample_dataframe):
        """Crea gráfico de precipitación correctamente."""
        date_range = (sample_dataframe.index[0], sample_dataframe.index[-1])

        fig = create_precipitation_chart(sample_dataframe, date_range)

        assert fig is not None
        assert "Precipitación (mm)" in fig.layout.title.text

    def test_create_wind_speed_chart(self, sample_dataframe):
        """Crea gráfico de velocidad del viento correctamente."""
        date_range = (sample_dataframe.index[0], sample_dataframe.index[-1])

        fig = create_wind_speed_chart(sample_dataframe, date_range)

        assert fig is not None
        assert "Velocidad del Viento (km/h)" in fig.layout.title.text

    def test_chart_functions_con_rango_filtrado(self, sample_dataframe):
        """Gráficos filtran correctamente por rango de fechas."""
        # Rango que incluye solo el primer punto
        start_date = sample_dataframe.index[0]
        end_date = sample_dataframe.index[0]

        fig = create_temperature_chart(sample_dataframe, (start_date, end_date))

        # Verificar que el gráfico tiene solo un punto
        assert len(fig.data[0].x) == 1
        assert fig.data[0].y[0] == sample_dataframe["temperatura_c"].iloc[0]