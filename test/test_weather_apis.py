# tests/test_weather_apis.py
import pytest
from unittest.mock import patch, MagicMock
from data_sources.open_meteo import get_weather_data, validate_coordinates
import sys
from pathlib import Path

# Agrega el directorio raíz del proyecto al sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
def test_validate_coordinates():
    # Coordenadas válidas
    assert validate_coordinates(6.244, -75.581) is True
    
    # Coordenadas inválidas
    with pytest.raises(ValueError):
        validate_coordinates(-91.0, 0.0)  # Latitud fuera de rango
    with pytest.raises(ValueError):
        validate_coordinates(0.0, 181.0)  # Longitud fuera de rango

@patch('data_sources.open_meteo.requests.get')
def test_get_weather_data_success(mock_get):
    # Mock de respuesta exitosa
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'hourly': {'time': ['2024-01-01T00:00'], 'temperature_2m': [25.0]}
    }
    mock_get.return_value = mock_response
    
    data = get_weather_data(6.244, -75.581, 'America/Bogota')
    assert 'hourly' in data