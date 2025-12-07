"""
Pruebas para el módulo de diagnóstico de datos.
"""
import pytest
import pandas as pd
import numpy as np
from processing.data_diagnostics import DataDiagnostics

class TestDataDiagnostics:
    """Pruebas para diagnóstico de DataFrames."""
    
    @pytest.fixture
    def sample_weather_df(self):
        """DataFrame de ejemplo con datos meteorológicos."""
        return pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=10, freq="H"),
            "temperature_2m": [20.5, 19.2, 18.1, 17.5, 16.8, 15.9, 15.2, 14.5, 13.8, 13.1],
            "humidity": [65, 70, 75, 80, 85, 88, 90, 88, 85, 80],
            "precipitation": [0.0, 0.0, 0.5, 1.2, 0.8, 0.3, 0.0, 0.0, 0.0, 0.0],
            "wind_speed": [10.0, 12.5, 15.0, 12.0, 8.5, 6.0, 5.0, 4.0, 3.0, 2.5]
        })
    
    def test_inspect_dataframe(self, sample_weather_df):
        """Prueba inspección de DataFrame."""
        inspection = DataDiagnostics.inspect_dataframe(sample_weather_df, "test_df")
        
        assert inspection["shape"] == (10, 5)
        assert inspection["is_empty"] == False
        assert len(inspection["columns"]) == 5
        assert inspection["name"] == "test_df"
    
    def test_find_datetime_columns(self, sample_weather_df):
        """Prueba detección de columnas datetime."""
        datetime_cols = DataDiagnostics.find_datetime_columns(sample_weather_df)
        
        assert "timestamp" in datetime_cols
        assert len(datetime_cols) >= 1
    
    def test_find_numeric_columns(self, sample_weather_df):
        """Prueba detección de columnas numéricas por categoría."""
        numeric_by_cat = DataDiagnostics.find_numeric_columns(sample_weather_df)
        
        assert "temperatura" in numeric_by_cat
        assert "humedad" in numeric_by_cat
        assert "precipitacion" in numeric_by_cat
        assert "viento" in numeric_by_cat
    
    def test_suggest_column_mapping(self, sample_weather_df):
        """Prueba sugerencia de mapeo de columnas."""
        mapping = DataDiagnostics.suggest_column_mapping(sample_weather_df)
        
        assert "timestamp" in mapping
        assert mapping["timestamp"] == "timestamp"
        # Debe mapear temperatura
        if "temperatura_c" in mapping:
            assert mapping["temperatura_c"] == "temperature_2m"
    
    def test_auto_normalize_columns(self, sample_weather_df):
        """Prueba normalización automática de columnas."""
        df_norm, mapping = DataDiagnostics.auto_normalize_columns(sample_weather_df)
        
        assert not df_norm.empty
        assert pd.api.types.is_datetime64_any_dtype(df_norm["timestamp"])
        assert len(mapping) > 0
    
    def test_validate_and_repair(self, sample_weather_df):
        """Prueba reparación automática."""
        # Añadir duplicados y valores faltantes
        df_broken = pd.concat([sample_weather_df, sample_weather_df.iloc[0:2]], ignore_index=True)
        df_broken.loc[0, "temperature_2m"] = np.nan
        
        df_repaired, actions = DataDiagnostics.validate_and_repair(df_broken)
        
        assert not df_repaired.empty
        assert len(actions) > 0
        # Verificar que se removieron duplicados
        assert df_repaired.duplicated().sum() == 0
    
    def test_empty_dataframe(self):
        """Prueba diagnóstico de DataFrame vacío."""
        df_empty = pd.DataFrame()
        inspection = DataDiagnostics.inspect_dataframe(df_empty)
        
        assert inspection["is_empty"] == True
        assert inspection["shape"] == (0, 0)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])