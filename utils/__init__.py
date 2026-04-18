"""
Utils - Caching, Data Processing, and Utilities
"""
import csv
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import time

logger = logging.getLogger(__name__)


# ============================================
# Cache Utilities
# ============================================

class SimpleCache:
    """Simple in-memory cache with TTL."""
    
    def __init__(self, default_ttl: int = 900):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < self.default_ttl:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self._cache[key] = (value, time.time())
    
    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        return {"entries": len(self._cache)}


# ============================================
# Data Processing Utilities
# ============================================

class DataProcessor:
    """
    Unified data processor - combines normalizer, diagnostics, and transform.
    Handles all data cleaning and transformation tasks.
    """
    
    # Valid ranges for weather data
    TEMP_MIN = -50
    TEMP_MAX = 60
    HUMIDITY_MIN = 0
    HUMIDITY_MAX = 100
    PRECIP_MIN = 0
    WIND_MAX = 200
    
    def __init__(self):
        pass
    
    def normalize(self, data: Dict[str, Any], source: str) -> Dict[str, Any]:
        """
        Normalize weather data to standard format.
        
        Args:
            data: Raw data from source
            source: Source name
            
        Returns:
            Normalized data dictionary
        """
        normalized = {
            "timestamp": data.get("timestamp", datetime.now().isoformat()),
            "temperature": self._clean_numeric(data.get("temperature")),
            "humidity": self._clean_numeric(data.get("humidity")),
            "precipitation": self._clean_numeric(data.get("precipitation"), min_val=self.PRECIP_MIN),
            "wind_speed": self._clean_numeric(data.get("wind_speed"), min_val=0, max_val=self.WIND_MAX),
            "source": source
        }
        
        return normalized
    
    def validate(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate weather data.
        
        Args:
            data: Weather data to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Temperature validation
        temp = data.get("temperature")
        if temp is not None:
            if temp < self.TEMP_MIN or temp > self.TEMP_MAX:
                errors.append(f"Temperature {temp}°C out of range [{self.TEMP_MIN}, {self.TEMP_MAX}]")
        
        # Humidity validation
        humidity = data.get("humidity")
        if humidity is not None:
            if humidity < self.HUMIDITY_MIN or humidity > self.HUMIDITY_MAX:
                errors.append(f"Humidity {humidity}% out of range [{self.HUMIDITY_MIN}, {self.HUMIDITY_MAX}]")
        
        # Wind speed validation
        wind = data.get("wind_speed")
        if wind is not None:
            if wind < 0 or wind > self.WIND_MAX:
                errors.append(f"Wind speed {wind} km/h out of range [0, {self.WIND_MAX}]")
        
        return len(errors) == 0, errors
    
    def transform(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform list of weather data - clean and standardize.
        
        Args:
            data_list: List of raw weather data
            
        Returns:
            List of cleaned data
        """
        cleaned = []
        
        for data in data_list:
            source = data.get("source", "unknown")
            normalized = self.normalize(data, source)
            
            is_valid, errors = self.validate(normalized)
            
            if is_valid:
                cleaned.append(normalized)
            else:
                logger.warning(f"Invalid data from {source}: {errors}")
                # Include with warning but mark as potentially invalid
                normalized["_warnings"] = errors
                cleaned.append(normalized)
        
        return cleaned
    
    def aggregate(self, data_list: List[Dict[str, Any]], frequency: str = "hourly") -> Dict[str, Any]:
        """
        Aggregate weather data by time frequency.
        
        Args:
            data_list: List of weather data
            frequency: Aggregation frequency (hourly, daily)
            
        Returns:
            Aggregated statistics
        """
        if not data_list:
            return {}
        
        import numpy as np
        
        temps = [d["temperature"] for d in data_list if d.get("temperature") is not None]
        humidities = [d["humidity"] for d in data_list if d.get("humidity") is not None]
        precips = [d["precipitation"] for d in data_list if d.get("precipitation") is not None]
        winds = [d["wind_speed"] for d in data_list if d.get("wind_speed") is not None]
        
        result = {
            "count": len(data_list),
            "temperature": {
                "mean": np.mean(temps) if temps else None,
                "min": np.min(temps) if temps else None,
                "max": np.max(temps) if temps else None,
            },
            "humidity": {
                "mean": np.mean(humidities) if humidities else None,
            },
            "precipitation": {
                "total": sum(precips) if precips else 0,
            },
            "wind_speed": {
                "mean": np.mean(winds) if winds else None,
                "max": np.max(winds) if winds else None,
            }
        }
        
        return result
    
    @staticmethod
    def _clean_numeric(value: Any, min_val: float = None, max_val: float = None) -> Optional[float]:
        """Clean and validate numeric value."""
        if value is None:
            return None
        
        try:
            val = float(value)
            
            if min_val is not None and val < min_val:
                return None
            if max_val is not None and val > max_val:
                return None
            
            return val
        except (ValueError, TypeError):
            return None


# ============================================
# Storage Utilities
# ============================================

class DataStorage:
    """Simple file-based data storage."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        
        # Create directories
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
    
    def save_raw(self, data: Dict[str, Any], source: str) -> str:
        """Save raw data to CSV."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{source}_{timestamp}.csv"
        filepath = self.raw_dir / filename
        
        self._write_csv(filepath, [data])
        logger.info(f"Saved raw data to {filepath}")
        return str(filepath)
    
    def save_processed(self, data: List[Dict[str, Any]], source: str = "combined") -> str:
        """Save processed/merged data."""
        filename = f"weather_{source}.csv"
        filepath = self.processed_dir / filename
        
        self._write_csv(filepath, data, append=True)
        logger.info(f"Saved processed data to {filepath}")
        return str(filepath)
    
    def load(self, filepath: str) -> List[Dict[str, Any]]:
        """Load data from CSV."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except FileNotFoundError:
            return []
    
    def _write_csv(self, filepath: Path, data: List[Dict], append: bool = False) -> None:
        """Write data to CSV file."""
        if not data:
            return
        
        fieldnames = list(data[0].keys())
        mode = 'a' if append else 'w'
        write_header = not append or not filepath.exists()
        
        with open(filepath, mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerows(data)


# ============================================
# Cleanup Utilities
# ============================================

def cleanup_temp_files(directory: str = ".") -> Dict[str, int]:
    """
    Clean up temporary and cache files.
    
    Args:
        directory: Base directory to clean
        
    Returns:
        Dictionary with cleanup statistics
    """
    import shutil
    
    patterns_to_remove = [
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".pytest_cache",
        "*.egg-info",
        ".mypy_cache",
        ".ruff_cache",
        "cache/",
        "logs/*.log",
    ]
    
    dirs_to_remove = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
    files_removed = 0
    dirs_removed = 0
    
    base_path = Path(directory)
    
    # Remove cache directories
    for dir_name in dirs_to_remove:
        for d in base_path.rglob(dir_name):
            try:
                shutil.rmtree(d)
                dirs_removed += 1
                logger.info(f"Removed directory: {d}")
            except Exception as e:
                logger.warning(f"Could not remove {d}: {e}")
    
    # Remove .pyc files
    for f in base_path.rglob("*.pyc"):
        try:
            f.unlink()
            files_removed += 1
        except Exception:
            pass
    
    return {
        "files_removed": files_removed,
        "dirs_removed": dirs_removed
    }


def create_data_directories(base_dir: str = "data") -> None:
    """Create data directories if they don't exist."""
    base = Path(base_dir)
    (base / "raw").mkdir(parents=True, exist_ok=True)
    (base / "processed").mkdir(parents=True, exist_ok=True)
    (base / "cache").mkdir(parents=True, exist_ok=True)
    logger.info(f"Created data directories in {base_dir}")


# ============================================
# Re-export commonly used
# ============================================

__all__ = [
    "SimpleCache",
    "DataProcessor", 
    "DataStorage",
    "cleanup_temp_files",
    "create_data_directories",
]