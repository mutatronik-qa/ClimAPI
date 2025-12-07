"""
Generador de reportes de calidad de datos.
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from datetime import datetime
import json

class DataQualityReport:
    """Genera reportes de calidad de datos meteorológicos."""
    
    @staticmethod
    def generate(df: pd.DataFrame, source: str = "unknown") -> Dict:
        """
        Genera un reporte completo de calidad de datos.
        
        Returns:
            Dict con métricas de calidad
        """
        if df.empty:
            return {
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "status": "error",
                "message": "DataFrame vacío",
                "total_records": 0,
                "summary": {
                    "overall_quality": "Unknown",
                    "missing_data_percent": 0.0
                }
            }
        
        report = {
            "source": source,
            "timestamp": datetime.now().isoformat(),
            "total_records": len(df),
            "date_range": {
                "start": str(df["timestamp"].min()) if "timestamp" in df.columns else None,
                "end": str(df["timestamp"].max()) if "timestamp" in df.columns else None,
            },
            "completeness": {},
            "validity": {},
            "consistency": {},
            "summary": {}
        }
        
        # Análisis de completitud
        total_cells = len(df) * len(df.columns)
        total_missing = 0
        
        for col in df.columns:
            total = len(df)
            missing = df[col].isna().sum()
            completeness = ((total - missing) / total * 100) if total > 0 else 0
            total_missing += missing
            report["completeness"][col] = {
                "missing_count": int(missing),
                "completeness_percent": round(completeness, 2)
            }
        
        # Análisis de validez (rangos realistas)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            values = df[col].dropna()
            if len(values) > 0:
                report["validity"][col] = {
                    "min": round(float(values.min()), 2),
                    "max": round(float(values.max()), 2),
                    "mean": round(float(values.mean()), 2),
                    "std": round(float(values.std()), 2),
                    "outliers_count": int((np.abs(values - values.mean()) > 3 * values.std()).sum())
                }
        
        # Consistencia temporal
        if "timestamp" in df.columns:
            try:
                df_sorted = df.sort_values("timestamp")
                time_diffs = df_sorted["timestamp"].diff().dropna()
                if len(time_diffs) > 0:
                    report["consistency"]["temporal"] = {
                        "mode_frequency": str(time_diffs.mode()[0]) if len(time_diffs.mode()) > 0 else None,
                        "irregular_gaps": int((time_diffs > time_diffs.quantile(0.95)).sum()),
                        "total_gaps": len(time_diffs)
                    }
            except Exception as e:
                logger.warning(f"Error en análisis temporal: {e}")
        
        # Resumen general
        missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0
        report["summary"]["overall_quality"] = "Good" if missing_pct < 5 else "Fair" if missing_pct < 15 else "Poor"
        report["summary"]["missing_data_percent"] = round(missing_pct, 2)
        
        return report
    
    @staticmethod
    def compare_sources(dataframes: Dict[str, pd.DataFrame]) -> Dict:
        """
        Compara calidad entre múltiples fuentes.
        
        Args:
            dataframes: {source_name -> DataFrame}
        
        Returns:
            Análisis comparativo
        """
        comparison = {
            "timestamp": datetime.now().isoformat(),
            "sources": {}
        }
        
        for source, df in dataframes.items():
            comparison["sources"][source] = DataQualityReport.generate(df, source)
        
        # Agregar comparación
        if comparison["sources"]:
            completeness_by_source = {
                src: sum(
                    rep["completeness"][col]["completeness_percent"] 
                    for col in rep["completeness"]
                ) / len(rep["completeness"])
                for src, rep in comparison["sources"].items()
            }
            comparison["best_source"] = max(completeness_by_source, key=completeness_by_source.get)
        
        return comparison
    
    @staticmethod
    def to_json(report: Dict) -> str:
        """Convierte reporte a JSON."""
        return json.dumps(report, indent=2, default=str)
    
    @staticmethod
    def to_markdown(report: Dict) -> str:
        """Convierte reporte a Markdown."""
        md = f"# Reporte de Calidad de Datos\n\n"
        md += f"**Fuente:** {report.get('source', 'unknown')}\n"
        md += f"**Generado:** {report.get('timestamp', 'N/A')}\n\n"
        
        md += f"## Resumen\n"
        md += f"- **Total de registros:** {report.get('total_records', 0)}\n"
        md += f"- **Calidad general:** {report['summary'].get('overall_quality', 'N/A')}\n"
        md += f"- **Datos faltantes:** {report['summary'].get('missing_data_percent', 0)}%\n\n"
        
        md += f"## Completitud por columna\n"
        for col, metrics in report.get("completeness", {}).items():
            md += f"- **{col}:** {metrics['completeness_percent']}% ({metrics['missing_count']} faltantes)\n"
        
        md += f"\n## Estadísticas de Validez\n"
        for col, metrics in report.get("validity", {}).items():
            md += f"- **{col}:** Min={metrics['min']}, Max={metrics['max']}, Media={metrics['mean']}\n"
        
        return md