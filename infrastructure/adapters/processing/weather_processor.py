"""Data processor adapter - normalizes and validates weather data."""
import logging
from typing import Optional
from datetime import datetime
import numpy as np

from domain.entities.weather import WeatherData
from domain.interfaces.sources import DataProcessor

logger = logging.getLogger(__name__)


class WeatherDataProcessor(DataProcessor):
    """
    Data processor adapter that normalizes and validates weather data.
    
    Handles:
    - Normalization to unified schema
    - Missing data handling
    - Outlier detection
    - Data validation
    """
    
    def __init__(
        self,
        temp_min: float = -50,
        temp_max: float = 60,
        humidity_min: float = 0,
        humidity_max: float = 100,
        wind_max: float = 200
    ):
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.humidity_min = humidity_min
        self.humidity_max = humidity_max
        self.wind_max = wind_max
    
    def normalize(self, raw_data: dict, source: str) -> list[WeatherData]:
        """
        Normalize raw data to unified WeatherData schema.
        
        Args:
            raw_data: Raw data from API
            source: Source identifier
            
        Returns:
            List of normalized WeatherData objects
        """
        # This is a simplified normalizer - in production you'd have
        # source-specific normalizers for each API
        result = []
        
        if "hourly" in raw_data:
            hourly = raw_data["hourly"]
            times = hourly.get("time", [])
            
            for i, time_str in enumerate(times):
                try:
                    timestamp = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    
                    weather_data = WeatherData(
                        timestamp=timestamp,
                        temperature=self._normalize_value(hourly.get("temperature_2m", []), i, self.temp_min, self.temp_max),
                        humidity=self._normalize_value(hourly.get("relative_humidity_2m", []), i, self.humidity_min, self.humidity_max),
                        precipitation=self._normalize_value(hourly.get("precipitation", []), i, 0, None),
                        wind_speed=self._normalize_value(hourly.get("wind_speed_10m", []), i, 0, self.wind_max),
                        source=source
                    )
                    result.append(weather_data)
                    
                except (ValueError, IndexError) as e:
                    logger.debug(f"Skipping invalid data point: {e}")
                    continue
        
        return result
    
    def _normalize_value(
        self,
        values: list,
        index: int,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None
    ) -> Optional[float]:
        """Normalize a single value with bounds checking."""
        try:
            if index >= len(values):
                return None
            
            val = values[index]
            if val is None:
                return None
            
            float_val = float(val)
            
            # Check bounds
            if min_val is not None and float_val < min_val:
                return None
            if max_val is not None and float_val > max_val:
                return None
            
            return float_val
            
        except (ValueError, TypeError):
            return None
    
    def validate(self, data: list[WeatherData]) -> tuple[list[WeatherData], list[str]]:
        """
        Validate and clean weather data.
        
        Args:
            data: List of WeatherData to validate
            
        Returns:
            Tuple of (cleaned_data, issues)
        """
        cleaned = []
        issues = []
        
        for i, weather in enumerate(data):
            item_issues = []
            
            # Validate temperature
            if weather.temperature is not None:
                if weather.temperature < self.temp_min or weather.temperature > self.temp_max:
                    item_issues.append(f"temperature out of range: {weather.temperature}")
            
            # Validate humidity
            if weather.humidity is not None:
                if weather.humidity < self.humidity_min or weather.humidity > self.humidity_max:
                    item_issues.append(f"humidity out of range: {weather.humidity}")
            
            # Validate wind speed
            if weather.wind_speed is not None:
                if weather.wind_speed < 0 or weather.wind_speed > self.wind_max:
                    item_issues.append(f"wind_speed out of range: {weather.wind_speed}")
            
            # Validate precipitation
            if weather.precipitation is not None:
                if weather.precipitation < 0:
                    item_issues.append(f"negative precipitation: {weather.precipitation}")
            
            if item_issues:
                issues.append(f"Record {i}: {', '.join(item_issues)}")
                # Still include the record but with None for invalid values
                weather.temperature = None if weather.temperature and weather.temperature < self.temp_min else weather.temperature
            
            cleaned.append(weather)
        
        return cleaned, issues
    
    def aggregate(
        self,
        data: list[WeatherData],
        frequency: str = "hourly"
    ) -> list[WeatherData]:
        """
        Aggregate data by time frequency.
        
        Args:
            data: List of WeatherData
            frequency: Aggregation frequency (hourly, daily, etc.)
            
        Returns:
            List of aggregated WeatherData
        """
        import pandas as pd
        
        if not data:
            return []
        
        # Convert to DataFrame
        df = pd.DataFrame([{
            'timestamp': d.timestamp,
            'temperature': d.temperature,
            'humidity': d.humidity,
            'precipitation': d.precipitation,
            'wind_speed': d.wind_speed,
            'source': d.source
        } for d in data])
        
        if df.empty:
            return []
        
        # Set timestamp as index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        # Aggregate based on frequency
        if frequency == "daily":
            resampled = df.resample("D").mean()
        elif frequency == "hourly":
            resampled = df.resample("H").mean()
        else:
            resampled = df.resample(frequency).mean()
        
        # Convert back to WeatherData
        result = []
        for timestamp, row in resampled.iterrows():
            result.append(WeatherData(
                timestamp=timestamp.to_pydatetime(),
                temperature=row['temperature'] if pd.notna(row['temperature']) else None,
                humidity=row['humidity'] if pd.notna(row['humidity']) else None,
                precipitation=row['precipitation'] if pd.notna(row['precipitation']) else None,
                wind_speed=row['wind_speed'] if pd.notna(row['wind_speed']) else None,
                source="aggregated"
            ))
        
        return result


class DataQualityAnalyzer:
    """Analyze data quality and generate reports."""
    
    @staticmethod
    def analyze(data: list[WeatherData]) -> dict:
        """Generate comprehensive data quality analysis."""
        if not data:
            return {
                "summary": {
                    "total_records": 0,
                    "overall_quality": "no_data"
                }
            }
        
        total = len(data)
        
        # Field completeness
        field_stats = {}
        for field in ['temperature', 'humidity', 'precipitation', 'wind_speed']:
            values = [getattr(d, field) for d in data]
            non_null = [v for v in values if v is not None]
            field_stats[field] = {
                "total": total,
                "available": len(non_null),
                "percent": round((len(non_null) / total) * 100, 2) if total > 0 else 0
            }
        
        # Calculate overall quality
        avg_completeness = sum(s['percent'] for s in field_stats.values()) / len(field_stats)
        
        if avg_completeness >= 90:
            quality = "excellent"
        elif avg_completeness >= 75:
            quality = "good"
        elif avg_completeness >= 50:
            quality = "fair"
        else:
            quality = "poor"
        
        # Sources
        sources = list(set(d.source for d in data))
        
        # Timestamp range
        timestamps = [d.timestamp for d in data if d.timestamp]
        ts_range = {
            "start": min(timestamps).isoformat() if timestamps else None,
            "end": max(timestamps).isoformat() if timestamps else None
        }
        
        return {
            "summary": {
                "total_records": total,
                "complete_records": sum(
                    1 for d in data
                    if all(getattr(d, f) is not None for f in ['temperature', 'humidity', 'precipitation', 'wind_speed'])
                ),
                "missing_data_percent": round(100 - avg_completeness, 2),
                "overall_quality": quality,
                "data_sources": sources,
                "timestamp_range": ts_range
            },
            "per_field": field_stats
        }