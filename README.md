# 🌤️ ClimAPI - Dashboard Meteorológico

Proyecto en Python para obtener datos meteorológicos y visualizarlos en un dashboard interactivo.

## 📋 Descripción

ClimAPI consume datos de la API gratuita Open-Meteo y los visualiza en un dashboard Streamlit.

## 🗂️ Estructura

```
ClimAPI/
├── data_sources/     # Consumo de APIs meteorológicas
├── processing/    # Transformación y almacenamiento
├── dashboard/     # Dashboard Streamlit
├── config/       # Configuración
├── data/         # Datos CSV (generado automáticamente)
├── cache/        # Caché (generado automáticamente)
├── main.py       # Script principal
└── README.md
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

Dashboard en `http://localhost:8501`.

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

- Gráficos interactivos (Plotly): Temperatura, Humedad, Precipitación, Viento
- Filtros por rango de fechas
- Estadísticas generales
- Tabla de datos
- Descarga CSV

## 📦 Dependencies

- pandas, requests, streamlit, plotly
- fastapi, uvicorn, pydantic
- diskcache (caché)

## 📄 Licencia

Código abierto para uso educativo y personal.