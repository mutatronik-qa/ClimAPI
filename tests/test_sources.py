"""
Tests for sources.py - Data source functions
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.sources import (
    get_weather_open_meteo,
    get_weather_openweathermap,
    get_weather_meteoblue,
    get_weather_siata,
    get_weather_radar,
    SOURCES,
    PRIORITY,
    get_source
)


class TestSources:
    """Test data source functions."""

    @patch('backend.sources.httpx.Client')
    def test_open_meteo_success(self, mock_client):
        """Test Open-Meteo successful response."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "hourly": {
                "time": ["2024-01-01T12:00:00"],
                "temperature_2m": [25.0],
                "relative_humidity_2m": [60.0],
                "precipitation": [0.0],
                "wind_speed_10m": [5.0]
            }
        }
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        result = get_weather_open_meteo(6.24, -75.58)

        assert result["temperature"] == 25.0
        assert result["humidity"] == 60.0
        assert result["source"] == "open-meteo"
        assert result["error"] is None

    @patch('backend.sources.httpx.Client')
    def test_open_meteo_failure(self, mock_client):
        """Test Open-Meteo failure handling."""
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("Network error")

        result = get_weather_open_meteo(6.24, -75.58)

        assert result["source"] == "open-meteo"
        assert result["error"] == "Network error"
        assert result["temperature"] is None

    def test_openweathermap_no_api_key(self):
        """Test OpenWeatherMap without API key."""
        result = get_weather_openweathermap(6.24, -75.58)

        assert result["source"] == "openweathermap"
        assert "API key not set" in result["error"]

    def test_meteoblue_no_api_key(self):
        """Test MeteoBlue without API key."""
        result = get_weather_meteoblue(6.24, -75.58)

        assert result["source"] == "meteoblue"
        assert "API key not set" in result["error"]

    def test_siata_fallback(self):
        """Test SIATA fallback response."""
        result = get_weather_siata(6.24, -75.58)

        assert result["source"] == "siata"
        assert "no public API" in result.get("error", "")

    def test_radar_fallback(self):
        """Test radar fallback response."""
        result = get_weather_radar(6.24, -75.58)

        assert result["source"] == "ideam_radar"
        assert "requires pyart" in result.get("error", "")

    def test_sources_registry(self):
        """Test sources registry."""
        assert "open-meteo" in SOURCES
        assert "openweathermap" in SOURCES
        assert "meteoblue" in SOURCES
        assert "siata" in SOURCES
        assert "ideam-radar" in SOURCES

        assert len(SOURCES) == 5

    def test_priority_order(self):
        """Test priority ordering."""
        assert PRIORITY[0] == "open-meteo"  # Free, reliable
        assert "openweathermap" in PRIORITY
        assert "meteoblue" in PRIORITY

    def test_get_source_function(self):
        """Test get_source helper."""
        func = get_source("open-meteo")
        assert callable(func)

        func = get_source("nonexistent")
        assert func is None