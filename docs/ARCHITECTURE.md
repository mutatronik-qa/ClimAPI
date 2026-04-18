"""
Architecture Overview - ClimAPI Refactoring

## NEW ARCHITECTURE: Clean Architecture with Hexagonal Design

### Layer Structure:

1. DOMAIN (Core) - Pure business logic, no external dependencies
   ├── entities/       - WeatherData, Location, Source data models
   ├── interfaces/     - Abstract base classes (ports)
   │                   - WeatherDataSource (port for data providers)
   │                   - CacheProvider (port for caching)
   │                   - DataProcessor (port for processing)
   └── value_objects/  - Temperature, Coordinates, etc.

2. APPLICATION (Use Cases) - Orchestration layer
   ├── use_cases/      - Business operations
   │   ├── get_current_weather.py
   │   ├── get_historical_weather.py
   │   ├── combine_weather_sources.py
   │   └── generate_quality_report.py
   └── services/       - Application services

3. INFRASTRUCTURE (Adapters) - External implementations
   ├── adapters/      - Implementations of domain interfaces
   │   ├── sources/   - API clients (Open-Meteo, OWM, MeteoBlue, etc.)
   │   ├── cache/     - File/Redis cache implementations
   │   └── storage/   - CSV/Parquet persistence
   └── repositories/   - Data access implementations

4. INTERFACE (API & UI)
   ├── api/           - FastAPI routes (clean, minimal)
   │   ├── routes/    - /weather, /locations, /sources
   │   ├── deps/      - Dependency injection
   │   └── models/    - Pydantic request/response models
   └── dashboard/     - Streamlit UI (completely separated)

5. DATA PIPELINE (ETL)
   ├── ingestion/     - Data extraction from sources
   ├── processing/    - Transform, normalize, validate
   └── storage/       - Raw + cleaned data storage

6. LABORATORY (Data Exploration)
   ├── analysis/      - Analysis functions
   ├── notebooks/     - Jupyter helpers
   └── metrics/       - Data quality metrics

7. SHARED
   ├── config/        - Settings and environment
   ├── utils/         - Helpers, validators
   └── exceptions/    - Custom exceptions

## KEY DESIGN PRINCIPLES

### SOLID:
- S: Each use case has single responsibility
- O: New sources added without modifying existing code
- L: Entities interchangeable via interfaces
- I: Small, focused interfaces
- D: Dependencies injected, not hardcoded

### OPEN/CLOSED:
- New sources: Create class implementing WeatherDataSource
- No modification to core logic needed

### DEPENDENCY INJECTION:
- FastAPI Depends() for API layer
- Factory pattern for adapters
- Configuration via settings

## PERFORMANCE IMPROVEMENTS

1. Async/await throughout (httpx instead of requests)
2. Background tasks for heavy processing
3. Caching with TTL per data type
4. Lazy loading in dashboard
5. Non-blocking UI with proper caching

## DATA NORMALIZATION

All sources normalized to unified schema:
{
    "timestamp": ISO8601,
    "temperature": float (°C),
    "humidity": float (%),
    "precipitation": float (mm),
    "wind_speed": float (km/h),
    "source": str
}

## EXTENSIBILITY

Adding new source:
1. Create adapter in infrastructure/adapters/sources/
2. Implement WeatherDataSource interface
3. Register in source registry
4. Available immediately via API

## MIGRATION PATH

Phase 1: Create new structure (domain, application, interfaces)
Phase 2: Move/refactor data sources as adapters
Phase 3: Refactor API to use use cases
Phase 4: Refactor dashboard to use API
Phase 5: Add laboratory module
Phase 6: Add tests and documentation
"""

README_ARCHITECTURE = """
# ClimAPI - Weather Dashboard Architecture

## Quick Start

```bash
# Run API
python -m api.main

# Run Dashboard
streamlit run dashboard/app.py

# Run Data Pipeline
python -m data_pipeline.main
```

## Project Structure

```
climapi/
├── domain/           # Core business logic
├── application/      # Use cases
├── infrastructure/   # External adapters
├── api/              # FastAPI interface
├── dashboard/        # Streamlit UI
├── data_pipeline/    # ETL processes
├── laboratory/       # Data exploration
└── shared/           # Config, utils
```

## Architecture

See ARCHITECTURE.md for full details.
"""