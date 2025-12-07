"""
Tests unitarios para módulo de procesamiento
"""

import unittest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from processing.transform import process_weather_data, calculate_statistics

class TestProcessWeatherData(unittest.TestCase):
    """Tests para procesamiento de datos"""
    
    def setUp(self):
        """Preparar datos de prueba"""
        self.sample_response = {
            "latitude": 6.244,
            "longitude": -75.581,
            "generationtime_ms": 10,
            "utc_offset_seconds": -18000,
            "timezone": "America/Bogota",
            "hourly": {
                "time": [
                    "2024-01-01T00:00",
                    "2024-01-01T01:00",
                    "2024-01-01T02:00"
                ],
                "temperature_2m": [20.0, 19.5, 21.0],
                "relative_humidity_2m": [65, 70, 60],
                "precipitation": [0, 0.5, 1.0],
                "weather_code": [0, 1, 61],
                "wind_speed_10m": [10, 12, 11],
                "visibility": [10000, 9500, 8000]
            }
        }
    
    def test_process_weather_data(self):
        """Debe procesar datos correctamente"""
        df = process_weather_data(self.sample_response)
        
        self.assertEqual(len(df), 3)
        self.assertIn("temperatura_c", df.columns)
        self.assertIn("humedad_porcentaje", df.columns)
        self.assertIn("descripcion_clima", df.columns)
    
    def test_calculate_statistics(self):
        """Debe calcular estadísticas"""
        df = process_weather_data(self.sample_response)
        stats = calculate_statistics(df)
        
        self.assertIn("temp_promedio", stats)
        self.assertIn("temp_maxima", stats)
        self.assertAlmostEqual(stats["temp_maxima"], 21.0)

if __name__ == '__main__':
    unittest.main()