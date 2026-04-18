"""Data laboratory - independent module for data exploration and analysis."""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable
import json

import pandas as pd

from domain.entities.weather import WeatherData
from domain.interfaces.sources import WeatherDataSource, DataStorage

logger = logging.getLogger(__name__)


class DataLaboratory:
    """
    Independent data exploration module.
    
    Can be used in:
    - Jupyter notebooks
    - Scripts
    - API (optional)
    
    Features:
    - Load and explore historical data
    - Compare sources
    - Data quality metrics
    - Export to CSV
    """
    
    def __init__(
        self,
        storage: Optional[DataStorage] = None,
        data_dir: str = "data"
    ):
        self.storage = storage or DataStorage()
        self.data_dir = Path(data_dir)
        self.clean_dir = self.data_dir / "cleaned"
        self.raw_dir = self.data_dir / "raw"
    
    def load_cleaned_data(
        self,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Load cleaned weather data as DataFrame."""
        import asyncio
        
        async def _load():
            return await self.storage.load_cleaned(source, start_date, end_date)
        
        data = asyncio.run(_load())
        
        if not data:
            return pd.DataFrame()
        
        records = []
        for d in data:
            records.append({
                "timestamp": d.timestamp,
                "temperature": d.temperature,
                "humidity": d.humidity,
                "precipitation": d.precipitation,
                "wind_speed": d.wind_speed,
                "source": d.source
            })
        
        df = pd.DataFrame(records)
        
        if not df.empty and "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        
        return df
    
    def load_csv(self, filepath: str) -> pd.DataFrame:
        """Load data from CSV file."""
        df = pd.read_csv(filepath)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")
        
        return df
    
    def compare_sources(
        self,
        sources: list[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Compare data from different sources."""
        comparison = {}
        
        for source in sources:
            df = self.load_cleaned_data(source, start_date, end_date)
            
            if df.empty:
                comparison[source] = {"status": "no_data"}
                continue
            
            comparison[source] = {
                "records": len(df),
                "date_range": {
                    "start": df.index.min().isoformat() if not df.empty else None,
                    "end": df.index.max().isoformat() if not df.empty else None
                },
                "temperature": {
                    "mean": df["temperature"].mean() if "temperature" in df.columns else None,
                    "min": df["temperature"].min() if "temperature" in df.columns else None,
                    "max": df["temperature"].max() if "temperature" in df.columns else None
                },
                "humidity": {
                    "mean": df["humidity"].mean() if "humidity" in df.columns else None
                }
            }
        
        return comparison
    
    def get_quality_metrics(
        self,
        df: pd.DataFrame
    ) -> dict:
        """Calculate data quality metrics for a DataFrame."""
        if df.empty:
            return {"status": "no_data"}
        
        metrics = {
            "total_records": len(df),
            "date_range": {
                "start": df.index.min().isoformat(),
                "end": df.index.max().isoformat()
            },
            "completeness": {}
        }
        
        for col in ["temperature", "humidity", "precipitation", "wind_speed"]:
            if col in df.columns:
                non_null = df[col].notna().sum()
                metrics["completeness"][col] = {
                    "available": int(non_null),
                    "missing": int(len(df) - non_null),
                    "percent": round(non_null / len(df) * 100, 2)
                }
        
        # Overall quality score
        avg_completeness = sum(m["percent"] for m in metrics["completeness"].values()) / len(metrics["completeness"])
        
        if avg_completeness >= 90:
            metrics["overall_quality"] = "excellent"
        elif avg_completeness >= 75:
            metrics["overall_quality"] = "good"
        elif avg_completeness >= 50:
            metrics["overall_quality"] = "fair"
        else:
            metrics["overall_quality"] = "poor"
        
        return metrics
    
    def export_to_csv(
        self,
        df: pd.DataFrame,
        filename: str,
        include_index: bool = True
    ) -> str:
        """Export DataFrame to CSV."""
        output_path = self.data_dir / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_path, index=include_index)
        logger.info(f"Exported to {output_path}")
        
        return str(output_path)
    
    def list_available_datasets(self) -> list[dict]:
        """List all available datasets in the data directory."""
        datasets = []
        
        # Cleaned data
        if self.clean_dir.exists():
            for f in self.clean_dir.glob("*.csv"):
                datasets.append({
                    "type": "cleaned",
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 2)
                })
        
        # Raw data
        if self.raw_dir.exists():
            for f in self.raw_dir.glob("*.csv"):
                datasets.append({
                    "type": "raw",
                    "filename": f.name,
                    "path": str(f),
                    "size_kb": round(f.stat().st_size / 1024, 2)
                })
        
        return datasets
    
    def analyze_trends(
        self,
        df: pd.DataFrame,
        column: str,
        frequency: str = "D"
    ) -> pd.DataFrame:
        """Analyze trends in a specific column."""
        if df.empty or column not in df.columns:
            return pd.DataFrame()
        
        # Resample and calculate statistics
        resampled = df[column].resample(frequency).agg(["mean", "min", "max", "std"])
        
        return resampled
    
    def detect_outliers(
        self,
        df: pd.DataFrame,
        column: str,
        method: str = "iqr",
        threshold: float = 1.5
    ) -> pd.DataFrame:
        """Detect outliers in a column using IQR or Z-score method."""
        if df.empty or column not in df.columns:
            return pd.DataFrame()
        
        if method == "iqr":
            Q1 = df[column].quantile(0.25)
            Q3 = df[column].quantile(0.75)
            IQR = Q3 - Q1
            
            lower = Q1 - threshold * IQR
            upper = Q3 + threshold * IQR
            
            outliers = df[(df[column] < lower) | (df[column] > upper)]
        
        elif method == "zscore":
            from scipy import stats
            z_scores = stats.zscore(df[column].dropna())
            outliers = df[abs(z_scores) > threshold]
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return outliers
    
    def correlation_analysis(
        self,
        df: pd.DataFrame,
        columns: Optional[list[str]] = None
    ) -> pd.DataFrame:
        """Calculate correlation matrix between columns."""
        if columns is None:
            columns = ["temperature", "humidity", "precipitation", "wind_speed"]
        
        available_cols = [c for c in columns if c in df.columns]
        
        if not available_cols:
            return pd.DataFrame()
        
        return df[available_cols].corr()


# Factory function
def create_laboratory(data_dir: str = "data") -> DataLaboratory:
    """Create a DataLaboratory instance."""
    from infrastructure.adapters.storage.csv_storage import CSVStorageAdapter
    
    storage = CSVStorageAdapter(data_dir)
    return DataLaboratory(storage, data_dir)


# Convenience functions for notebook/script usage
def load_weather_data(
    source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> pd.DataFrame:
    """Quick load function for notebooks."""
    lab = create_l laboratory()
    
    start = pd.to_datetime(start_date) if start_date else None
    end = pd.to_datetime(end_date) if end_date else None
    
    return lab.load_cleaned_data(source, start, end)


def get_quality_report(df: pd.DataFrame) -> dict:
    """Quick quality report for notebooks."""
    lab = create_laboratory()
    return lab.get_quality_metrics(df)


def export_data(df: pd.DataFrame, filename: str) -> str:
    """Quick export function for notebooks."""
    lab = create_laboratory()
    return lab.export_to_csv(df, filename)