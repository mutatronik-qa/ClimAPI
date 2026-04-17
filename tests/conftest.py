"""
Fixtures reutilizables para ClimAPI Tests.

Provee:
- Mocks de APIs externas
- DataFrames de ejemplo
- Configuración de test
- Clientes autenticados
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient


# ============================================================================
# FIXTURES DE DATOS METEREOLÓGICOS
# ============================================================================

@pytest.fixture
def sample_api_response():
    """
    Respuesta simulada de Open-Meteo API (formato real).
    """
    base_time = datetime(2024, 1, 1, 0, 0)
    times = [(base_time + timedelta(hours=i)).isoformat() for i in range(48)]
    
    return {
        "latitude": 6.244,
        "longitude": -75.581,
        "generationtime_ms": 50.0,
        "utc_offset_seconds": -18000,
        "timezone": "America/Bogota",
        "hourly": {
            "time": times,
            "temperature_2m": [20.0 + i * 0.1 for i in range(48)],
            "relative_humidity_2m": [70 + i % 10 for i in range(48)],
            "precipitation": [0.0 if i % 4 != 0 else 0.5 for i in range(48)],
            "weather_code": [0 if i % 4 != 0 else 1 for i in range(48)],
            "wind_speed_10m": [10.0 + i * 0.05 for i in range(48)],
            "visibility": [10000 for _ in range(48)]
        }
    }


@pytest.fixture
def sample_dataframe():
    """
    DataFrame de weather data ya procesado.
    """
    base_time = datetime(2024, 1, 1, 0, 0)
    index = [base_time + timedelta(hours=i) for i in range(48)]
    
    return pd.DataFrame({
        "temperatura_c": [20.0 + i * 0.1 for i in range(48)],
        "humedad_porcentaje": [70 + i % 10 for i in range(48)],
        "precipitacion_mm": [0.0 if i % 4 != 0 else 0.5 for i in range(48)],
        "velocidad_viento_kmh": [10.0 + i * 0.05 for i in range(48)]
    }, index=index)


@pytest.fixture
def sample_dataframe_with_nulls():
    """
    DataFrame con valores nulos para testing de limpieza.
    """
    base_time = datetime(2024, 1, 1, 0, 0)
    index = [base_time + timedelta(hours=i) for i in range(10)]
    
    # Incluir algunos None/NaN
    temps = [20.0, 21.0, None, 22.0, 21.5, None, 23.0, 22.5, 21.0, 20.5]
    
    return pd.DataFrame({
        "temperatura_c": temps,
        "humedad_porcentaje": [80, 75, 70, 65, 70, None, 75, 80, 85, 90],
        "precipitacion_mm": [0.0, 0.5, 0.0, 0.0, 1.0, 0.0, 0.5, 0.0, 0.0, 0.0],
        "velocidad_viento_kmh": [10.0, 12.0, 11.0, 8.0, 9.0, 10.5, 11.0, 9.5, 8.0, 7.5]
    }, index=index)


@pytest.fixture
def sample_csv_content():
    """
    Contenido CSV de weather data (para testing de parsing).
    """
    return """time,temperatura_c,humedad_porcentaje,precipitacion_mm,velocidad_viento_kmh
2024-01-01 00:00:00,20.0,80,0.0,10.0
2024-01-01 01:00:00,20.5,78,0.0,10.5
2024-01-01 02:00:00,21.0,75,0.0,11.0"""


# ============================================================================
# FIXTURES DE INPUTS VLidos
# ============================================================================

@pytest.fixture
def valid_location():
    """Ubicación válida: Medellín"""
    return {"latitude": 6.244, "longitude": -75.581, "timezone": "America/Bogota"}


@pytest.fixture
def valid_city_request():
    """Request de ciudad para geocoding"""
    return {"city": "Medellin", "timezone": "America/Bogota"}


# ============================================================================
# FIXTURES DE CLIENTES Y APPS
# ============================================================================

@pytest.fixture
def mock_requests_get():
    """
    Mock de requests.get para evitar llamadas reales a internet.
    Usa response.json() para retornar sample_api_response.
    """
    with patch("requests.get") as mock:
        mock.return_value = Mock(status_code=200)
        mock.return_value.json.return_value = {
            "latitude": 6.244,
            "longitude": -75.581,
            "hourly": {
                "time": ["2024-01-01T00:00"],
                "temperature_2m": [20.0],
                "relative_humidity_2m": [80],
                "precipitation": [0.0],
                "weather_code": [0],
                "wind_speed_10m": [10.0]
            }
        }
        mock.return_value.raise_for_status = Mock()
        yield mock


@pytest.fixture
def client(tmp_path, monkeypatch):
    """
    Crea TestClient de FastAPI con mocks.
    Evita imports problemáticos.
    """
    import sys
    from pathlib import Path
    
    # Mockear módulos que pueden fallar
    monkeypatch.setenv("CACHE_TTL_MINUTES", "1")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    
    # Importar después de configurar mocks
    from main import app
    return TestClient(app)


@pytest.fixture
def client_no_cache():
    """
    TestClient sin caché para testing aislados.
    """
    from main import app
    return TestClient(app)


# ============================================================================
# FIXTURES DE ASSERTIONS HELPERS
# ============================================================================

def assert_dataframe_schema(df: pd.DataFrame):
    """Verifica schema esperado del DataFrame."""
    expected_cols = ["temperatura_c", "humedad_porcentaje", "precipitacion_mm", "velocidad_viento_kmh"]
    for col in expected_cols:
        assert col in df.columns, f"Columna faltante: {col}"


def assert_api_response_valid(response_data: dict, has_data: bool = True):
    """Verifica estructura de respuesta de API."""
    if has_data:
        assert "data" in response_data or "location" in response_data
    # No debe tener errores
    assert "error" not in response_data


# ============================================================================
# FIXTURES DE LIMPIEZA
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_cache(tmp_path):
    """Limpia cache después de cada test."""
    yield
    cache_dir = tmp_path / "cache"
    if cache_dir.exists():
        for f in cache_dir.glob("*"):
            f.unlink()