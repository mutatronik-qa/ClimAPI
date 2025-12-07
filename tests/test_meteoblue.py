# Tests async básicos para MeteoBlueService._summarize_daily and get_forecast (mocked)
import pytest
import asyncio
from data_sources.meteoblue import MeteoBlueService

@pytest.mark.asyncio
async def test_summarize_daily_and_forecast(monkeypatch):
    config = {"api_key": "DUMMY", "base_url": "https://example.com", "ttl_seconds": 1}
    svc = MeteoBlueService(config)

    # fake hourly data
    hourly = [
        {"time": "2025-12-07T00:00:00", "temp": 10, "precip": 0},
        {"time": "2025-12-07T12:00:00", "temp": 15, "precip": 1},
        {"time": "2025-12-08T00:00:00", "temp": 12, "precip": 0}
    ]
    # mock _http_get to return structure that leads to hourly list
    async def fake_http_get(url, timeout=10):
        return {"hours": hourly}
    monkeypatch.setattr(svc, "_http_get", fake_http_get)

    res = await svc.get_forecast({"lat": 6.244, "lon": -75.581}, days=2)
    assert "days" in res
    assert isinstance(res["days"], list)
    assert any(d["date"] == "2025-12-07" for d in res["days"])