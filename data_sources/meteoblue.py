"""
Cliente para la API de MeteoBlue.

MeteoBlue proporciona pronósticos meteorológicos de alta precisión basados
en modelos numéricos de predicción del tiempo.

Este módulo implementará el cliente para obtener pronósticos meteorológicos
detallados con múltiples días de anticipación.

Clases:
    MeteoBlueService: Cliente para MeteoBlue API (pendiente de implementación)

Características planificadas:
    - Pronósticos de 7-14 días
    - Datos horarios de temperatura, precipitación, viento
    - Modelos meteorológicos de alta resolución
    - Índices UV, visibilidad, etc.

API Documentation: https://www.meteoblue.com/en/weather-api

TODO: Implementar cliente cuando se configure API key de MeteoBlue
"""

"""
Módulo unificado MeteoBlue:
- MeteoBlueService: cliente async (aiohttp preferido, requests fallback en executor)
- fetch_weather_sync: wrapper sync para compatibilidad legacy
- caching: usa BaseService async; sync usa processing.storage.CacheManager si existe
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import hashlib
import hmac
import logging
import urllib.parse
import asyncio

logger = logging.getLogger(__name__)

# Intentar usar aiohttp si está disponible para peticiones async
try:
    import aiohttp  # type: ignore
    HAS_AIOHTTP = True
except Exception:
    HAS_AIOHTTP = False

import requests

# Intentar importar BaseService (async cache helpers)
try:
    from app.services.base import BaseService
except Exception:
    class BaseService:  # type: ignore
        def __init__(self, config: Dict[str, Any]):
            self.config = config or {}
            self._default_ttl = int(self.config.get("ttl_seconds", 900))
        async def _get_cache(self, key: str) -> Optional[Any]:
            return None
        async def _set_cache(self, key: str, value: Any, ttl: Optional[int] = None):
            return

# Intentar usar processing.storage.CacheManager para cache sync (fallback local)
_SYNC_CACHE_MANAGER = None
try:
    from processing.storage import CacheManager  # type: ignore
    _SYNC_CACHE_MANAGER = CacheManager(ttl_minutes=15, cache_dir="cache")
    logger.debug("Usando processing.storage.CacheManager para cache sync")
except Exception:
    _SYNC_LOCAL_CACHE: Dict[str, Dict[str, Any]] = {}
    logger.debug("No se encontró processing.storage.CacheManager; usando cache sync local")

def _sync_cache_get(key: str) -> Optional[Any]:
    if _SYNC_CACHE_MANAGER is not None:
        mem = getattr(_SYNC_CACHE_MANAGER, "memory_cache", {})
        entry = mem.get(key)
        return entry[0] if entry else None
    entry = _SYNC_LOCAL_CACHE.get(key)
    if not entry:
        return None
    if datetime.utcnow().timestamp() > entry["expires_at"]:
        del _SYNC_LOCAL_CACHE[key]
        return None
    return entry["data"]

def _sync_cache_set(key: str, value: Any, ttl_seconds: int = 900):
    if _SYNC_CACHE_MANAGER is not None:
        _SYNC_CACHE_MANAGER.memory_cache[key] = (value, datetime.utcnow())
        return
    _SYNC_LOCAL_CACHE[key] = {
        "data": value,
        "expires_at": datetime.utcnow().timestamp() + ttl_seconds
    }

class MeteoBlueService(BaseService):
    """
    Cliente MeteoBlue unificado.
    Config keys:
      - api_key, base_url, endpoint, shared_secret, ttl_seconds, forecast_days
    """
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url: str = config.get("base_url", "https://my.meteoblue.com")
        self.api_key: Optional[str] = config.get("api_key")
        self.shared_secret: Optional[str] = config.get("shared_secret")
        self.endpoint: str = config.get("endpoint", "/packages/basic-1h")

    def _build_signed_url(self, query_params: Dict[str, Any]) -> str:
        query = urllib.parse.urlencode(query_params)
        path_and_query = f"{self.endpoint}?{query}"
        if self.shared_secret:
            sig = hmac.new(self.shared_secret.encode(), path_and_query.encode(), hashlib.sha256).hexdigest()
            signed = f"{self.base_url}{path_and_query}&sig={sig}"
        else:
            signed = f"{self.base_url}{path_and_query}"
        return signed

    async def _http_get(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Ejecuta petición GET usando requests en executor (sync) para simplificar compatibilidad.
        aiohttp se usa solo en get_current cuando está disponible.
        """
        loop = asyncio.get_running_loop()
        def sync_get():
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.json()
        return await loop.run_in_executor(None, sync_get)

    def _summarize_daily(self, hourly_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        by_day: Dict[str, Dict[str, float]] = {}
        for rec in hourly_records:
            t = rec.get("time") or rec.get("timestamp") or rec.get("date")
            if not t:
                continue
            try:
                ts = datetime.fromisoformat(t)
            except Exception:
                # intentar parse flex (sin zona)
                try:
                    ts = datetime.strptime(t, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
            day = ts.date().isoformat()
            temp = rec.get("temp") or rec.get("temperature") or rec.get("t")
            precip = rec.get("precip") or rec.get("precipitation") or rec.get("p")
            if temp is None:
                continue
            entry = by_day.setdefault(day, {"temp_min": float("inf"), "temp_max": float("-inf"), "precipitation": 0.0})
            try:
                valt = float(temp)
                entry["temp_min"] = min(entry["temp_min"], valt)
                entry["temp_max"] = max(entry["temp_max"], valt)
            except Exception:
                pass
            try:
                entry["precipitation"] += float(precip or 0.0)
            except Exception:
                pass
        days = []
        for day, vals in sorted(by_day.items()):
            if vals["temp_min"] == float("inf"):
                continue
            days.append({
                "date": day,
                "temp_min": vals["temp_min"],
                "temp_max": vals["temp_max"],
                "precipitation": vals["precipitation"],
                "description": ""
            })
        return days

    async def get_forecast(self, location: Dict[str, Any], days: int = 7) -> Dict[str, Any]:
        lat = location.get("lat") or location.get("latitude")
        lon = location.get("lon") or location.get("longitude")
        if lat is None or lon is None:
            raise ValueError("location debe contener 'lat' y 'lon'")

        cache_key = f"meteoblue:forecast:{lat}:{lon}:{days}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        params = {
            "lat": lat,
            "lon": lon,
            "apikey": self.api_key or "",
            "expire": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            "format": "json"
        }
        if "forecast_days" in self.config:
            params["forecast_days"] = int(min(days, int(self.config.get("forecast_days", days))))

        url = self._build_signed_url(params)
        try:
            resp = await self._http_get(url)
        except Exception as e:
            logger.error(f"Error petición MeteoBlue forecast: {e}")
            raise

        hourly = []
        if isinstance(resp, dict):
            # heurísticas para detectar lista hourly
            if "hours" in resp and isinstance(resp["hours"], list):
                hourly = resp["hours"]
            elif "data" in resp and isinstance(resp["data"], list):
                hourly = resp["data"]
            elif "hourly" in resp and isinstance(resp["hourly"], list):
                hourly = resp["hourly"]
            else:
                for v in resp.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict) and ("time" in v[0] or "timestamp" in v[0]):
                        hourly = v
                        break

        if not hourly:
            result = {"location_id": location.get("id") or f"{lat},{lon}", "source": "meteoblue", "raw": resp}
            await self._set_cache(cache_key, result, ttl=self._default_ttl)
            return result

        days_summary = self._summarize_daily(hourly)
        result = {"location_id": location.get("id") or f"{lat},{lon}", "source": "meteoblue", "days": days_summary}
        await self._set_cache(cache_key, result, ttl=self._default_ttl)
        return result

    async def get_current(self, location: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene estado actual. Usa aiohttp si está disponible para menor latencia async;
        si falla, usa requests en executor.
        """
        lat = location.get("lat") or location.get("latitude")
        lon = location.get("lon") or location.get("longitude")
        if lat is None or lon is None:
            raise ValueError("location debe contener 'lat' y 'lon'")

        cache_key = f"meteoblue:current:{lat}:{lon}"
        cached = await self._get_cache(cache_key)
        if cached:
            return cached

        params = {"lat": lat, "lon": lon, "apikey": self.api_key or "", "format": "json"}
        url = self._build_signed_url(params)

        # async aiohttp path
        if HAS_AIOHTTP:
            try:
                timeout = aiohttp.ClientTimeout(total=12)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(url) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        period = {}
                        if isinstance(data, dict):
                            if "forecast" in data and isinstance(data["forecast"].get("periods", []), list):
                                period = data["forecast"]["periods"][0] if data["forecast"]["periods"] else {}
                            elif "hours" in data and isinstance(data["hours"], list):
                                period = data["hours"][0] if data["hours"] else {}
                        processed = {
                            "timestamp": period.get("time") or datetime.utcnow().isoformat(),
                            "temperature": period.get("temperature") or period.get("temp"),
                            "humidity": period.get("humidity"),
                            "description": period.get("symbol") or "",
                            "source": "meteoblue",
                            "raw": data,
                            "location": f"{lat},{lon}"
                        }
                        await self._set_cache(cache_key, processed, ttl=self._default_ttl)
                        return processed
            except Exception as e:
                logger.debug(f"aiohttp failed for meteoblue current: {e}")

        # fallback sync via requests in executor
        try:
            resp = await self._http_get(url)
        except Exception as e:
            logger.error(f"Error petición MeteoBlue current: {e}")
            raise

        period = {}
        if isinstance(resp, dict):
            if "forecast" in resp and isinstance(resp["forecast"].get("periods", []), list):
                period = resp["forecast"]["periods"][0] if resp["forecast"]["periods"] else {}
            elif "hours" in resp and isinstance(resp["hours"], list):
                period = resp["hours"][0] if resp["hours"] else {}
        processed = {
            "timestamp": period.get("time") or datetime.utcnow().isoformat(),
            "temperature": period.get("temperature") or period.get("temp"),
            "humidity": period.get("humidity"),
            "description": period.get("symbol") or "",
            "source": "meteoblue",
            "raw": resp,
            "location": f"{lat},{lon}"
        }
        await self._set_cache(cache_key, processed, ttl=self._default_ttl)
        return processed

# --- Wrappers y compatibilidad sync --------------------------------------------------

# wrapper import compat: permite exponer DEFAULT_CONFIG si existe
try:
    from app.services import meteoblue as _mb_module  # type: ignore
except Exception:
    try:
        from backend.app.services import meteoblue as _mb_module  # type: ignore
    except Exception:
        _mb_module = None

def fetch_weather_sync(lat: float, lon: float, days: int = 1) -> Dict[str, Any]:
    cache_key = f"meteoblue:sync:{lat}:{lon}:{days}"
    cached = _sync_cache_get(cache_key)
    if cached:
        return {"source": "meteoblue", "data": cached, "cached": True}

    base_url = None
    api_key = None
    shared_secret = None
    endpoint = "/packages/basic-1h"
    if _mb_module and hasattr(_mb_module, "DEFAULT_CONFIG"):
        cfg = getattr(_mb_module, "DEFAULT_CONFIG")
        base_url = cfg.get("base_url")
        api_key = cfg.get("api_key")
        shared_secret = cfg.get("shared_secret")
        endpoint = cfg.get("endpoint", endpoint)

    if base_url is None:
        import os
        base_url = os.getenv("METEOBLUE_BASE_URL", "https://my.meteoblue.com")
        api_key = api_key or os.getenv("METEOBLUE_API_KEY")
        shared_secret = shared_secret or os.getenv("METEOBLUE_SHARED_SECRET")

    params = {
        "lat": lat,
        "lon": lon,
        "apikey": api_key or "",
        "expire": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        "format": "json"
    }
    q = urllib.parse.urlencode(params)
    path_and_query = f"{endpoint}?{q}"
    if shared_secret:
        sig = hmac.new(shared_secret.encode(), path_and_query.encode(), hashlib.sha256).hexdigest()
        url = f"{base_url}{path_and_query}&sig={sig}"
    else:
        url = f"{base_url}{path_and_query}"

    try:
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        resp = r.json()

        hourly = []
        if isinstance(resp, dict):
            if "hours" in resp and isinstance(resp["hours"], list):
                hourly = resp["hours"]
            elif "data" in resp and isinstance(resp["data"], list):
                hourly = resp["data"]
            elif "hourly" in resp and isinstance(resp["hourly"], list):
                hourly = resp["hourly"]
            else:
                for v in resp.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict) and ("time" in v[0] or "timestamp" in v[0]):
                        hourly = v
                        break

        if not hourly:
            result = {"location": f"{lat},{lon}", "source": "meteoblue", "raw": resp}
            _sync_cache_set(cache_key, result, ttl_seconds=3600)
            return {"source": "meteoblue", "data": result, "cached": False}

        by_day = {}
        for rec in hourly:
            t = rec.get("time") or rec.get("timestamp") or rec.get("date")
            if not t:
                continue
            try:
                ts = datetime.fromisoformat(t)
            except Exception:
                continue
            day = ts.date().isoformat()
            temp = rec.get("temp") or rec.get("temperature")
            precip = rec.get("precip") or rec.get("precipitation") or 0.0
            if temp is None:
                continue
            ent = by_day.setdefault(day, {"temp_min": float("inf"), "temp_max": float("-inf"), "precipitation": 0.0})
            try:
                vt = float(temp)
                ent["temp_min"] = min(ent["temp_min"], vt)
                ent["temp_max"] = max(ent["temp_max"], vt)
            except Exception:
                pass
            try:
                ent["precipitation"] += float(precip or 0.0)
            except Exception:
                pass

        days = []
        for d, v in sorted(by_day.items()):
            if v["temp_min"] == float("inf"):
                continue
            days.append({"date": d, "temp_min": v["temp_min"], "temp_max": v["temp_max"], "precipitation": v["precipitation"]})
        result = {"location": f"{lat},{lon}", "source": "meteoblue", "days": days}
        _sync_cache_set(cache_key, result, ttl_seconds=3600)
        return {"source": "meteoblue", "data": result, "cached": False}
    except requests.RequestException as e:
        logger.error(f"fetch_weather_sync error: {e}")
        return {"source": "meteoblue", "error": str(e)}