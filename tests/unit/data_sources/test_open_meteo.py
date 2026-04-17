"""
Pruebas unitarias para data_sources/open_meteo.py

Verifica:
- Validación de coordenadas
- Construcción de parámetros de API
- Manejo de errores HTTP
- Geocodificación de ciudades
"""

import os
import sys

# Añadir el directorio raíz del proyecto al path ANTES de cualquier import
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

import pytest
import requests
from unittest.mock import patch, Mock

from data_sources.open_meteo import (    validate_coordinates,
    get_weather_data,
    get_weather_by_city_name
)



class TestValidateCoordinates:
    """Pruebas para validate_coordinates."""

    def test_validate_coordinates_validas(self):
        """Coordenadas válidas deben retornar la tupla sin cambios."""
        lat, lon = validate_coordinates(6.244, -75.581)
        assert lat == 6.244
        assert lon == -75.581

    def test_validate_coordinates_latitud_invalida_baja(self):
        """Latitud menor a -90 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="Latitud inválida"):
            validate_coordinates(-91.0, -75.581)

    def test_validate_coordinates_latitud_invalida_alta(self):
        """Latitud mayor a 90 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="Latitud inválida"):
            validate_coordinates(91.0, -75.581)

    def test_validate_coordinates_longitud_invalida_baja(self):
        """Longitud menor a -180 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="Longitud inválida"):
            validate_coordinates(6.244, -181.0)

    def test_validate_coordinates_longitud_invalida_alta(self):
        """Longitud mayor a 180 debe lanzar ValueError."""
        with pytest.raises(ValueError, match="Longitud inválida"):
            validate_coordinates(6.244, 181.0)


class TestGetWeatherData:
    """Pruebas para get_weather_data."""

    @patch('data_sources.open_meteo.requests.get')
    def test_get_weather_data_construye_parametros_correctos(self, mock_get, sample_openmeteo_response):
        """Debe construir la URL y parámetros correctamente."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = sample_openmeteo_response
        mock_get.return_value = mock_response

        result = get_weather_data(
            latitude=6.244,
            longitude=-75.581,
            timezone="America/Bogota"
        )

        # Verificar que se llamó con la URL correcta
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[0][0] == "https://api.open-meteo.com/v1/forecast"

        # Verificar parámetros
        params = call_args[1]['params']
        assert params['latitude'] == 6.244
        assert params['longitude'] == -75.581
        assert params['timezone'] == "America/Bogota"
        assert 'temperature_2m' in params['hourly']
        assert 'relative_humidity_2m' in params['hourly']

        # Verificar resultado
        assert result == sample_openmeteo_response

    @patch('data_sources.open_meteo.requests.get')
    def test_get_weather_data_maneja_timeout(self, mock_get):
        """Debe lanzar TimeoutError cuando hay timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with pytest.raises(TimeoutError, match="API Open-Meteo tardó demasiado"):
            get_weather_data(latitude=6.244, longitude=-75.581)

    @patch('data_sources.open_meteo.requests.get')
    def test_get_weather_data_maneja_connection_error(self, mock_get):
        """Debe lanzar ConnectionError cuando falla la conexión."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        with pytest.raises(ConnectionError, match="No se pudo conectar a Open-Meteo"):
            get_weather_data(latitude=6.244, longitude=-75.581)

    @patch('data_sources.open_meteo.requests.get')
    def test_get_weather_data_maneja_http_error(self, mock_get):
        """Debe lanzar Exception cuando hay error HTTP."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        response = Mock(status_code=404)
        mock_response.raise_for_status.side_effect.response = response
        mock_get.return_value = mock_response

        with pytest.raises(Exception, match="Error en API Open-Meteo"):
            get_weather_data(latitude=6.244, longitude=-75.581)


class TestGetWeatherByCityName:
    """Pruebas para get_weather_by_city_name."""

    @patch('data_sources.open_meteo.requests.get')
    def test_get_weather_by_city_name_exito(self, mock_get, sample_openmeteo_response):
        """Debe geocodificar y obtener datos correctamente."""
        # Mock geocoding response
        geocode_response = Mock()
        geocode_response.raise_for_status.return_value = None
        geocode_response.json.return_value = {
            "results": [{
                "latitude": 6.244,
                "longitude": -75.581,
                "name": "Medellín",
                "country": "Colombia"
            }]
        }

        # Mock weather response
        weather_response = Mock()
        weather_response.raise_for_status.return_value = None
        weather_response.json.return_value = sample_openmeteo_response

        # Configurar mock para llamadas secuenciales
        mock_get.side_effect = [geocode_response, weather_response]

        result = get_weather_by_city_name("Medellín")

        # Verificar geocoding call
        geocode_call = mock_get.call_args_list[0]
        assert geocode_call[0][0] == "https://geocoding-api.open-meteo.com/v1/search"
        assert geocode_call[1]['params']['name'] == "Medellín"

        # Verificar weather call
        weather_call = mock_get.call_args_list[1]
        assert weather_call[0][0] == "https://api.open-meteo.com/v1/forecast"
        params = weather_call[1]['params']
        assert params['latitude'] == 6.244
        assert params['longitude'] == -75.581

        assert result == sample_openmeteo_response

    @patch('data_sources.open_meteo.requests.get')
    def test_get_weather_by_city_name_ciudad_no_encontrada(self, mock_get):
        """Debe lanzar ValueError cuando no encuentra la ciudad."""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response

        with pytest.raises(ValueError, match="Ciudad no encontrada"):
            get_weather_by_city_name("CiudadInexistente")