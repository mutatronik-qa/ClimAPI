# tests/test_data_processing.py
import pandas as pd
from processing.transform import process_weather_data, clean_and_standardize

def test_process_weather_data():
    # Datos de prueba simulando respuesta de API
    api_response = {
        'hourly': {
            'time': ['2024-01-01T00:00', '2024-01-01T01:00'],
            'temperature_2m': [25.0, 24.5],
            'relative_humidity_2m': [80, 85],
            'precipitation': [0.0, 0.5],
            'wind_speed_10m': [10.0, 12.0]
        }
    }
    
    df = process_weather_data(api_response)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert 'temperatura_c' in df.columns
    assert 'humedad_porcentaje' in df.columns