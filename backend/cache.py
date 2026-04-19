"""
Simple Cache - Extracted from weather_service.py
"""
import time
from typing import Dict, Any, Optional


class SimpleCache:
    """Simple TTL cache with optimized retention."""

    def __init__(self, default_ttl: int = 1800):
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

    def stats(self) -> Dict[str, Any]:
        return {"entries": len(self._cache)}