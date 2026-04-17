# 🌤️ ClimAPI - Sistema de Datos Meteorológicos

Proyecto completo en Python para consumir datos meteorológicos desde múltiples APIs públicas y visualizarlos en un dashboard interactivo o mediante una API REST.

## 📋 Descripción

ClimAPI es un sistema robusto de procesamiento de datos meteorológicos que:
- Consume datos de múltiples APIs meteorológicas (Open-Meteo, OpenWeatherMap, MeteoBlue, SIATA, IDEAM)
- Procesa, normaliza y valida datos con Pandas
- Proporciona una API REST con FastAPI
- Visualiza datos en un dashboard interactivo con Streamlit
- Sistema de caché para optimizar rendimiento
- Reportes de calidad de datos

## 🗂️ Estructura del Proyecto

```
ClimAPI/
├── api/
│   ├── __init__.py
│   ├── config.py
│   ├── dependencies.py
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       ├── locations.py
│       └── weather.py
│
├── data_sources/
│   ├── __init__.py
│   ├── base.py
│   ├── base_source.py
│   ├── meteoblue.py
│   ├── nsrdb_nasa.py
│   ├── open_meteo.py
│   ├── openweathermap.py
│   ├── power_larc.py
│   ├── radar_ideam.py
│   ├── reimagine_energy.py
│   └── siata.py
│
├── processing/
│   ├── __init__.py
│   ├── api_data_extractors.py
│   ├── data_diagnostics.py
│   ├── data_normalizer.py
│   ├── data_processor.py
│   ├── data_quality_report.py
│   ├── storage.py
│   └── transform.py
│
├── dashboard/
│   ├── __init__.py
│   └── app.py
│
├── config/
│   └── settings.py
│
├── scripts/
│   ├── __init__.py
│   └── ipynb_analyzer.py
│
├── tests/
│   ├── __init__.py
│   └── [archivos de pruebas]
│
├── app/
│   ├── config.py
│   └── services/
│       └── base.py
│
├── data/                     # Directorio para datos (creado automáticamente)
├── cache/                   # Directorio para caché (creado automáticamente)
├── main.py                  # API FastAPI + script de procesamiento
├── requirements.txt         # Dependencias del proyecto
└── README.md
```

## 🚀 Instalación

1. **Clonar o descargar el proyecto**

2. **Crear un entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   ```

3. **Activar el entorno virtual**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

4. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

5. **Configurar variables de entorno (opcional)**
   Crear un archivo `.env` con las API keys necesarias:
   ```env
   OPENWEATHER_API_KEY=tu_api_key
   METEOBLUE_API_KEY=tu_api_key
   METEOBLUE_SHARED_SECRET=tu_shared_secret
   CACHE_TTL_MINUTES=15
   ```

## 📖 Uso

### Modo 1: API FastAPI

Ejecutar el servidor API:
```bash
python main.py api
```

El servidor se iniciara en `http://localhost:8000`

Documentación interactiva disponible en:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Modo 2: Dashboard Streamlit

Ejecutar el dashboard:
```bash
streamlit run dashboard/app.py
```

El dashboard se abrirá en `http://localhost:8501`

### Modo 3: Script de Procesamiento

Ejecutar el pipeline de datos completo:
```bash
python main.py
```

Este script:
- Extrae datos de múltiples APIs
- Combina y normaliza los datos
- Valida y repara calidad de datos
- Genera reporte de calidad
- Guarda datos en CSV

### Endpoints Principales

| Endpoint | Descripción |
|----------|-------------|
| `GET /` | Información básica de la API |
| `GET /api/v1/health` | Estado de salud de la API |
| `POST /api/v1/weather/current` | Datos meteorológicos actuales |
| `GET /api/v1/weather/meteoblue` | Datos de MeteoBlue |
| `GET /api/v1/weather/openweathermap` | Datos de OpenWeatherMap |
| `GET /api/v1/locations/default` | Ubicación por defecto (Medellín) |
| `GET /api/v1/cache/stats` | Estadísticas de caché |
| `DELETE /api/v1/cache` | Limpiar caché |

## 🎯 Características del Dashboard

- **Gráficos interactivos** con Plotly:
  - Temperatura (°C)
  - Humedad Relativa (%)
  - Precipitación (mm)
  - Velocidad del Viento (km/h)

- **Filtros de fecha**: Selecciona rangos de fechas específicos

- **Estadísticas generales**: Métricas clave en sidebar

- **Tabla de datos**: Visualización detallada

- **Descarga de datos**: Exporta datos filtrados en CSV

## 🔧 Módulos del Proyecto

### `data_sources/`
- **open_meteo.py**: API gratuita de Open-Meteo
- **openweathermap.py**: OpenWeatherMap (requiere API key)
- **meteoblue.py**: MeteoBlue (requiere API key)
- **siata.py**: Datos del SIATA (Medellín)
- **radar_ideam.py**: Datos del RADAR IDEAM

### `processing/`
- **transform.py**: Transformación de datos JSON a DataFrame
- **storage.py**: Guardado/carga de CSV y gestión de caché
- **data_normalizer.py**: Normalización y combinación de fuentes
- **data_diagnostics.py**: Diagnóstico y reparación de datos
- **data_quality_report.py**: Generación de reportes de calidad

### `main.py`
- API FastAPI completa con endpoints meteorológicos
- Pipeline de procesamiento de datos
- Sistema de caché integrado
- Configuración CORS para frontend

## 📊 Calidad de Datos

El sistema incluye validación y reporte de calidad:
- Detección de datos faltantes
- Reparación automática de valores inválidos
- Validación de esquema de datos
- Reportes en formato JSON

## 🔮 Expansión Futura

El proyecto es fácilmente expandible:
- **Nuevas fuentes**: Agregar módulos en `data_sources/`
- **Análisis avanzado**: Nueva carpeta `analysis/`
- **Base de datos**: Modificar `storage.py` para PostgreSQL/MongoDB
- **Alertas**: Implementar sistema de notificaciones

## 📝 Notas

- Open-Meteo es gratuita y no requiere API key
- OpenWeatherMap y MeteoBlue requieren API keys
- Datos por defecto: Medellín, Colombia (Lat: 6.244, Lon: -75.581)
- Sistema de caché configurable (por defecto 15 minutos)

## 🤝 Contribuciones

Puntos de expansión sugeridos:
- Nuevas fuentes de datos meteorológicos
- Mejoras en visualizaciones
- Análisis estadísticos
- Alertas meteorológicas

## 📄 Licencia

Proyecto de código abierto para uso educativo y personal.