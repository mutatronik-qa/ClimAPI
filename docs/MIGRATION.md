# Migration Guide - From v1.0 to v2.0

## Overview

This guide explains how to migrate from the old monolithic structure to the new Clean Architecture.

## Architecture Changes

### Before (v1.0)
```
climapi/
├── main.py                 # Everything in one file
├── data_sources/           # Mixed API clients
├── processing/             # ETL mixed together
├── api/                   # Minimal FastAPI
├── dashboard/             # Blocking dashboard
└── config/                # Basic settings
```

### After (v2.0)
```
climapi/
├── domain/                # Pure business logic
│   ├── entities/          # WeatherData, Location
│   └── interfaces/        # Abstract base classes
├── application/           # Use cases
│   └── use_cases/         # GetCurrentWeather, etc.
├── infrastructure/       # External adapters
│   ├── adapters/
│   │   ├── sources/       # API implementations
│   │   ├── cache/        # Cache implementations
│   │   └── storage/      # Storage implementations
├── api/                  # Clean FastAPI routes
├── dashboard/            # Non-blocking Streamlit
├── data_pipeline/        # ETL orchestration
├── laboratory/           # Data exploration
└── shared/               # Config, utils
```

## Step-by-Step Migration

### Step 1: Domain Layer

The domain layer is completely new. It defines:
- Entities (WeatherData, Location, etc.)
- Interfaces (WeatherDataSource, CacheProvider, etc.)

No changes needed - this is new code.

### Step 2: Move Data Sources to Adapters

**Before:**
```python
# data_sources/open_meteo.py
def get_weather_data(lat, lon):
    # sync requests
    return data
```

**After:**
```python
# infrastructure/adapters/sources/open_meteo.py
class OpenMeteoAdapter(WeatherDataSource):
    async def fetch_current(self, lat, lon, timezone):
        # async httpx
        return list[WeatherData]
```

### Step 3: Refactor API Routes

**Before:**
```python
# main.py
@app.get("/weather")
async def get_weather(location):
    data = get_weather_data(location.lat, location.lon)
    return process_weather_data(data)
```

**After:**
```python
# api/main.py
@app.get("/weather")
async def get_weather(
    location: LocationRequest,
    use_case: GetCurrentWeather = Depends()
):
    return await use_case.execute(location.lat, location.lon)
```

### Step 4: Update Dashboard

**Key changes:**
- Use `st.cache_data` for caching API calls
- Use `st.spinner` for non-blocking loading
- Fetch data from API instead of direct imports
- Add proper error handling

### Step 5: Update Configuration

**Before:**
```python
# config/settings.py
class Settings:
    OPENWEATHER_API_KEY = "..."
```

**After:**
```python
# .env
OPENWEATHER_API_KEY=...

# shared/config/settings.py
# Uses pydantic-settings with .env
```

## Running the New Architecture

### Start API
```bash
python -m api.main
# or
uvicorn api.main:app --reload
```

### Start Dashboard
```bash
streamlit run dashboard/app.py
```

### Run Data Pipeline
```bash
python -m data_pipeline.main --lat 6.244 --lon -75.581 --mode current
```

## Adding New Weather Sources

To add a new weather source (e.g., WeatherAPI):

1. Create adapter:
```python
# infrastructure/adapters/sources/weather_api.py
class WeatherAPIAdapter(WeatherDataSource):
    @property
    def name(self) -> str:
        return "weather-api"
    
    async def fetch_current(self, lat, lon, timezone):
        # implementation
        pass
```

2. Register in initialization:
```python
# somewhere in initialization
SourceRegistry.register(WeatherAPIAdapter())
```

3. Use immediately:
```bash
curl "http://localhost:8000/api/v1/weather/current?source_name=weather-api&latitude=6.244&longitude=-75.581"
```

## Using the Laboratory

```python
# In notebook or script
from laboratory import create_laboratory, load_weather_data

lab = create_laboratory()

# Load data
df = lab.load_cleaned_data()

# Get quality metrics
metrics = lab.get_quality_metrics(df)

# Export
lab.export_to_csv(df, "export.csv")
```

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest --cov=. --cov-report=html
```

## Troubleshooting

### Import Errors
Make sure the project root is in PYTHONPATH:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### API Connection Issues
Ensure the API is running:
```bash
python -m api.main
```

### Cache Issues
Clear the cache:
```bash
curl -X DELETE http://localhost:8000/api/v1/cache
```

## Breaking Changes

1. **No more sync data sources**: All data sources are now async
2. **Different response format**: API responses use new Pydantic models
3. **New endpoints**: Some endpoint paths have changed
4. **Dashboard requires API**: Dashboard now fetches from API, not direct imports

## Performance Improvements

1. **Async HTTP**: Using httpx instead of requests
2. **In-memory caching**: MemoryCacheAdapter for faster access
3. **Cached dashboard queries**: st.cache_data with proper TTL
4. **Parallel source fetching**: CombineWeatherSources fetches in parallel