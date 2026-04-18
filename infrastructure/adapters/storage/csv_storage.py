"""Data storage adapter implementation."""
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import json

import pandas as pd

from domain.entities.weather import WeatherData
from domain.interfaces.sources import DataStorage

logger = logging.getLogger(__name__)


class CSVStorageAdapter(DataStorage):
    """
    CSV-based data storage adapter.
    
    Stores raw and cleaned data as CSV files.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.clean_dir = self.data_dir / "cleaned"
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.clean_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_raw(self, data: dict, source: str, timestamp: datetime) -> str:
        """Save raw data to CSV."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{timestamp_str}.csv"
        filepath = self.raw_dir / filename
        
        df = pd.DataFrame([data])
        df.to_csv(filepath, index=False)
        
        logger.info(f"Saved raw data to {filepath}")
        return str(filepath)
    
    async def save_cleaned(self, data: list[WeatherData]) -> str:
        """Save cleaned data to CSV."""
        if not data:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weather_cleaned_{timestamp}.csv"
        filepath = self.clean_dir / filename
        
        records = [d.model_dump(mode='json') for d in data]
        df = pd.DataFrame(records)
        
        # Convert timestamp to string for CSV
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        df.to_csv(filepath, index=False)
        
        logger.info(f"Saved cleaned data to {filepath}: {len(data)} records")
        return str(filepath)
    
    async def load_cleaned(
        self,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[WeatherData]:
        """Load cleaned data with optional filters."""
        pattern = f"{self.clean_dir}/*.csv"
        
        if source:
            pattern = f"{self.clean_dir}/{source}_*.csv"
        
        files = list(Path(pattern).glob("*.csv"))
        
        if not files:
            return []
        
        # Load and concatenate all files
        dfs = []
        for f in files:
            try:
                df = pd.read_csv(f)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Error loading {f}: {e}")
        
        if not dfs:
            return []
        
        combined = pd.concat(dfs, ignore_index=True)
        
        # Apply date filters
        if start_date:
            combined = combined[combined['timestamp'] >= start_date]
        if end_date:
            combined = combined[combined['timestamp'] <= end_date]
        
        # Convert to WeatherData objects
        return [WeatherData(**row) for row in combined.to_dict('records')]
    
    async def list_available_data(self) -> list[dict]:
        """List available data files."""
        result = []
        
        # Raw data
        for f in self.raw_dir.glob("*.csv"):
            result.append({
                "type": "raw",
                "source": f.stem.split("_")[0],
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        # Cleaned data
        for f in self.clean_dir.glob("*.csv"):
            result.append({
                "type": "cleaned",
                "source": "combined",
                "path": str(f),
                "size_bytes": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        return result


class ParquetStorageAdapter(DataStorage):
    """
    Parquet-based data storage for better performance.
    
    Good for large datasets and analytical queries.
    """
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw_parquet"
        self.clean_dir = self.data_dir / "cleaned_parquet"
        
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.clean_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_raw(self, data: dict, source: str, timestamp: datetime) -> str:
        """Save raw data to Parquet."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{timestamp_str}.parquet"
        filepath = self.raw_dir / filename
        
        df = pd.DataFrame([data])
        df.to_parquet(filepath, index=False)
        
        return str(filepath)
    
    async def save_cleaned(self, data: list[WeatherData]) -> str:
        """Save cleaned data to Parquet."""
        if not data:
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"weather_cleaned_{timestamp}.parquet"
        filepath = self.clean_dir / filename
        
        records = [d.model_dump(mode='json') for d in data]
        df = pd.DataFrame(records)
        df.to_parquet(filepath, index=False)
        
        return str(filepath)
    
    async def load_cleaned(
        self,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[WeatherData]:
        """Load cleaned Parquet data."""
        pattern = f"{self.clean_dir}/*.parquet"
        
        if source:
            pattern = f"{self.clean_dir}/{source}_*.parquet"
        
        files = list(Path(pattern).glob("*.parquet"))
        
        if not files:
            return []
        
        dfs = []
        for f in files:
            try:
                df = pd.read_parquet(f)
                dfs.append(df)
            except Exception as e:
                logger.warning(f"Error loading {f}: {e}")
        
        if not dfs:
            return []
        
        combined = pd.concat(dfs, ignore_index=True)
        
        if start_date:
            combined = combined[combined['timestamp'] >= start_date]
        if end_date:
            combined = combined[combined['timestamp'] <= end_date]
        
        return [WeatherData(**row) for row in combined.to_dict('records')]
    
    async def list_available_data(self) -> list[dict]:
        """List available Parquet files."""
        result = []
        
        for f in self.raw_dir.glob("*.parquet"):
            result.append({
                "type": "raw",
                "format": "parquet",
                "path": str(f),
                "size_bytes": f.stat().st_size
            })
        
        for f in self.clean_dir.glob("*.parquet"):
            result.append({
                "type": "cleaned",
                "format": "parquet",
                "path": str(f),
                "size_bytes": f.stat().st_size
            })
        
        return result