"""Data pipeline - main orchestration script."""
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from domain.entities.weather import WeatherData
from domain.interfaces.sources import WeatherDataSource, DataStorage

from infrastructure import (
    OpenMeteoAdapter,
    SourceRegistry,
    initialize_default_sources,
    CSVStorageAdapter,
    WeatherDataProcessor,
    DataQualityAnalyzer,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataPipeline:
    """
    Orchestrates the data pipeline:
    1. Extract - Fetch data from sources
    2. Transform - Normalize and clean data
    3. Load - Store data
    """
    
    def __init__(
        self,
        sources: list[WeatherDataSource],
        storage: DataStorage,
        processor: WeatherDataProcessor
    ):
        self.sources = sources
        self.storage = storage
        self.processor = processor
    
    async def run_current(
        self,
        latitude: float,
        longitude: float,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """Run pipeline for current weather data."""
        logger.info(f"Running pipeline for: {latitude}, {longitude}")
        
        all_data: list[WeatherData] = []
        
        for source in self.sources:
            try:
                logger.info(f"Fetching from {source.name}...")
                data = await source.fetch_current(latitude, longitude, timezone)
                
                # Store raw data
                await self.storage.save_raw(
                    {"source": source.name, "data": [d.model_dump() for d in data]},
                    source.name,
                    datetime.now()
                )
                
                all_data.extend(data)
                logger.info(f"Fetched {len(data)} records from {source.name}")
                
            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
        
        # Validate and clean
        cleaned, issues = self.processor.validate(all_data)
        if issues:
            logger.warning(f"Validation issues: {issues}")
        
        # Store cleaned data
        if cleaned:
            await self.storage.save_cleaned(cleaned)
            logger.info(f"Stored {len(cleaned)} cleaned records")
        
        return cleaned
    
    async def run_historical(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """Run pipeline for historical data."""
        logger.info(f"Historical pipeline: {start_date} to {end_date}")
        
        all_data: list[WeatherData] = []
        
        for source in self.sources:
            if not hasattr(source, 'fetch_historical'):
                continue
            
            try:
                logger.info(f"Fetching historical from {source.name}...")
                data = await source.fetch_historical(
                    latitude, longitude, start_date, end_date, timezone
                )
                all_data.extend(data)
                
            except Exception as e:
                logger.error(f"Error fetching historical from {source.name}: {e}")
        
        # Process and store
        cleaned, _ = self.processor.validate(all_data)
        
        if cleaned:
            await self.storage.save_cleaned(cleaned)
        
        return cleaned
    
    async def run_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 7,
        timezone: str = "America/Bogota"
    ) -> list[WeatherData]:
        """Run pipeline for forecast data."""
        logger.info(f"Forecast pipeline: {days} days")
        
        all_data: list[WeatherData] = []
        
        for source in self.sources:
            try:
                data = await source.fetch_forecast(latitude, longitude, days, timezone)
                all_data.extend(data)
            except Exception as e:
                logger.error(f"Error fetching forecast from {source.name}: {e}")
        
        return all_data
    
    def analyze_data(self, data: list[WeatherData]) -> dict:
        """Generate quality analysis of data."""
        analyzer = DataQualityAnalyzer()
        return analyzer.analyze(data)


async def main():
    """Main entry point for data pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ClimAPI Data Pipeline")
    parser.add_argument("--lat", type=float, default=6.244, help="Latitude")
    parser.add_argument("--lon", type=float, default=-75.581, help="Longitude")
    parser.add_argument("--days", type=int, default=7, help="Forecast days")
    parser.add_argument("--mode", choices=["current", "historical", "forecast"], default="current")
    parser.add_argument("--start-date", help="Start date for historical (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for historical (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    # Initialize
    initialize_default_sources()
    sources = [OpenMeteoAdapter()]
    storage = CSVStorageAdapter()
    processor = WeatherDataProcessor()
    
    pipeline = DataPipeline(sources, storage, processor)
    
    # Run
    if args.mode == "current":
        data = await pipeline.run_current(args.lat, args.lon)
    elif args.mode == "forecast":
        data = await pipeline.run_forecast(args.lat, args.lon, args.days)
    else:
        start = datetime.fromisoformat(args.start_date) if args.start_date else datetime.now() - timedelta(days=30)
        end = datetime.fromisoformat(args.end_date) if args.end_date else datetime.now()
        data = await pipeline.run_historical(args.lat, args.lon, start, end)
    
    # Analyze
    if data:
        report = pipeline.analyze_data(data)
        print(f"\nData Quality Report:")
        print(f"  Total records: {report['summary']['total_records']}")
        print(f"  Quality: {report['summary']['overall_quality']}")
        print(f"  Missing data: {report['summary']['missing_data_percent']}%")


if __name__ == "__main__":
    asyncio.run(main())