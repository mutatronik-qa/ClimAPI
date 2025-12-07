"""
Tests unitarios para módulo de API de clima
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Agregar ruta del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.open_meteo import (
    validate_coordinates, 
    get_weather_data
)

class TestValidateCoordinates(unittest.TestCase):
    """Tests para validación de coordenadas"""
    
    def test_valid_coordinates(self):
        """Coordenadas válidas deben pasar"""
        lat, lon = validate_coordinates(40.7128, -74.0060)  # Nueva York
        self.assertEqual(lat, 40.7128)
        self.assertEqual(lon, -74.0060)
    
    def test_invalid_latitude_too_high(self):
        """Latitud > 90 debe fallar"""
        with self.assertRaises(ValueError):
            validate_coordinates(91, 0)
    
    def test_invalid_latitude_too_low(self):
        """Latitud < -90 debe fallar"""
        with self.assertRaises(ValueError):
            validate_coordinates(-91, 0)
    
    def test_invalid_longitude_too_high(self):
        """Longitud > 180 debe fallar"""
        with self.assertRaises(ValueError):
            validate_coordinates(0, 181)
    
    def test_invalid_longitude_too_low(self):
        """Longitud < -180 debe fallar"""
        with self.assertRaises(ValueError):
            validate_coordinates(0, -181)
    
    def test_boundary_values(self):
        """Valores límite deben ser válidos"""
        validate_coordinates(90, 180)  # Debe pasar
        validate_coordinates(-90, -180)  # Debe pasar

class TestGetWeatherData(unittest.TestCase):
    """Tests para obtención de datos meteorológicos"""
    
    @patch('requests.get')
    def test_successful_request(self, mock_get):
        """Request exitoso retorna datos"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "generationtime_ms": 10.5,
            "utc_offset_seconds": -18000,
            "timezone": "America/New_York",
            "hourly": {
                "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
                "temperature_2m": [5.2, 4.8],
                "relative_humidity_2m": [65, 70],
                "precipitation": [0, 0.1],
                "weather_code": [0, 1],
                "wind_speed_10m": [10, 12],
                "visibility": [10000, 9500]
            }
        }
        mock_get.return_value = mock_response
        
        result = get_weather_data(40.7128, -74.0060)
        
        self.assertEqual(result["latitude"], 40.7128)
        self.assertIn("hourly", result)

if __name__ == '__main__':
    unittest.main()