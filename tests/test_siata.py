# tests/test_siata.py
import pytest
from data_sources.siata import SIATAClient

def test_siata_client_initialization():
    config = {"api_url": "https://www.siata.gov.co"}
    client = SIATAClient(config)
    assert client.base_url == "https://www.siata.gov.co"

def test_siata_weather_current():
    config = {"api_url": "https://www.siata.gov.co"}
    client = SIATAClient(config)
    data = client.get_weather_current("medellin")
    # Verificar estructura básica
    if data:
        assert "timestamp" in data
        assert data.get("source") == "siata"

# tests/test_radar_ideam.py
from src.data_sources.radar_ideam import RadarIDEAMClient

def test_radar_list_scans():
    config = {"bucket": "s3-radaresideam", "region": "us-east-1"}
    client = RadarIDEAMClient(config)
    scans = client.list_available_scans(hours_back=3)
    assert isinstance(scans, list)

# Ejecutar tests
# pytest tests/ -v --cov=src --cov-report=html
