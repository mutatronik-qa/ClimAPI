# 🌤️ ClimAPI - Dashboard Meteorológico

Proyecto en Python para obtener datos meteorológicos y visualizarlos en un dashboard interactivo.

## 📋 Descripción

ClimAPI consume datos de la API gratuita Open-Meteo y los visualiza en un dashboard Streamlit.

## 🗂️ Estructura

```
ClimAPI/
├── api/           # Endpoints FastAPI
├── app/           # Configuración y servicios de la aplicación
├── data_sources/  # Consumo de APIs meteorológicas
├── processing/    # Transformación y almacenamiento de datos
├── dashboard/     # Dashboard Streamlit
├── config/        # Configuración centralizada
├── data/          # Datos CSV generados
├── notebooks/     # Jupyter notebooks de análisis
├── scripts/       # Scripts auxiliares
├── tests/         # Pruebas pytest
├── frontend/      # Frontend Next.js (opcional)
├── README.md
└── requirements.txt
```

## 🚀 Instalación

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 📖 Uso

### 1. Obtener datos (Terminal)

```bash
python main.py
```

Genera `data/weather_data.csv` con datos de Open-Meteo.

### 2. Dashboard (Streamlit)

```bash
python main.py dashboard
# o directamente:
streamlit run dashboard/app.py
```

Dashboard en `http://localhost:8501` con 4 páginas:
- **📊 Dashboard**: Gráficos y análisis de datos meteorológicos
- **🗺️ Mapa**: Visualización de radares IDEAM con capas GeoJSON
- **📓 Notebooks**: Análisis y extracción de datos desde notebooks Jupyter
- **⚙️ Configuración**: Gestión de API keys y credenciales

### 3. API FastAPI (Opcional)

```bash
python main.py api
```

API en `http://localhost:8000` (docs en `/docs`).

## ⚙️ Configuración

Editar `config/settings.py` o variables de entorno en `.env`:

```env
# Ubicación por defecto: Medellín
DEFAULT_LOCATION=medellin

#TTL de caché (minutos)
CACHE_TTL_MINUTES=15
```

Ubicaciones disponibles: medellin, bello, envigado, bogota

## 🎯 Características Dashboard

### 📊 Dashboard Principal
- Gráficos interactivos (Plotly): Temperatura, Humedad, Precipitación, Viento
- Filtros por rango de fechas
- Estadísticas generales
- Tabla de datos
- Descarga CSV
- Integración múltiple de APIs (Open-Meteo, OpenWeatherMap, MeteoBlue, RADAR IDEAM)

### 🗺️ Mapa Meteorológico
- Visualización de radares IDEAM en tiempo real
- Capas GeoJSON para límites geográficos
- Mapa interactivo centrado en Medellín
- Información de precipitación por radar

### ⚙️ Configuración de APIs
- Interfaz para configurar API keys (OpenWeatherMap, MeteoBlue)
- Gestión de URLs de servicios (SIATA, IDEAM)
- Validación y guardado seguro de credenciales
- Información de ayuda para obtener API keys

### 📓 Análisis de Notebooks
- Exploración automática de notebooks Jupyter (.ipynb)
- Extracción de URLs y datasets desde código Python
- Descarga segura de CSVs desde notebooks
- Clasificación de datos realtime/historical
- Estadísticas detalladas por notebook

## 📦 Dependencies

- fastapi, uvicorn, pydantic, pydantic-settings
- pandas, numpy, requests, bs4
- streamlit, plotly, folium, streamlit-folium
- diskcache, nbformat
- boto3, arm-pyart

## 🛠️ Dependencias de desarrollo

- pytest, pytest-asyncio, black, isort, mypy

## 🧪 Tests

```bash
# Instalar pytest si no está
pip install pytest pytest-asyncio

# Todos los tests
pytest tests/ -v

# Solo unit tests (transform, storage)
pytest tests/test_transform.py tests/test_storage.py -v

# Tests de API (usa TestClient, sin llamada real)
pytest tests/test_api_endpoints_v2.py -v

# Tests del dashboard (funciones auxiliares)
pytest tests/test_dashboard.py -v
```

O ejecutar scripts incluidos:
```bash
# Windows
run_tests.bat

# Linux/Mac
bash run_tests.sh
```

## � Cambios Recientes

### v1.0.1 - Abril 2026

#### ✅ Integración SIATA
- **Agregado**: Soporte completo para cliente SIATA (Sistema de Alerta Temprana de Medellín)
- **Configuración**: URL operativa `https://www.siata.gov.co/operacional/`
- **Uso**: Cliente SIATA ahora disponible en `main.py` y endpoints API

#### ✅ Corrección Radar IDEAM
- **Arreglado**: Error `boto3.UNSIGNED` → `botocore.UNSIGNED`
- **Compatibilidad**: Acceso público a bucket S3 de IDEAM funcionando correctamente

#### ✅ Seguridad y Configuración
- **Agregado**: Archivo `.gitignore` para proteger `.env` y archivos sensibles
- **Migrado**: Pydantic v1 → v2 (`pydantic_settings.BaseSettings`)
- **Corregido**: Parsing de `ALLOWED_ORIGINS` en `.env` (lista separada por comas)
- **Centralizado**: API keys ahora usan configuración centralizada en lugar de `os.getenv()`

#### ✅ Compatibilidad Windows
- **Agregado**: Función `_safe_timestamp()` para nombres de archivo válidos en Windows
- **Arreglado**: Error `[Errno 22] Invalid argument` al guardar archivos JSON

#### ✅ OpenWeatherMap HTTPS
- **Actualizado**: URL base cambiada de `http://` a `https://` (requerido por API)
- **Seguridad**: Todas las llamadas API ahora usan HTTPS

#### ✅ Web Scraping SIATA Histórico
- **Mejorado**: Cliente SIATA con scraping de datos históricos
- **Nuevo método**: `get_historical_weather(days=7)` para datos pasados
- **Integración**: Datos históricos junto con servicios gratuitos
- **Compatibilidad**: Fallback automático si scraping falla

## �📄 Licencia

Código abierto para uso educativo y personal.