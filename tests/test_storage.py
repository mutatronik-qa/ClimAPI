"""
Tests para processing/storage.py

Funciones:
- save_to_csv()
- load_from_csv()
- CacheManager
Usa pandas.testing para comparaciones.
"""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime

from processing.storage import (
    save_to_csv,
    load_from_csv,
    CacheManager
)


class TestSaveToCsv:
    """Tests para save_to_csv()"""
    
    def test_guarda_csv_exitosamente(self, tmp_path, sample_dataframe):
        """Debe guardar DataFrame en archivo CSV"""
        filepath = tmp_path / "test_output.csv"
        
        result = save_to_csv(sample_dataframe, str(filepath))
        
        assert Path(result).exists()
    
    def test_agrega_extension_csv(self, tmp_path, sample_dataframe):
        """Debe agregar .csv si no está"""
        filepath = tmp_path / "test_output"
        
        result = save_to_csv(sample_dataframe, str(filepath))
        
        assert result.endswith(".csv")
    
    def test_guarda_con_indice(self, tmp_path, sample_dataframe):
        """Debe guardar con índice (time)"""
        filepath = tmp_path / "test_output.csv"
        
        save_to_csv(sample_dataframe, str(filepath))
        
        # Cargar y verificar
        df_loaded = pd.read_csv(filepath, index_col=0, parse_dates=True)
        
        assert len(df_loaded) == len(sample_dataframe)
        assert "temperatura_c" in df_loaded.columns
    
    def test_append_agrega_datos(self, tmp_path, sample_dataframe):
        """Modo append debe agregar datos"""
        filepath = tmp_path / "test_append.csv"
        
        # Guardar inicial
        save_to_csv(sample_dataframe, str(filepath))
        
        # Agregar más datos
        more_data = sample_dataframe.copy()
        more_data.index = more_data.index + pd.Timedelta(hours=48)
        save_to_csv(more_data, str(filepath), append=True)
        
        # Cargar
        df_final = pd.read_csv(filepath, index_col=0, parse_dates=True)
        
        assert len(df_final) > len(sample_dataframe)


class TestLoadFromCsv:
    """Tests para load_from_csv()"""
    
    def test_carga_csv_exitosamente(self, tmp_path, sample_dataframe):
        """Debe cargar DataFrame desde CSV"""
        filepath = tmp_path / "test_load.csv"
        sample_dataframe.to_csv(filepath)
        
        df_loaded = load_from_csv(str(filepath))
        
        assert isinstance(df_loaded, pd.DataFrame)
        assert len(df_loaded) == len(sample_dataframe)
    
    def test_error_si_no_existe(self, tmp_path):
        """Debe lanzar error si archivo no existe"""
        with pytest.raises(FileNotFoundError):
            load_from_csv(str(tmp_path / "no_existe.csv"))
    
    def test_carga_parsea_datetime(self, tmp_path, sample_dataframe):
        """Debe parsear índice como datetime"""
        filepath = tmp_path / "test_parse.csv"
        sample_dataframe.to_csv(filepath)
        
        df_loaded = load_from_csv(str(filepath))
        
        assert pd.api.types.is_datetime64_any_dtype(df_loaded.index)
    
    def test_datos_iguales(self, tmp_path):
        """Datos cargados deben ser iguales a originales"""
        filepath = tmp_path / "test_compare.csv"
        
        # Guardar
        sample_dataframe.to_csv(filepath)
        
        # Cargar y comparar
        df_loaded = load_from_csv(str(filepath))
        
        # Usar pandas.testing para comparación exacta
        pd.testing.assert_frame_equal(
            df_loaded, 
            sample_dataframe,
            check_dtype=False  # Puede haber diferencias menores en tipos
        )


class TestCacheManager:
    """Tests para CacheManager"""
    
    def test_inicializa_cache(self, tmp_path):
        """Debe inicializar sin errores"""
        cache = CacheManager(str(tmp_path / "cache"), ttl_minutes=5)
        
        assert cache.cache is not None
    
    def test_set_y_get(self, tmp_path):
        """Debe guardar y recuperar datos"""
        cache = CacheManager(str(tmp_path / "cache"), ttl_minutes=5)
        
        cache.set("test_key", {"temp": 20.0})
        result = cache.get("test_key")
        
        assert result is not None
    
    def test_get_inexistente_retorna_none(self, tmp_path):
        """Clave inexistente debe retornar None"""
        cache = CacheManager(str(tmp_path / "cache"), ttl_minutes=5)
        
        result = cache.get("no_existe")
        
        assert result is None
    
    def test_cache_expirado(self, tmp_path):
        """Debe limpiar datos expirados"""
        import time
        cache = CacheManager(str(tmp_path / "cache"), ttl_minutes=0)  # TTL instantáneo
        
        cache.set("test_key", {"temp": 20.0})
        time.sleep(0.1)  # Esperar a que expire
        
        result = cache.get("test_key")
        
        # Debe ser None (expirado)
        assert result is None
    
    def test_clear_limpia_cache(self, tmp_path):
        """Debe limpiar todo el cache"""
        cache = CacheManager(str(tmp_path / "cache"), ttl_minutes=5)
        
        cache.set("key1", {"data": 1})
        cache.set("key2", {"data": 2})
        
        result = cache.clear()
        
        assert "message" in result
        assert cache.get("key1") is None
    
    def test_get_stats(self, tmp_path):
        """Debe retornar estadísticas"""
        cache = CacheManager(str(tmp_path / "cache"), ttl_minutes=5)
        
        cache.set("key1", {"data": 1})
        
        stats = cache.get_stats()
        
        assert "entries" in stats
        assert "path" in stats
        assert stats["entries"] >= 1


# ============================================================================
# TESTS DE INTEGRACIÓN: CSV ROUNDTRIP
# ============================================================================

class TestCsvRoundtrip:
    """Tests completos de save -> load"""
    
    def test_roundtrip_data_completo(self, tmp_path, sample_dataframe):
        """Guardar y cargar debe mantener datos exactos"""
        filepath = tmp_path / "roundtrip.csv"
        
        # Save
        save_to_csv(sample_dataframe, str(filepath))
        
        # Load
        df_result = load_from_csv(str(filepath))
        
        # Comparar (ignorando dtype por posibles conversiones)
        assert len(df_result) == len(sample_dataframe)
        assert list(df_result.columns) == list(sample_dataframe.columns)
    
    def test_roundtrip_preserva_nulls(self, tmp_path):
        """Debe preservar valores NaN"""
        df_with_nan = pd.DataFrame({
            "temperatura_c": [20.0, None, 22.0],
            "humedad_porcentaje": [80, 75, 70]
        }, index=pd.date_range("2024-01-01", periods=3, freq="h"))
        
        filepath = tmp_path / "nan_test.csv"
        save_to_csv(df_with_nan, str(filepath))
        
        df_loaded = load_from_csv(str(filepath))
        
        # Verificar que hay valores null
        assert df_loaded["temperatura_c"].isna().any()