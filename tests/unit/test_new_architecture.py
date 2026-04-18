"""Basic unit tests for the new architecture."""

import pytest
from datetime import datetime, timedelta

from domain.entities.weather import WeatherData, Location, WeatherSourceInfo
from domain.interfaces.sources import WeatherDataSource, CacheProvider

from infrastructure.adapters.sources.open_meteo import OpenMeteoAdapter
from infrastructure.adapters.cache.file_cache import MemoryCacheAdapter
from infrastructure.adapters.processing.weather_processor import WeatherDataProcessor

import asyncio


class TestWeatherData:
    """Tests for WeatherData entity."""
    
    def test_create_weather_data(self):
        """Test creating a WeatherData object."""
        data = WeatherData(
            timestamp=datetime.now(),
            temperature=25.5,
            humidity=60.0,
            precipitation=0.0,
            wind_speed=10.5,
            source="test"
        )
        
        assert data.temperature == 25.5
        assert data.humidity == 60.0
        assert data.source == "test"
    
    def test_weather_data_with_nulls(self):
        """Test WeatherData allows null values."""
        data = WeatherData(
            timestamp=datetime.now(),
            temperature=None,
            source="test"
        )
        
        assert data.temperature is None
        assert data.source == "test"


class TestLocation:
    """Tests for Location entity."""
    
    def test_valid_location(self):
        """Test creating a valid location."""
        loc = Location(
            latitude=6.244,
            longitude=-75.581,
            timezone="America/Bogota",
            name="Medellín"
        )
        
        assert loc.latitude == 6.244
        assert loc.longitude == -75.581
        assert loc.name == "Medellín"
    
    def test_invalid_latitude(self):
        """Test invalid latitude raises error."""
        with pytest.raises(ValueError):
            Location(latitude=100, longitude=0)
    
    def test_invalid_longitude(self):
        """Test invalid longitude raises error."""
        with pytest.raises(ValueError):
            Location(latitude=0, longitude=200)


class TestOpenMeteoAdapter:
    """Tests for Open-Meteo adapter."""
    
    @pytest.mark.asyncio
    async def test_adapter_properties(self):
        """Test adapter properties."""
        adapter = OpenMeteoAdapter()
        
        assert adapter.name == "open-meteo"
        assert adapter.info.display_name == "Open-Meteo"
        assert adapter.info.requires_api_key is False
        assert adapter.info.is_free is True
    
    @pytest.mark.asyncio
    async def test_fetch_current(self):
        """Test fetching current weather."""
        adapter = OpenMeteoAdapter()
        
        try:
            data = await adapter.fetch_current(6.244, -75.581, "America/Bogota")
            assert isinstance(data, list)
        except Exception:
            pytest.skip("API not available or network error")
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        adapter = OpenMeteoAdapter()
        
        result = await adapter.health_check()
        assert isinstance(result, bool)


class TestMemoryCache:
    """Tests for memory cache adapter."""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test setting and getting values."""
        cache = MemoryCacheAdapter(default_ttl=60)
        
        await cache.set("test_key", {"data": "test_value"}, ttl_seconds=60)
        value = await cache.get("test_key")
        
        assert value == {"data": "test_value"}
    
    @pytest.mark.asyncio
    async def test_get_missing_key(self):
        """Test getting non-existent key returns None."""
        cache = MemoryCacheAdapter()
        
        value = await cache.get("non_existent")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_expiry(self):
        """Test cache expiry."""
        cache = MemoryCacheAdapter(default_ttl=1)
        
        await cache.set("expiry_test", "value", ttl_seconds=1)
        
        # Wait for expiry
        await asyncio.sleep(1.1)
        
        value = await cache.get("expiry_test")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing cache."""
        cache = MemoryCacheAdapter()
        
        await cache.set("key1", "value1", ttl_seconds=60)
        await cache.set("key2", "value2", ttl_seconds=60)
        
        await cache.clear()
        
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None
    
    @pytest.mark.asyncio
    async def test_stats(self):
        """Test cache statistics."""
        cache = MemoryCacheAdapter()
        
        await cache.set("key", "value", ttl_seconds=60)
        await cache.get("key")  # hit
        await cache.get("missing")  # miss
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 50.0


class TestWeatherDataProcessor:
    """Tests for data processor."""
    
    def test_validate_valid_data(self):
        """Test validating valid data."""
        processor = WeatherDataProcessor()
        
        data = [
            WeatherData(
                timestamp=datetime.now(),
                temperature=25.0,
                humidity=60.0,
                precipitation=0.0,
                wind_speed=10.0,
                source="test"
            )
        ]
        
        cleaned, issues = processor.validate(data)
        
        assert len(cleaned) == 1
        assert len(issues) == 0
    
    def test_validate_invalid_temperature(self):
        """Test validation catches out-of-range temperature."""
        processor = WeatherDataProcessor()
        
        data = [
            WeatherData(
                timestamp=datetime.now(),
                temperature=100.0,  # Too high
                humidity=60.0,
                source="test"
            )
        ]
        
        cleaned, issues = processor.validate(data)
        
        assert len(issues) > 0
    
    def test_aggregate_hourly(self):
        """Test hourly aggregation."""
        processor = WeatherDataProcessor()
        
        now = datetime.now()
        data = [
            WeatherData(
                timestamp=now + timedelta(hours=i),
                temperature=20.0 + i,
                humidity=50.0,
                source="test"
            )
            for i in range(24)
        ]
        
        aggregated = processor.aggregate(data, "daily")
        
        assert len(aggregated) <= 2  # ~24 hours = 1-2 days


class TestDataQualityAnalyzer:
    """Tests for data quality analysis."""
    
    def test_analyze_empty_data(self):
        """Test analyzing empty data."""
        from infrastructure.adapters.processing.weather_processor import DataQualityAnalyzer
        
        analyzer = DataQualityAnalyzer()
        result = analyzer.analyze([])
        
        assert result["summary"]["total_records"] == 0
        assert result["summary"]["overall_quality"] == "no_data"
    
    def test_analyze_complete_data(self):
        """Test analyzing complete data."""
        from infrastructure.adapters.processing.weather_processor import DataQualityAnalyzer
        
        analyzer = DataQualityAnalyzer()
        
        data = [
            WeatherData(
                timestamp=datetime.now() + timedelta(hours=i),
                temperature=25.0,
                humidity=60.0,
                precipitation=0.0,
                wind_speed=10.0,
                source="test"
            )
            for i in range(10)
        ]
        
        result = analyzer.analyze(data)
        
        assert result["summary"]["total_records"] == 10
        assert result["summary"]["overall_quality"] in ["excellent", "good"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])