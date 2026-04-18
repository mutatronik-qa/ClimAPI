"""Shared utilities."""

from datetime import datetime
from typing import Optional
import logging

import pandas as pd


def setup_logging(
    name: str,
    level: str = "INFO",
    format: str = "text"
) -> logging.Logger:
    """Setup logging for a module."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        if format == "json":
            formatter = logging.Formatter(
                '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """Validate latitude and longitude."""
    if not -90 <= lat <= 90:
        raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
    return lat, lon


def normalize_timestamp(ts: any) -> Optional[datetime]:
    """Normalize timestamp to datetime."""
    if ts is None:
        return None
    
    try:
        if isinstance(ts, str):
            return pd.to_datetime(ts)
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts)
    except Exception:
        pass
    
    return None


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dictionaries."""
    if df.empty:
        return []
    
    return df.to_dict('records')


def safe_float(value: any) -> Optional[float]:
    """Safely convert value to float."""
    if value is None:
        return None
    
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: any) -> Optional[int]:
    """Safely convert value to int."""
    if value is None:
        return None
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return None