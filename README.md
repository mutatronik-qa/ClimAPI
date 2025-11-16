# 🌤️ Proyecto ClimAPI - Dashboard Meteorológico

Proyecto completo en Python para consumir datos meteorológicos desde la API pública de Open-Meteo y visualizarlos en un dashboard interactivo.

## 📋 Descripción

Este proyecto permite:
- Consumir datos horarios del clima (temperatura, humedad, precipitación y velocidad del viento) desde Open-Meteo
- Procesar y transformar los datos con Pandas
- Guardar los datos en formato CSV
- Visualizar los datos en un dashboard interactivo con Streamlit

## 🗂️ Estructura del Proyecto

```
ClimAPI/
│
├── data_sources/
│   └── open_meteo.py          # Módulo para consumir la API de Open-Meteo
│
├── processing/
│   ├── transform.py            # Transformación y limpieza de datos
│   └── storage.py              # Guardado y carga de datos CSV
│
├── dashboard/
│   └── app.py                  # Dashboard interactivo con Streamlit
│
├── config/
│   └── settings.json           # Configuración del proyecto
│
├── data/                       # Directorio para almacenar datos CSV (se crea automáticamente)
│
├── main.py                     # Script principal que orquesta todo el flujo
├── requirements.txt            # Dependencias del proyecto
└── README.md                   # Este archivo
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

## 📖 Uso

### 1. Obtener y procesar datos

Ejecuta el script principal para consumir datos de la API, procesarlos y guardarlos:

```bash
python main.py
```

Este script:
- Obtiene datos meteorológicos para Medellín (configurado por defecto)
- Procesa y limpia los datos
- Guarda los datos en `data/weather_data.csv`

### 2. Visualizar datos en el dashboard

Ejecuta el dashboard con Streamlit:

```bash
streamlit run dashboard/app.py
```

El dashboard se abrirá automáticamente en tu navegador (generalmente en `http://localhost:8501`).

### 3. Personalizar la ubicación

Edita el archivo `config/settings.json` para cambiar la ubicación:

```json
{
    "location": {
        "name": "Tu Ciudad",
        "latitude": 6.244,
        "longitude": -75.581,
        "timezone": "America/Bogota"
    }
}
```

## 🎯 Características del Dashboard

- **Gráficos interactivos** con Plotly:
  - Temperatura (°C) - Gráfico de línea
  - Humedad Relativa (%) - Gráfico de línea
  - Precipitación (mm) - Gráfico de barras
  - Velocidad del Viento (km/h) - Gráfico de línea

- **Filtros de fecha**: Selecciona rangos de fechas para visualizar datos específicos

- **Estadísticas generales**: Muestra métricas clave en el sidebar

- **Tabla de datos**: Visualiza los datos detallados en formato tabla

- **Descarga de datos**: Descarga los datos filtrados en formato CSV

## 🔧 Módulos del Proyecto

### `data_sources/open_meteo.py`
- Función `get_weather_data()`: Consume la API de Open-Meteo
- Manejo de errores y validación de coordenadas
- Parámetros configurables (latitud, longitud, fechas, zona horaria)

### `processing/transform.py`
- `json_to_dataframe()`: Convierte JSON a DataFrame
- `clean_and_standardize()`: Limpia y estandariza columnas
- `process_weather_data()`: Función principal de procesamiento

### `processing/storage.py`
- `save_to_csv()`: Guarda DataFrames en CSV
- `load_from_csv()`: Carga DataFrames desde CSV
- Soporte para append y timestamps

### `dashboard/app.py`
- Dashboard completo con Streamlit
- Visualizaciones interactivas con Plotly
- Filtros y estadísticas en tiempo real

### `main.py`
- Orquesta todo el flujo del proyecto
- Carga configuración
- Ejecuta: consumo → procesamiento → guardado

## 🔮 Expansión Futura

El proyecto está diseñado para ser fácilmente expandible:

- **Nuevas fuentes de datos**: Agrega nuevos módulos en `data_sources/` (ej: `openweather.py`, `noaa.py`)
- **Más procesamiento**: Extiende `processing/transform.py` con nuevas transformaciones
- **Análisis avanzado**: Agrega módulos de análisis en una nueva carpeta `analysis/`
- **Base de datos**: Modifica `storage.py` para guardar en bases de datos (PostgreSQL, MongoDB, etc.)

## 📝 Notas

- La API de Open-Meteo es gratuita y no requiere API key
- Los datos se obtienen en tiempo real (forecast)
- El proyecto usa coordenadas de Medellín por defecto (Lat: 6.244, Lon: -75.581)
- Los datos se guardan en formato CSV para fácil acceso y portabilidad

## 🤝 Contribuciones

Este proyecto está diseñado para ser un punto de partida. Siéntete libre de:
- Agregar nuevas fuentes de datos
- Mejorar las visualizaciones
- Agregar análisis estadísticos
- Implementar alertas meteorológicas

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso educativo y personal.

