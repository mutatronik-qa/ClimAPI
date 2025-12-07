# Tests sync wrapper fetch_weather_sync (mock requests)
import requests
import pytest
from unittest.mock import MagicMock
import data_sources.meteoblue as mb_module

def test_fetch_weather_sync_success(monkeypatch):
    fake_json = {
        "hours": [
            {"time": "2025-12-07T00:00:00", "temp": 11},
            {"time": "2025-12-07T13:00:00", "temp": 16}
        ]
    }
    class FakeResp:
        def raise_for_status(self): return None
        def json(self): return fake_json

    def fake_get(url, timeout=12):
        return FakeResp()

    monkeypatch.setattr(requests, "get", fake_get)
    out = mb_module.fetch_weather_sync(6.244, -75.581, days=1)
    assert out["source"] == "meteoblue"
    assert "data" in out
    assert "days" in out["data"] or "raw" in out["data"]