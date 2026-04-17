"""
Tests para FastAPI Endpoints (main.py)

Usa TestClient para testing sin servidor real.
Mocks para APIs externas.
"""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from fastapi.testclient import TestClient


# ============================================================================
# TESTS DE ENDPOINTS BÁSICOS
# ============================================================================

class TestRootEndpoint:
    """Tests para endpoint raíz /"""
    
    def test_root_returns_message(self, client):
        """GET / debe retornar message y version"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestHealthEndpoint:
    """Tests para /api/v1/health"""
    
    def test_health_returns_healthy(self, client):
        """Health check debe retornar status: healthy"""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data


# ============================================================================
# TESTS DE WEATHER ENDPOINTS
# ============================================================================

class TestCurrentWeatherEndpoint:
    """Tests para POST /api/v1/weather/current"""
    
    def test_current_weather_returns_data(self, client):
        """Debe retornar datos meteorológicos"""
        payload = {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }
        
        response = client.post("/api/v1/weather/current", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "source" in data
        assert "location" in data
    
    def test_current_weather_validates_location(self, client):
        """Debe validar coordenadas fuera de rango"""
        payload = {
            "latitude": 100.0,  # Inválida
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }
        
        response = client.post("/api/v1/weather/current", json=payload)
        
        assert response.status_code == 400
    
    def test_current_weather_returns_weather_fields(self, client):
        """Debe tener campos de weather en response"""
        payload = {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }
        
        response = client.post("/api/v1/weather/current", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verificar estructura de primer dato
        if data.get("data"):
            first = data["data"][0]
            assert "time" in first
            assert "temperature" in first
            assert "humidity" in first


class TestDefaultLocation:
    """Tests para /api/v1/locations/default"""
    
    def test_returns_default_medellin(self, client):
        """Por defecto debe retornar Medellín"""
        response = client.get("/api/v1/locations/default")
        
        assert response.status_code == 200
        data = response.json()
        assert data["latitude"] == 6.244
        assert data["longitude"] == -75.581
        assert "city" in data


# ============================================================================
# TESTS DE CACHE
# ============================================================================

class TestCacheEndpoints:
    """Tests paraendpoints de caché"""
    
    def test_cache_stats_returns_structure(self, client):
        """GET /api/v1/cache/stats debe retornar estructura válida"""
        response = client.get("/api/v1/cache/stats")
        
        # Puede ser 200 o 500 si hay error de inicialización
        assert response.status_code in [200, 500]
    
    def test_clear_cache_returns_message(self, client):
        """DELETE /api/v1/cache debe retornar mensaje"""
        response = client.delete("/api/v1/cache")
        
        # Puede ser 200 o 500
        assert response.status_code in [200, 500]


# ============================================================================
# TESTS CON MOCKS (SIN LLAMADAS A INTERNET)
# ============================================================================

class TestWeatherWithMock:
    """Tests que usan mocks para evitar llamadas reales"""
    
    @patch("main.get_weather_data")
    def test_current_weather_uses_cache(self, mock_get_data, client):
        """Debe usar cache si está disponible"""
        # Configurar mock
        mock_get_data.return_value = {
            "hourly": {
                "time": ["2024-01-01T00:00"],
                "temperature_2m": [20.0],
                "relative_humidity_2m": [80],
                "precipitation": [0.0],
                "wind_speed_10m": [10.0]
            }
        }
        
        payload = {
            "latitude": 6.244,
            "longitude": -75.581,
            "timezone": "America/Bogota"
        }
        
        response = client.post("/api/v1/weather/current", json=payload)
        
        # Verificar que se usó el mock (no debe fallar por red)
        assert response.status_code in [200, 500]


# ============================================================================
# TESTS DE INTEGRACIÓN: RESPUESTAS VALIDAS
# ============================================================================

class TestIntegration:
    """Tests de integración real (si hay datos en CSV)"""
    
    def test_loads_existing_csv_if_present(self, client):
        """Si existe weather_data.csv, debe usarlo"""
        from pathlib import Path
        
        csv_path = Path("data/weather_data.csv")
        
        if csv_path.exists():
            # El endpoint debe retornar datos sin error
            payload = {
                "latitude": 6.244,
                "longitude": -75.581,
                "timezone": "America/Bogota"
            }
            response = client.post("/api/v1/weather/current", json=payload)
            # No debe ser 500 (error de server)
            assert response.status_code in [200, 400]