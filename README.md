# 🌤️ ClimAPI

ClimAPI is a lightweight weather project with:
- a **FastAPI backend**
- a **Streamlit dashboard**
- a **single CLI** for debugging and data inspection
- a **single source of truth** in `backend/weather_service.py`

## ✅ Supported Weather Sources

- `open-meteo` — primary free source
- `openweathermap` — uses `OPENWEATHER_API_KEY`
- `meteosource` — uses `METEOSOURCE_API_KEY` and `https://www.meteosource.com/api/v1/free/point`
- `meteoblue` — uses `METEOBLUE_API_KEY`, package with `secret_share=climapi`
- `siata` — web scraping from `https://www.siata.gov.co/operacional/#`
- `ideam-radar` — uses `boto3` unsigned S3 access to `s3-radaresideam`

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure `.env`

Copy `.env` from your local file and make sure these keys exist:

```env
OPENWEATHER_API_KEY=your_openweathermap_key
METEOSOURCE_API_KEY=your_meteosource_key
METEOBLUE_API_KEY=your_meteoblue_key
SIATA_OPERACIONAL_URL=https://www.siata.gov.co/operacional/#
```

If you want radar metadata, install AWS CLI and use no-sign-request access.

### 3. Run the CLI

```bash
ClimAPI CLI - Weather data from command line

positional arguments:
  {current,sources,save,history,test-source,advanced}
                        Commands
    current             Get current weather
    sources             List all sources
    save                Save weather data
    history             Show historical data
    test-source         Test a specific source
    advanced            Advanced data using src/data_sources/ clients

options:
  -h, --help            show this help message and exit

Examples:
  python cli.py current --lat 6.24 --lon -75.58
  python cli.py current --lat 6.24 --lon -75.58 --all-sources
  python cli.py sources
  python cli.py save --lat 6.24 --lon -75.58
  python cli.py history
  python cli.py test-source open-meteo

  # Advanced (uses detailed src/data_sources/ clients)
  python cli.py advanced open-meteo --detail forecast --days 7
  python cli.py advanced open-meteo --detail historical --days 14
  python cli.py advanced openweather --detail current
  python cli.py advanced openweather --detail forecast
  python cli.py advanced openweather --detail air
  python cli.py advanced meteoblue --detail forecast
  python cli.py advanced meteoblue --detail meteogram

python cli.py current --lat 6.279552149570526 --lon -75.575345826297
python cli.py sources
python cli.py save --lat 6.279552149570526 --lon -75.575345826297
python cli.py history
```

### 4. Run the API

```bash
python main.py
```

Then open: `http://localhost:8000/docs`

### 5. Run the dashboard

```bash
streamlit run dashboard/app.py
```

### 6. Radar y SIATA

- Usa la nueva página **Radar + SIATA** en el menú lateral.
- El mapa ahora muestra los 4 radares IDEAM principales y el punto de búsqueda actual.
- SIATA muestra un historial local cuando hay datos guardados en `data/raw/siata.csv`.

## 📦 What changed

### `backend/sources.py`

- `openweathermap` now reads the API key from `.env`
- `meteosource` uses `METEOSOURCE_API_KEY` and the free point endpoint from `https://www.meteosource.com/api/v1/free/point`
- `meteoblue` uses the requested package:
  `basic-15min_basic-3h_current_clouds-1h_sunmoon_moonlight-30min`
- `siata` scrapes the operational page for weather values
- `ideam-radar` uses `boto3` unsigned access to list objects in `s3-radaresideam`

### `dashboard/app.py`

- imports the backend service directly
- uses caching to avoid freeze

## 🧪 CLI Commands

| Command | Description |
|---|---|
| `python cli.py current --lat <lat> --lon <lon>` | Get current weather | 
| `python cli.py sources` | List available sources | 
| `python cli.py save --lat <lat> --lon <lon>` | Save current weather and source history to `data/raw/` and `data/processed/weather.csv` | 
| `python cli.py history` | Show historical records | 
| `python cli.py test-source <source>` | Debug a specific source | 

## 🌍 Environment Variables

Required keys for best source coverage:

```env
OPENWEATHER_API_KEY=your_openweathermap_key
METEOBLUE_API_KEY=your_meteoblue_key
SIATA_OPERACIONAL_URL=https://www.siata.gov.co/operacional/#
```

Optional keys:

```env
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## 🔧 Notes

- `open-meteo` is the fallback free source.
- `openweathermap` and `meteoblue` are optional but improve coverage.
- `siata` is scraped from the operational page and may return partial values.
- `ideam-radar` returns metadata about the AWS S3 radar bucket.

## 🚨 Troubleshooting

- If `cli.py` fails, run from repository root: `cd e:\GIT\ClimAPI`
- If `dashboard` fails to import backend, run from the repo root
- If AWS radar fails, ensure AWS CLI is installed and reachable from PATH
