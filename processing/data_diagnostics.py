"""
Herramienta de diagnóstico para identificar y corregir problemas en DataFrames.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class DataDiagnostics:
    """Diagnóstico de problemas en DataFrames meteorológicos."""
    
    @staticmethod
    def inspect_dataframe(df: pd.DataFrame, name: str = "DataFrame") -> Dict:
        """
        Inspecciona un DataFrame y retorna información detallada.
        """
        inspection = {
            "name": name,
            "shape": df.shape,
            "is_empty": df.empty,
            "columns": list(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            "memory_usage": float(df.memory_usage(deep=True).sum()) / 1024**2,  # MB
            "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
            "duplicates": int(df.duplicated().sum()),
            "index_info": {
                "name": str(df.index.name),
                "dtype": str(df.index.dtype),
                "is_unique": bool(df.index.is_unique)
            }
        }
        
        # Muestra de datos
        if not df.empty:
            inspection["head"] = df.head(2).to_dict(orient='records')
        
        return inspection
    
    @staticmethod
    def find_datetime_columns(df: pd.DataFrame) -> List[str]:
        """Encuentra columnas que podrían ser datetime."""
        candidates = []
        
        # Buscar por nombre
        datetime_keywords = ["date", "time", "timestamp", "fecha", "hora"]
        by_name = [c for c in df.columns 
                   if any(kw in c.lower() for kw in datetime_keywords)]
        candidates.extend(by_name)
        
        # Buscar por tipo
        by_type = df.select_dtypes(include=['datetime64']).columns.tolist()
        candidates.extend(by_type)
        
        # Intentar parsear string columns
        object_cols = df.select_dtypes(include=['object']).columns
        for col in object_cols:
            if col in candidates:
                continue
            try:
                sample = df[col].dropna().head(5)
                if all(isinstance(x, str) for x in sample):
                    # Intentar parsear como datetime
                    pd.to_datetime(sample, errors='coerce')
                    if pd.to_datetime(sample, errors='coerce').notna().any():
                        candidates.append(col)
            except:
                pass
        
        return list(set(candidates))
    
    @staticmethod
    def find_numeric_columns(df: pd.DataFrame, 
                            weather_keywords: List[str] = None) -> Dict[str, List[str]]:
        """Encuentra columnas numéricas y las categoriza."""
        if weather_keywords is None:
            weather_keywords = {
                "temperatura": ["temp", "temperature", "t_"],
                "humedad": ["humid", "humidity", "rh"],
                "precipitacion": ["precip", "rain", "lluvia", "pp"],
                "viento": ["wind", "speed", "velocidad", "viento"],
                "presion": ["pressure", "presion", "press", "pres"],
                "nube": ["cloud", "cloudcover", "nube", "nubosidad"],
                "rocio": ["dew", "rocio"],
                "visibilidad": ["visib", "visibility"],
                "radiacion": ["radiation", "radiacion", "solar"],
                "uv": ["uv", "index"]
            }
        
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        categorized = {}
        for category, keywords in weather_keywords.items():
            matches = [c for c in numeric_cols 
                      if any(kw in c.lower() for kw in keywords)]
            if matches:
                categorized[category] = matches
        
        # Columnas no categorizadas
        uncategorized = [c for c in numeric_cols 
                        if not any(c in v for v in categorized.values())]
        if uncategorized:
            categorized["other"] = uncategorized
        
        return categorized
    
    @staticmethod
    def suggest_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
        """
        Sugiere mapeo de columnas encontradas a esquema normalizado.
        """
        mapping = {}
        
        # Buscar datetime
        datetime_cols = DataDiagnostics.find_datetime_columns(df)
        if datetime_cols:
            mapping["timestamp"] = datetime_cols[0]
        
        # Buscar categorías numéricas
        numeric_by_cat = DataDiagnostics.find_numeric_columns(df)
        
        # Mapeos esperados
        expected_mappings = {
            "temperatura_c": "temperatura",
            "humedad_porcentaje": "humedad",
            "precipitacion_mm": "precipitacion",
            "velocidad_viento_kmh": "viento",
            "presion_hpa": "presion",
            "nubosidad_porcentaje": "nube",
            "punto_rocio_c": "rocio",
            "visibilidad_m": "visibilidad",
            "radiacion_solar_wm2": "radiacion",
            "indice_uv": "uv"
        }
        
        for std_col, category in expected_mappings.items():
            if category in numeric_by_cat:
                candidates = numeric_by_cat[category]
                if candidates:
                    mapping[std_col] = candidates[0]
        
        return mapping
    
    @staticmethod
    def auto_normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Intenta normalizar automáticamente las columnas de un DataFrame.
        
        Returns:
            (DataFrame normalizado, mapping usado)
        """
        if df.empty:
            return df, {}
        
        mapping = DataDiagnostics.suggest_column_mapping(df)
        
        if not mapping:
            logger.warning("No se pudo sugerir mapeo de columnas")
            return df, {}
        
        # Aplicar renombramiento
        df_normalized = df.copy()
        
        # Renombrar columnas
        reverse_mapping = {v: k for k, v in mapping.items()}
        df_normalized = df_normalized.rename(columns=reverse_mapping)
        
        # Convertir timestamp a datetime
        if "timestamp" in df_normalized.columns:
            try:
                df_normalized["timestamp"] = pd.to_datetime(
                    df_normalized["timestamp"], 
                    utc=True, 
                    errors='coerce'
                )
            except Exception as e:
                logger.warning(f"No se pudo convertir timestamp: {e}")
        
        # Convertir columnas numéricas
        numeric_cols = df_normalized.select_dtypes(include=['object']).columns
        for col in numeric_cols:
            if col != "source" and col != "city" and col != "country":
                try:
                    df_normalized[col] = pd.to_numeric(
                        df_normalized[col], 
                        errors='coerce'
                    )
                except:
                    pass
        
        return df_normalized, mapping
    
    @staticmethod
    def validate_and_repair(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Valida y repara un DataFrame automáticamente.
        
        Returns:
            (DataFrame reparado, lista de acciones realizadas)
        """
        actions = []
        df_repaired = df.copy()
        
        # 1. Remover duplicados
        initial_len = len(df_repaired)
        df_repaired = df_repaired.drop_duplicates()
        if len(df_repaired) < initial_len:
            actions.append(f"Removidos {initial_len - len(df_repaired)} duplicados")
        
        # 2. Normalizar columnas
        df_repaired, mapping = DataDiagnostics.auto_normalize_columns(df_repaired)
        if mapping:
            actions.append(f"Columnas normalizadas: {mapping}")
        
        # 3. Llenar valores faltantes si es posible
        if "timestamp" in df_repaired.columns:
            df_repaired = df_repaired.sort_values("timestamp")
            actions.append("Datos ordenados por timestamp")
        
        # 4. Validar que timestamp sea datetime
        if "timestamp" in df_repaired.columns:
            if not pd.api.types.is_datetime64_any_dtype(df_repaired["timestamp"]):
                try:
                    df_repaired["timestamp"] = pd.to_datetime(
                        df_repaired["timestamp"], 
                        utc=True
                    )
                    actions.append("timestamp convertido a datetime")
                except Exception as e:
                    logger.error(f"No se pudo convertir timestamp: {e}")
        
        return df_repaired, actions
    
    @staticmethod
    def print_diagnosis(df: pd.DataFrame, name: str = "DataFrame"):
        """Imprime diagnóstico completo."""
        inspection = DataDiagnostics.inspect_dataframe(df, name)
        
        print(f"\n{'='*60}")
        print(f"📊 DIAGNÓSTICO: {inspection['name']}")
        print(f"{'='*60}")
        print(f"Forma: {inspection['shape']}")
        print(f"Vacío: {inspection['is_empty']}")
        print(f"Memoria: {inspection['memory_usage']:.2f} MB")
        
        print(f"\n📋 Columnas ({len(inspection['columns'])}):")
        for col in inspection['columns']:
            missing = inspection['missing_values'][col]
            dtype = inspection['dtypes'][col]
            status = "✓" if missing == 0 else f"⚠️  ({missing} faltantes)"
            print(f"  • {col}: {dtype} {status}")
        
        print(f"\n🔍 Análisis:")
        print(f"  • Índice único: {inspection['index_info']['is_unique']}")
        print(f"  • Duplicados: {inspection['duplicates']}")
        
        datetime_cols = DataDiagnostics.find_datetime_columns(df)
        if datetime_cols:
            print(f"  • Columnas datetime detectadas: {datetime_cols}")
        
        numeric_by_cat = DataDiagnostics.find_numeric_columns(df)
        if numeric_by_cat:
            print(f"  • Columnas numéricas por categoría:")
            for cat, cols in numeric_by_cat.items():
                print(f"    - {cat}: {cols}")
        
        suggested_mapping = DataDiagnostics.suggest_column_mapping(df)
        if suggested_mapping:
            print(f"\n💡 Mapeo sugerido:")
            for std_col, found_col in suggested_mapping.items():
                print(f"  • {std_col} <- {found_col}")
        
        print(f"{'='*60}\n")