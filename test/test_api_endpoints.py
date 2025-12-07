# tests/test_api_endpoints.py
from fastapi.testclient import TestClient
from backend.app.mainback import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_current_weather_endpoint():
    response = client.get("/api/v1/weather/current?latitude=6.244&longitude=-75.581")
    assert response.status_code == 200
    data = response.json()
    assert 'data' in data
    assert 'source' in data