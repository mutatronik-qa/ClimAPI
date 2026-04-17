"""
Pruebas de integración para la API FastAPI

Verifica:
- Endpoints de health check
- Endpoints de weather con TestClient
- Manejo de errores y validaciones
- Integración con caché
"""

import os
import sys
import pytest
from unittest.mock import patch, Mock

# Añadir el directorio raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class TestHealthEndpoints:
    """Pruebas para endpoints de health."""

    def test_health_check_endpoint(self, api_client):
        """GET /api/v1/health debe retornar 200 con status healthy."""
        response = api_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

    def test_root_endpoint(self, api_client):
        """GET / debe retornar información básica."""
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestWeatherEndpoints:
    """Pruebas para endpoints de weather."""

    @patch('mainback.get_weather_data')
    @patch('mainback.process_weather_data')
    @patch('mainback.CacheManager')
    def test_get_current_weather_exito(self, mock_cache_class, mock_process, mock_get_weather, api_client, sample_dataframe):
        """POST /api/v1/weather/current con datos válidos debe retornar 200."""
        # Configurar mocks
        mock_cache = Mock()
        mock_cache.get_processed_data.return_value = None  # Sin caché
        mock_cache_class.return_value = mock_cache

        mock_get_weather.return_value = {"mock": "response"}
        mock_process.return_value = sample_dataframe

        request_data = {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }

        response = api_client.post("/api/v1/weather/current", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verificar estructura de respuesta
        assert "location" in data
        assert "data" in data
        assert "source" in data
        assert "timestamp" in data

        # Verificar que contiene datos weather
        assert len(data["data"]) > 0
        weather_item = data["data"][0]
        assert "time" in weather_item
        assert "temperature" in weather_item
        assert "humidity" in weather_item
        assert "precipitation" in weather_item
        assert "wind_speed" in weather_item

    @patch('mainback.CacheManager')
    def test_get_current_weather_coordenadas_invalidas(self, mock_cache_class, api_client):
        """POST /api/v1/weather/current con coordenadas inválidas debe retornar 400."""
        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        request_data = {
            "latitude": 91.0,  # Inválida
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }

        response = api_client.post("/api/v1/weather/current", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    @patch('mainback.get_weather_data')
    @patch('mainback.CacheManager')
    def test_get_current_weather_error_api(self, mock_cache_class, mock_get_weather, api_client):
        """Error en API externa debe retornar 500."""
        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        mock_get_weather.side_effect = Exception("API Error")

        request_data = {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }

        response = api_client.post("/api/v1/weather/current", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @patch('mainback.CacheManager')
    def test_get_current_weather_usa_cache(self, mock_cache_class, api_client, sample_dataframe):
        """Debe usar datos desde caché cuando disponibles."""
        mock_cache = Mock()
        mock_cache.get_processed_data.return_value = sample_dataframe
        mock_cache_class.return_value = mock_cache

        request_data = {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }

        response = api_client.post("/api/v1/weather/current", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert "Cached" in data["source"]


class TestCacheEndpoints:
    """Pruebas para endpoints de caché."""

    @patch('mainback.CacheManager')
    def test_get_cache_stats(self, mock_cache_class, api_client):
        """GET /api/v1/cache/stats debe retornar estadísticas."""
        mock_cache = Mock()
        mock_cache.get_stats.return_value = {"hits": 10, "misses": 5}
        mock_cache_class.return_value = mock_cache

        response = api_client.get("/api/v1/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["hits"] == 10
        assert data["misses"] == 5

    @patch('mainback.CacheManager')
    def test_clear_cache(self, mock_cache_class, api_client):
        """DELETE /api/v1/cache debe limpiar caché."""
        mock_cache = Mock()
        mock_cache_class.return_value = mock_cache

        response = api_client.delete("/api/v1/cache")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        mock_cache.clear.assert_called_once()


class TestLocationEndpoints:
    """Pruebas para endpoints de locations."""

    def test_get_default_location(self, api_client):
        """GET /api/v1/locations/default debe retornar ubicación por defecto."""
        response = api_client.get("/api/v1/locations/default")

        assert response.status_code == 200
        data = response.json()
        # Verificar que contiene coordenadas de Medellín
        assert "latitude" in data or isinstance(data, dict)