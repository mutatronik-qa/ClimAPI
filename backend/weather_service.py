"""
Weather Service - SINGLE SOURCE OF TRUTH
All logic lives here: sources, caching, merging, error handling.
API, CLI, and Dashboard MUST use this service.
"""
import csv
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.cache import SimpleCache
from backend.sources import SOURCES, PRIORITY, get_source

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ====================
# Weather Service
# ====================

class WeatherService:
    """
    Single source of truth for weather data.
    - Calls all sources concurrently
    - Handles failures gracefully
    - Caches results
    - Returns merged or per-source data
    """
    
    def __init__(self, cache_ttl: int = 900):
        self.cache = SimpleCache(cache_ttl)
        self.default_ttl = cache_ttl
    
    def get_weather(
        self,
        lat: float,
        lon: float,
        source: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get weather data.
        
        Args:
            lat, lon: Coordinates
            source: Specific source name, or None for all
            use_cache: Whether to use caching
            
        Returns:
            Single dict with merged data OR all_sources list
        """
        cache_key = f"weather:{source or 'all'}:{lat}:{lon}"
        
        # Check cache
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                logger.info("📦 Using cached data")
                return cached
        
        # Fetch from source(s)
        if source:
            result = self._call_source(source, lat, lon, **kwargs)
        else:
            result = self._call_all_sources(lat, lon, **kwargs)
        
        # Cache result
        if use_cache and result:
            self.cache.set(cache_key, result, self.default_ttl)
        
        return result
    
    def _call_source(
        self,
        source_name: str,
        lat: float,
        lon: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Call a specific source."""
        source_func = get_source(source_name)
        
        if not source_func:
            return {
                "error": f"Unknown source: {source_name}",
                "available": list(SOURCES.keys())
            }
        
        start = time.time()
        try:
            result = source_func(lat, lon, **kwargs)
            elapsed = time.time() - start
            
            if result.get("error"):
                logger.warning(f"❌ {source_name}: {result['error']} ({elapsed:.2f}s)")
            else:
                logger.info(f"✅ {source_name}: {elapsed:.2f}s")
            
            result["response_time"] = elapsed
            return result
            
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"❌ {source_name}: EXCEPTION {e} ({elapsed:.2f}s)")
            return {
                "source": source_name,
                "error": str(e),
                "response_time": elapsed
            }
    
    def _call_all_sources(
        self,
        lat: float,
        lon: float,
        **kwargs
    ) -> Dict[str, Any]:
        """Call all sources concurrently and merge."""
        results: List[Dict[str, Any]] = []
        
        def fetch(name: str) -> tuple[str, Dict[str, Any], float]:
            start = time.time()
            try:
                func = get_source(name)
                data = func(lat, lon, **kwargs)
                elapsed = time.time() - start
                
                status = "✅" if not data.get("error") and data.get("temperature") else "❌"
                logger.info(f"{status} {name}: {elapsed:.2f}s")
                
                return (name, data, elapsed)
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"❌ {name}: {e}")
                return (name, {"source": name, "error": str(e)}, elapsed)
        
        # Concurrent fetch
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch, name): name for name in SOURCES}
            
            for future in as_completed(futures):
                name, data, elapsed = future.result()
                results.append(data)
        
        # Get first valid result (priority order)
        valid = [r for r in results if r.get("temperature") is not None]
        
        if valid:
            primary = valid[0].copy()
            primary["all_sources"] = results
            primary["sources_responded"] = [r["source"] for r in valid]
            primary["sources_failed"] = [r["source"] for r in results if r.get("error")]
            return primary
        
        # All failed
        return {
            "error": "All sources failed",
            "all_sources": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_sources_status(self) -> List[Dict[str, Any]]:
        """Check health of all sources."""
        status = []
        test_lat, test_lon = 6.244, -75.581  # Medellín
        
        for name in SOURCES:
            start = time.time()
            try:
                result = get_source(name)(test_lat, test_lon)
                elapsed = time.time() - start
                
                status.append({
                    "name": name,
                    "available": result.get("temperature") is not None,
                    "response_time": elapsed,
                    "error": result.get("error")
                })
            except Exception as e:
                status.append({
                    "name": name,
                    "available": False,
                    "response_time": time.time() - start,
                    "error": str(e)
                })
        
        return status
    
    def save_data(self, data: Dict[str, Any], source: str = "combined") -> None:
        """Save data to CSV."""
        import csv
        from pathlib import Path
        
        data_dir = Path("data")
        raw_dir = data_dir / "raw"
        processed_dir = data_dir / "processed"
        
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to raw (per source)
        if data.get("source"):
            filepath = raw_dir / f"{data['source']}.csv"
            self._append_csv(filepath, data)
        
        # Save merged
        if source == "combined" and data.get("temperature") is not None:
            filepath = processed_dir / "weather.csv"
            self._append_csv(filepath, data)
    
    def _append_csv(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Append data to CSV."""
        import os
        
        fieldnames = ["timestamp", "temperature", "humidity", "precipitation", "wind_speed", "source"]
        write_header = not os.path.exists(filepath)
        
        with open(filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow({
                "timestamp": data.get("timestamp", datetime.now().isoformat()),
                "temperature": data.get("temperature"),
                "humidity": data.get("humidity"),
                "precipitation": data.get("precipitation"),
                "wind_speed": data.get("wind_speed"),
                "source": data.get("source", "unknown")
            })
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self.cache.clear()
        logger.info("📦 Cache cleared")


# ====================
# Global Service Instance
# ====================

_service: Optional[WeatherService] = None


def get_service() -> WeatherService:
    """Get global weather service."""
    global _service
    if _service is None:
        _service = WeatherService()
    return _service