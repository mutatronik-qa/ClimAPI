# 🌤️ ClimAPI - Weather Dashboard v2.0

Clean Architecture weather API with multiple data sources.

## 🏗️ Architecture

This project follows **Clean Architecture** principles with proper separation of concerns:

```
climapi/
├── domain/                    # Core business logic (no dependencies)
│   ├── entities/              # WeatherData, Location, etc.
│   └── interfaces/            # Abstract base classes (ports)
├── application/               # Use cases (orchestration)
│   └── use_cases/             # GetCurrentWeather, CombineSources, etc.
├── infrastructure/             # External adapters
│   └── adapters/
│       ├── sources/           # API implementations (Open-Meteo, etc.)
│       ├── cache/             # Cache implementations
│       └── storage/           # CSV/Parquet storage
├── api/                       # FastAPI (clean routes)
├── dashboard/                 # Streamlit (non-blocking)
├── data_pipeline/             # ETL orchestration
├── laboratory/                # Data exploration module
├── shared/                    # Config, utils
├── docs/                      # Architecture & migration guides
└── tests/                     # Unit & integration tests
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run API

```bash
python -m api.main
# or
uvicorn api.main:app --reload
```

API docs: http://localhost:8000/docs

### 3. Run Dashboard

```bash
streamlit run dashboard/app.py
```

Dashboard: http://localhost:8501

### 4. Run Data Pipeline

```bash
python -m data_pipeline.main --lat 6.244 --lon -75.581 --mode current
```

## 📡 Available Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/health` | Health check |
| `GET /api/v1/sources` | List available sources |
| `POST /api/v1/weather/current` | Get current weather |
| `GET /api/v1/weather/forecast` | Get weather forecast |
| `GET /api/v1/weather/combined` | Combine multiple sources |
| `GET /api/v1/weather/quality` | Data quality report |
| `GET /api/v1/cache/stats` | Cache statistics |
| `DELETE /api/v1/cache` | Clear cache |

## 🌤️ Weather Sources

Priority (free, no API key):
- **Open-Meteo** - Primary source (free, no key)
- **IDEAM Radar** - Colombian radar data
- **NASA Power** - Solar/weather data

Optional (requires API key):
- OpenWeatherMap
- MeteoBlue
- SIATA

## 🔌 Adding New Sources

Create a new adapter following this pattern:

```python
# infrastructure/adapters/sources/new_source.py
from domain.entities.weather import WeatherData, WeatherSourceInfo
from domain.interfaces.sources import WeatherDataSource

class NewSourceAdapter(WeatherDataSource):
    @property
    def name(self) -> str:
        return "new-source"
    
    @property
    def info(self) -> WeatherSourceInfo:
        return WeatherSourceInfo(
            name="new-source",
            display_name="New Source",
            requires_api_key=True,
            is_free=False
        )
    
    async def fetch_current(self, lat, lon, timezone):
        # Implement async fetch
        pass
    
    # ... implement other required methods
```

Then register it:

```python
SourceRegistry.register(NewSourceAdapter())
```

## 📊 Laboratory Module

For data exploration in notebooks or scripts:

```python
from laboratory import create_laboratory

lab = create_laboratory()

# Load data
df = lab.load_cleaned_data()

# Get quality metrics
metrics = lab.get_quality_metrics(df)

# Export
lab.export_to_csv(df, "export.csv")
```

## 🐳 Docker

```bash
# Start all services
docker-compose up

# Or manually
docker build -t climapi .
docker run -p 8000:8000 climapi
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest --cov=. --cov-report=html

# Specific test file
pytest tests/unit/test_new_architecture.py -v
```

## 📁 Project Files

- `docs/ARCHITECTURE.md` - Detailed architecture explanation
- `docs/MIGRATION.md` - Migration guide from v1.0 to v2.0
- `.env.example` - Environment variables template
- `requirements.txt` - Python dependencies

## ⚙️ Configuration

Edit `.env` file:

```env
# Default location
DEFAULT_LATITUDE=6.244
DEFAULT_LONGITUDE=-75.581
DEFAULT_TIMEZONE=America/Bogota

# Cache settings
CACHE_BACKEND=memory
CACHE_TTL_CURRENT=900

# API Keys (optional)
# OPENWEATHER_API_KEY=your_key
# METEOBLUE_API_KEY=your_key
```

## 📖 Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Migration Guide](docs/MIGRATION.md)
- API docs at `/docs` when running

## License

Open source for educational and personal use.