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
    
    def __init__(self, cache_ttl: int = 1800):
        self.cache = SimpleCache(cache_ttl)
        self.default_ttl = cache_ttl
        self._health_cache = {}
        self._health_cache_ttl = 300  # 5 minutes
    
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
            
            result["lat"] = lat
            result["lon"] = lon
            
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
        """Call all sources concurrently with timeout."""
        results: List[Dict[str, Any]] = []
        
        def fetch(name: str) -> tuple[str, Dict[str, Any], float]:
            start = time.time()
            try:
                func = get_source(name)
                data = func(lat, lon, **kwargs)
                data["lat"] = lat
                data["lon"] = lon
                elapsed = time.time() - start
                
                status = "✅" if not data.get("error") and data.get("temperature") else "❌"
                logger.info(f"{status} {name}: {elapsed:.2f}s")
                
                return (name, data, elapsed)
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"❌ {name}: {e}")
                return (name, {"source": name, "error": str(e)}, elapsed)
        
        # Concurrent fetch with reasonable timeout
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch, name): name for name in SOURCES}
            
            # Wait max 15 seconds total, collect results as they come
            try:
                for future in as_completed(futures, timeout=15):
                    try:
                        name, data, elapsed = future.result(timeout=10)
                        results.append(data)
                    except Exception as e:
                        name = futures.get(future, "unknown")
                        logger.warning(f"⚠️ {name} timeout/error: {e}")
                        results.append({"source": name, "error": f"Timeout: {str(e)}"})
            except TimeoutError:
                logger.warning("⚠️ Sources batch timeout (15s) - returning partial results")
                for future in futures:
                    if not future.done():
                        future.cancel()
        
        # Merge all valid results (even partial)
        merged = self._merge_results(results)
        merged["all_sources"] = results
        merged["sources_responded"] = [r["source"] for r in results if not r.get("error") and r.get("temperature") is not None]
        merged["sources_failed"] = [r["source"] for r in results if r.get("error") or r.get("temperature") is None]
        
        return merged
    
    def _merge_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from multiple sources by averaging numeric values."""
        valid_results = [r for r in results if not r.get("error") and r.get("temperature") is not None]
        
        if not valid_results:
            return {
                "error": "All sources failed",
                "timestamp": datetime.now().isoformat()
            }
        
        # Collect all numeric values, ensuring they are indeed numbers
        def get_numeric(results, key):
            vals = []
            for r in results:
                val = r.get(key)
                if val is not None and isinstance(val, (int, float)):
                    vals.append(float(val))
            return vals

        temperatures = get_numeric(valid_results, "temperature")
        humidities = get_numeric(valid_results, "humidity")
        precipitations = get_numeric(valid_results, "precipitation")
        wind_speeds = get_numeric(valid_results, "wind_speed")
        
        # Calculate averages safely
        def avg(values: List[float]) -> Optional[float]:
            if not values: return None
            try:
                return round(sum(values) / len(values), 2)
            except Exception as e:
                logger.error(f"Error calculating average: {e}")
                return None
        
        merged = {
            "timestamp": datetime.now().isoformat(),
            "temperature": avg(temperatures),
            "humidity": avg(humidities),
            "precipitation": avg(precipitations),
            "wind_speed": avg(wind_speeds),
            "source": "merged",
            "lat": valid_results[0].get("lat"),
            "lon": valid_results[0].get("lon"),
            "sources_used": len(valid_results)
        }
        
        return merged
    
    def get_sources_status(self, use_cache: bool = True, fast: bool = False) -> List[Dict[str, Any]]:
        """
        Check health of all sources with aggressive timeout.
        - fast=True uses very short timeouts (3s)
        - use_cache=True returns cached status if still valid
        """
        now = time.time()
        
        # Check health cache
        if use_cache and self._health_cache:
            if all(now - s.get("_checked_at", 0) < self._health_cache_ttl for s in self._health_cache.values()):
                logger.info("📡 Using cached sources status")
                return list(self._health_cache.values())
        
        status = []
        test_lat, test_lon = 6.244, -75.581  # Medellín
        
        def check_source(name: str) -> Dict[str, Any]:
            start = time.time()
            try:
                # Use shorter timeouts for health check
                timeout = 5 if fast else 10
                result = get_source(name)(test_lat, test_lon, timeout=timeout, max_items=5)
                elapsed = time.time() - start
                
                # Radar and SIATA might not return temperature but are online if they return status/files
                is_available = result.get("temperature") is not None or (name in ["ideam-radar", "siata"] and not result.get("error"))
                
                return {
                    "name": name,
                    "available": is_available,
                    "response_time": elapsed,
                    "error": result.get("error"),
                    "_checked_at": now
                }
            except Exception as e:
                elapsed = time.time() - start
                return {
                    "name": name,
                    "available": False,
                    "response_time": elapsed,
                    "error": str(e),
                    "_checked_at": now
                }
        
        # Concurrent check
        with ThreadPoolExecutor(max_workers=len(SOURCES)) as executor:
            futures = {executor.submit(check_source, name): name for name in SOURCES}
            
            # Total timeout for the batch
            batch_timeout = 8 if fast else 15
            try:
                for future in as_completed(futures, timeout=batch_timeout):
                    try:
                        result = future.result()
                        status.append(result)
                        # Update cache
                        self._health_cache[result["name"]] = result
                    except Exception as e:
                        name = futures.get(future, "unknown")
                        err_result = {
                            "name": name,
                            "available": False,
                            "response_time": batch_timeout,
                            "error": f"Timeout/Error: {str(e)}",
                            "_checked_at": now
                        }
                        status.append(err_result)
                        self._health_cache[name] = err_result
            except Exception as e:
                logger.warning(f"Source status check batch timeout: {e}")
        
        # Fill missing
        for name in SOURCES:
            if name not in [s["name"] for s in status]:
                status.append({
                    "name": name, 
                    "available": False, 
                    "response_time": 0, 
                    "error": "Not checked (batch timeout)",
                    "_checked_at": now
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
        
        fieldnames = ["timestamp", "temperature", "humidity", "precipitation", "wind_speed", "source", "lat", "lon"]
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
                "source": data.get("source", "unknown"),
                "lat": data.get("lat"),
                "lon": data.get("lon")
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