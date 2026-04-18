"""
Tests for weather_service.py - Single source of truth
"""
import pytest
from unittest.mock import patch, MagicMock
from backend.weather_service import WeatherService, get_service
from backend.sources import SOURCES


class TestWeatherService:
    """Test WeatherService class."""

    def test_init(self):
        """Test service initialization."""
        service = WeatherService(cache_ttl=300)
        assert service.default_ttl == 300
        assert service.cache is not None

    def test_get_weather_single_source(self):
        """Test getting weather from single source."""
        service = WeatherService()

        # Mock the source function
        mock_result = {
            "temperature": 25.0,
            "humidity": 60.0,
            "source": "test"
        }

        with patch.object(service, '_call_source') as mock_call:
            mock_call.return_value = mock_result

            result = service.get_weather(6.24, -75.58, source="test", use_cache=False)

            assert result["temperature"] == 25.0
            assert result["humidity"] == 60.0
            assert result["source"] == "test"

    def test_get_weather_all_sources(self):
        """Test getting weather from all sources."""
        service = WeatherService()

        # Mock sources
        mock_results = [
            {"temperature": 25.0, "source": "source1"},
            {"temperature": None, "source": "source2", "error": "failed"},
            {"temperature": 26.0, "source": "source3"}
        ]

        with patch.object(service, '_call_all_sources') as mock_call_all:
            mock_call_all.return_value = {
                "temperature": 25.0,
                "source": "source1",
                "all_sources": mock_results
            }

            result = service.get_weather(6.24, -75.58, use_cache=False)

            assert result["temperature"] == 25.0
            assert "all_sources" in result

    def test_cache_usage(self):
        """Test cache functionality."""
        service = WeatherService(cache_ttl=1)  # 1 second TTL

        # First call should cache
        with patch.object(service, '_call_source') as mock_call:
            mock_call.return_value = {"temperature": 25.0, "source": "test"}

            result1 = service.get_weather(6.24, -75.58, source="test", use_cache=True)
            assert result1["temperature"] == 25.0

            # Second call should use cache
            result2 = service.get_weather(6.24, -75.58, source="test", use_cache=True)
            assert result2["temperature"] == 25.0

            # Should only call source once
            assert mock_call.call_count == 1

    def test_sources_status(self):
        """Test getting sources status."""
        service = WeatherService()

        with patch('backend.sources.get_source') as mock_get_source:
            # Mock successful source
            mock_get_source.return_value = lambda lat, lon, **kwargs: {"temperature": 25.0}

            status = service.get_sources_status()

            assert len(status) == len(SOURCES)
            assert all("name" in s for s in status)
            assert all("available" in s for s in status)

    def test_save_data(self):
        """Test data saving functionality."""
        service = WeatherService()

        test_data = {
            "temperature": 25.0,
            "source": "test",
            "timestamp": "2024-01-01T00:00:00"
        }

        # This should not raise an exception
        service.save_data(test_data)


def test_get_service():
    """Test global service instance."""
    service = get_service()
    assert isinstance(service, WeatherService)

    # Should return same instance
    service2 = get_service()
    assert service is service2