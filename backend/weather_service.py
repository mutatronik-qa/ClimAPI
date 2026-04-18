"""
Weather Service - Orchestrates all weather sources.
Simple, clean, production-ready.
"""
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.sources import get_all_sources, PRIORITY_SOURCES

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Orchestrates multiple weather sources.
    
    Features:
    - Calls all available sources concurrently
    - Skips failing sources (no crash)
    - Returns merged results or best available
    - Simple caching with TTL
    """
    
    def __init__(self, cache_ttl: int = 900):  # 15 min default
        self.sources = get_all_sources()
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, tuple[Any, float]] = {}
    
    def _get_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Dict[str, Any]) -> None:
        """Cache result."""
        self._cache[key] = (data, time.time())
    
    def get_weather(
        self,
        lat: float,
        lon: float,
        source: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get weather data from one or all sources.
        
        Args:
            lat: Latitude
            lon: Longitude
            source: Specific source name, or None for all
            use_cache: Whether to use caching
            **kwargs: Additional params (timezone, etc.)
            
        Returns:
            If source specified: single result dict
            If source is None: list of results from all sources
        """
        cache_key = f"weather:{lat}:{lon}:{source or 'all'}"
        
        # Check cache
        if use_cache:
            cached = self._get_cache(cache_key)
            if cached:
                logger.info("📦 Using cached data")
                return cached
        
        if source:
            # Get from specific source
            result = self._call_source(source, lat, lon, **kwargs)
        else:
            # Get from all sources concurrently
            result = self._call_all_sources(lat, lon, **kwargs)
        
        # Cache result
        if use_cache and result:
            self._set_cache(cache_key, result)
        
        return result
    
    def _call_source(
        self,
        source_name: str,
        lat: float,
        lon: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Call a specific source."""
        if source_name not in self.sources:
            return {
                "error": f"Unknown source: {source_name}",
                "available_sources": list(self.sources.keys())
            }
        
        start = time.time()
        try:
            source_func = self.sources[source_name]
            result = source_func(lat, lon, **kwargs)
            elapsed = time.time() - start
            
            logger.info(f"✅ {source_name}: {elapsed:.2f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"❌ {source_name}: failed after {elapsed:.2f}s - {e}")
            return {
                "error": str(e),
                "source": source_name,
                "timestamp": datetime.now().isoformat()
            }
    
    def _call_all_sources(
        self,
        lat: float,
        lon: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Call all sources concurrently and merge results."""
        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        
        def call_source(name: str) -> tuple[str, Dict[str, Any], float]:
            start = time.time()
            try:
                func = self.sources[name]
                data = func(lat, lon, **kwargs)
                elapsed = time.time() - start
                
                # Check if we got valid data
                if data.get("temperature") is not None:
                    logger.info(f"✅ {name}: success ({elapsed:.2f}s)")
                    return (name, data, elapsed)
                else:
                    logger.warning(f"⚠️ {name}: no data ({elapsed:.2f}s)")
                    return (name, {"source": name, "error": data.get("error", "no data")}, elapsed)
                    
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"❌ {name}: failed ({elapsed:.2f}s) - {e}")
                return (name, {"source": name, "error": str(e)}, elapsed)
        
        # Call all sources concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(call_source, name): name for name in self.sources}
            
            for future in as_completed(futures):
                name, data, elapsed = future.result()
                data["response_time"] = elapsed
                results.append(data)
        
        # Get the best result (first with valid data)
        valid_results = [r for r in results if r.get("temperature") is not None]
        
        if valid_results:
            primary = valid_results[0]
            # Add all sources to response
            primary["all_sources"] = results
            primary["sources_responded"] = [r["source"] for r in valid_results]
            primary["sources_failed"] = [r["source"] for r in results if r.get("error")]
        else:
            # No valid data from any source
            primary = {
                "error": "All sources failed",
                "all_sources": results,
                "timestamp": datetime.now().isoformat()
            }
        
        return primary
    
    def get_sources_status(self) -> List[Dict[str, Any]]:
        """Get status of all sources (for health check)."""
        # Test with default location
        test_lat, test_lon = 6.244, -75.581
        
        status = []
        for name in self.sources:
            start = time.time()
            try:
                result = self.sources[name](test_lat, test_lon)
                elapsed = time.time() - start
                
                status.append({
                    "name": name,
                    "status": "ok" if result.get("temperature") else "no_data",
                    "response_time": elapsed,
                    "error": result.get("error")
                })
            except Exception as e:
                status.append({
                    "name": name,
                    "status": "error",
                    "response_time": time.time() - start,
                    "error": str(e)
                })
        
        return status
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        logger.info("📦 Cache cleared")


# Global service instance
weather_service = WeatherService()


def get_weather_service() -> WeatherService:
    """Get the global weather service instance."""
    return weather_service