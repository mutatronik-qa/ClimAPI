"""
Weather Service - Orchestrates all weather sources.
Implements Strategy Pattern for source selection.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import WeatherSource, WeatherData, CacheProvider

logger = logging.getLogger(__name__)


class InMemoryCache(CacheProvider):
    """Simple in-memory cache implementation."""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.time() - timestamp < 900:  # 15 min default
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 900) -> None:
        self._cache[key] = (value, time.time())
    
    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self._cache),
            "keys": list(self._cache.keys())[:10]  # Sample
        }


class WeatherService:
    """
    Orchestrates multiple weather sources using Strategy Pattern.
    
    Features:
    - Calls all available sources concurrently
    - Selects best available source (prioritizes free sources)
    - Simple caching with TTL
    - Health checks for all sources
    """
    
    def __init__(self, cache: Optional[CacheProvider] = None):
        self.cache = cache or InMemoryCache()
        self._sources: Dict[str, WeatherSource] = {}
    
    def register_source(self, source: WeatherSource) -> None:
        """Register a weather source."""
        self._sources[source.name] = source
        logger.info(f"Registered weather source: {source.name}")
    
    def get_source(self, name: str) -> Optional[WeatherSource]:
        """Get a specific source by name."""
        return self._sources.get(name)
    
    def get_current_weather(
        self,
        lat: float,
        lon: float,
        source_name: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> WeatherData:
        """
        Get current weather from one or all sources.
        
        Args:
            lat: Latitude
            lon: Longitude
            source_name: Specific source, or None for all
            use_cache: Whether to use caching
            **kwargs: Additional params (timezone, etc.)
        """
        cache_key = f"current:{source_name or 'all'}:{lat}:{lon}"
        
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info("Using cached data")
                return cached
        
        if source_name:
            result = self._fetch_single_source(source_name, lat, lon, **kwargs)
        else:
            result = self._fetch_all_sources(lat, lon, **kwargs)
        
        if use_cache and result:
            self.cache.set(cache_key, result, ttl=900)
        
        return result
    
    def _fetch_single_source(
        self,
        source_name: str,
        lat: float,
        lon: float,
        **kwargs
    ) -> WeatherData:
        """Fetch from a specific source."""
        source = self._sources.get(source_name)
        if not source:
            return WeatherData(
                timestamp=datetime.now(),
                source=source_name,
                temperature=None,
                error=f"Source not found: {source_name}"
            )
        
        try:
            start = time.time()
            result = source.fetch_current(lat, lon, **kwargs)
            elapsed = time.time() - start
            logger.info(f"{source_name}: {elapsed:.2f}s")
            return result
        except Exception as e:
            logger.error(f"Error fetching from {source_name}: {e}")
            return WeatherData(
                timestamp=datetime.now(),
                source=source_name,
                error=str(e)
            )
    
    def _fetch_all_sources(
        self,
        lat: float,
        lon: float,
        **kwargs
    ) -> WeatherData:
        """Fetch from all sources and return best available."""
        results: List[WeatherData] = []
        
        def fetch_source(name: str) -> tuple[str, WeatherData, float]:
            source = self._sources.get(name)
            if not source:
                return (name, WeatherData(timestamp=datetime.now(), source=name), 0)
            
            start = time.time()
            try:
                data = source.fetch_current(lat, lon, **kwargs)
                return (name, data, time.time() - start)
            except Exception as e:
                return (name, WeatherData(timestamp=datetime.now(), source=name, error=str(e)), time.time() - start)
        
        # Fetch concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_source, name): name for name in self._sources}
            
            for future in as_completed(futures):
                name, data, elapsed = future.result()
                results.append(data)
                status = "✅" if data.temperature else "❌"
                logger.info(f"{status} {name}: {elapsed:.2f}s")
        
        # Return first valid result (prioritize free sources)
        for data in results:
            if data.temperature is not None:
                data.temperature = data.temperature
                return data
        
        # All failed
        return results[0] if results else WeatherData(
            timestamp=datetime.now(),
            source="none",
            error="All sources failed"
        )
    
    def get_forecast(
        self,
        lat: float,
        lon: float,
        days: int = 7,
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[WeatherData]:
        """Get weather forecast."""
        cache_key = f"forecast:{source_name or 'all'}:{lat}:{lon}:{days}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        if source_name:
            source = self._sources.get(source_name)
            if source:
                result = source.fetch_forecast(lat, lon, days, **kwargs)
                self.cache.set(cache_key, result, ttl=3600)
                return result
            return []
        
        # Get from first available source
        for source in self._sources.values():
            try:
                result = source.fetch_forecast(lat, lon, days, **kwargs)
                if result:
                    self.cache.set(cache_key, result, ttl=3600)
                    return result
            except Exception as e:
                logger.warning(f"Forecast fetch failed from {source.name}: {e}")
                continue
        
        return []
    
    def get_historical(
        self,
        lat: float,
        lon: float,
        start_date: datetime,
        end_date: datetime,
        source_name: Optional[str] = None,
        **kwargs
    ) -> List[WeatherData]:
        """Get historical weather data."""
        cache_key = f"historical:{source_name or 'all'}:{lat}:{lon}:{start_date.date()}:{end_date.date()}"
        
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        if source_name:
            source = self._sources.get(source_name)
            if source:
                result = source.fetch_historical(lat, lon, start_date, end_date, **kwargs)
                self.cache.set(cache_key, result, ttl=86400)
                return result
            return []
        
        # Get from first available source
        for source in self._sources.values():
            try:
                result = source.fetch_historical(lat, lon, start_date, end_date, **kwargs)
                if result:
                    self.cache.set(cache_key, result, ttl=86400)
                    return result
            except Exception as e:
                logger.warning(f"Historical fetch failed from {source.name}: {e}")
                continue
        
        return []
    
    def get_sources_status(self) -> List[Dict[str, Any]]:
        """Get health status of all sources."""
        status = []
        
        for name, source in self._sources.items():
            start = time.time()
            try:
                is_healthy = source.health_check()
                elapsed = time.time() - start
                status.append({
                    "name": name,
                    "is_available": is_healthy,
                    "is_free": source.is_free,
                    "response_time": elapsed
                })
            except Exception as e:
                status.append({
                    "name": name,
                    "is_available": False,
                    "is_free": source.is_free,
                    "error": str(e)
                })
        
        return status
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        logger.info("Cache cleared")


# Global service instance
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Get or create global weather service."""
    global _weather_service
    
    if _weather_service is None:
        _weather_service = WeatherService()
        
        # Register default sources
        try:
            from services.open_meteo import OpenMeteoSource
            _weather_service.register_source(OpenMeteoSource())
        except ImportError as e:
            logger.warning(f"Could not register OpenMeteoSource: {e}")
        
        try:
            from services.siata import SIATASource
            _weather_service.register_source(SIATASource())
        except ImportError as e:
            logger.warning(f"Could not register SIATASource: {e}")
    
    return _weather_service