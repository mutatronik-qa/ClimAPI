"""
Normalización y agregación de puntos de datos en memoria.
"""
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.data_points: List[Dict[str, Any]] = []

    def _convert_temperature(self, temp: Any):
        try:
            return float(temp) if temp is not None else None
        except (ValueError, TypeError):
            return None

    def normalize_data(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            "timestamp": source_data.get("timestamp") or datetime.utcnow().isoformat(),
            "temperature": self._convert_temperature(source_data.get("temperature")),
            "humidity": source_data.get("humidity"),
            "location": source_data.get("location")
        }
        self.data_points.append(normalized)
        return normalized

    def aggregate_data(self, data_points: List[Dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame(data_points)
        if df.empty:
            return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df.set_index("timestamp", inplace=True)
        aggregated = df.resample("H").mean()
        return aggregated

    def get_aggregated_data(self) -> pd.DataFrame:
        return self.aggregate_data(self.data_points)