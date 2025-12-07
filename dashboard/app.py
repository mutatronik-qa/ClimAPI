"""
Dashboard interactivo para visualizar datos meteorológicos.

Este módulo crea un dashboard usando Streamlit para visualizar
temperatura, humedad, precipitación y velocidad del viento.
"""

from pathlib import Path
import sys
import glob

# Añadir la raíz del proyecto al PYTHONPATH para poder importar módulos sibling
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # e:\GIT\ClimAPI
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from processing.data_processor import DataProcessor
from processing.storage import load_from_csv


def load_data(filepath: str = "data/weather_data.csv") -> pd.DataFrame:
    """
    Carga los datos meteorológicos desde un archivo CSV.
    
    Args:
        filepath: Ruta del archivo CSV
    
    Returns:
        pd.DataFrame: DataFrame con los datos meteorológicos
    """
    try:
        df = load_from_csv(filepath)
        return df
    except FileNotFoundError:
        st.error(f"❌ No se encontró el archivo {filepath}. Por favor, ejecuta main.py primero para obtener datos.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error al cargar los datos: {e}")
        st.stop()

def _load_api_csv_as_standard(path: str) -> pd.DataFrame:
    """
    Carga un CSV de una API y lo normaliza al esquema usado en el dashboard:
    índice datetime UTC y columnas: temperatura_c, humedad_porcentaje, precipitacion_mm, velocidad_viento_kmh
    """
    try:
        df_api = load_from_csv(path)
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    if df_api.empty:
        return df_api

    # asegurar columna timestamp
    if "timestamp" in df_api.columns:
        df_api["timestamp"] = pd.to_datetime(df_api["timestamp"], utc=True)
        df_api = df_api.set_index("timestamp")
    elif df_api.index.dtype == object:
        try:
            df_api.index = pd.to_datetime(df_api.index, utc=True)
        except Exception:
            pass

    # mapeos comunes
    col_map = {}
    if "temperature" in df_api.columns:
        col_map["temperature"] = "temperatura_c"
    if "temp" in df_api.columns:
        col_map["temp"] = "temperatura_c"
    if "humidity" in df_api.columns:
        col_map["humidity"] = "humedad_porcentaje"
    if "wind_speed" in df_api.columns:
        col_map["wind_speed"] = "velocidad_viento_kmh"
    if "precipitation" in df_api.columns:
        col_map["precipitation"] = "precipitacion_mm"
    if "precip" in df_api.columns:
        col_map["precip"] = "precipitacion_mm"

    if col_map:
        df_api = df_api.rename(columns=col_map)

    # mantener sólo las columnas que interesan si existen
    keep = [c for c in ["temperatura_c", "humedad_porcentaje", "precipitacion_mm", "velocidad_viento_kmh"] if c in df_api.columns]
    if not keep:
        return pd.DataFrame()
    return df_api[keep]

def create_temperature_chart(df: pd.DataFrame, date_range: tuple) -> go.Figure:
    """
    Crea un gráfico de línea para la temperatura.
    
    Args:
        df: DataFrame con los datos meteorológicos
        date_range: Tupla con (fecha_inicio, fecha_fin)
    
    Returns:
        go.Figure: Gráfico de Plotly
    """
    df_filtered = df.loc[date_range[0]:date_range[1]]
    
    fig = px.line(
        df_filtered,
        x=df_filtered.index,
        y='temperatura_c',
        title='🌡️ Temperatura (°C)',
        labels={'temperatura_c': 'Temperatura (°C)', 'index': 'Fecha y Hora'},
        color_discrete_sequence=['#FF6B6B']
    )
    fig.update_layout(
        xaxis_title="Fecha y Hora",
        yaxis_title="Temperatura (°C)",
        hovermode='x unified'
    )
    return fig


def create_humidity_chart(df: pd.DataFrame, date_range: tuple) -> go.Figure:
    """
    Crea un gráfico de línea para la humedad.
    
    Args:
        df: DataFrame con los datos meteorológicos
        date_range: Tupla con (fecha_inicio, fecha_fin)
    
    Returns:
        go.Figure: Gráfico de Plotly
    """
    df_filtered = df.loc[date_range[0]:date_range[1]]
    
    fig = px.line(
        df_filtered,
        x=df_filtered.index,
        y='humedad_porcentaje',
        title='💧 Humedad Relativa (%)',
        labels={'humedad_porcentaje': 'Humedad (%)', 'index': 'Fecha y Hora'},
        color_discrete_sequence=['#4ECDC4']
    )
    fig.update_layout(
        xaxis_title="Fecha y Hora",
        yaxis_title="Humedad (%)",
        hovermode='x unified'
    )
    return fig


def create_precipitation_chart(df: pd.DataFrame, date_range: tuple) -> go.Figure:
    """
    Crea un gráfico de barras para la precipitación.
    
    Args:
        df: DataFrame con los datos meteorológicos
        date_range: Tupla con (fecha_inicio, fecha_fin)
    
    Returns:
        go.Figure: Gráfico de Plotly
    """
    df_filtered = df.loc[date_range[0]:date_range[1]]
    
    fig = px.bar(
        df_filtered,
        x=df_filtered.index,
        y='precipitacion_mm',
        title='🌧️ Precipitación (mm)',
        labels={'precipitacion_mm': 'Precipitación (mm)', 'index': 'Fecha y Hora'},
        color_discrete_sequence=['#95E1D3']
    )
    fig.update_layout(
        xaxis_title="Fecha y Hora",
        yaxis_title="Precipitación (mm)",
        hovermode='x unified'
    )
    return fig


def create_wind_speed_chart(df: pd.DataFrame, date_range: tuple) -> go.Figure:
    """
    Crea un gráfico de línea para la velocidad del viento.
    
    Args:
        df: DataFrame con los datos meteorológicos
        date_range: Tupla con (fecha_inicio, fecha_fin)
    
    Returns:
        go.Figure: Gráfico de Plotly
    """
    df_filtered = df.loc[date_range[0]:date_range[1]]
    
    fig = px.line(
        df_filtered,
        x=df_filtered.index,
        y='velocidad_viento_kmh',
        title='💨 Velocidad del Viento (km/h)',
        labels={'velocidad_viento_kmh': 'Velocidad (km/h)', 'index': 'Fecha y Hora'},
        color_discrete_sequence=['#F38181']
    )
    fig.update_layout(
        xaxis_title="Fecha y Hora",
        yaxis_title="Velocidad del Viento (km/h)",
        hovermode='x unified'
    )
    return fig


def fetch_meteoblue_points(lat: float = 6.244, lon: float = -75.581, mode: str = "current"):
    """
    Llamada al backend FastAPI para obtener datos MeteoBlue.
    Devuelve lista de puntos normalizados (timestamp, temperature).
    """
    url = f"http://localhost:8000/api/v1/weather/meteoblue"
    params = {"lat": lat, "lon": lon, "mode": mode}
    try:
        r = requests.get(url, params=params, timeout=8)
        r.raise_for_status()
        payload = r.json().get("data", {})
        points = []
        if payload:
            if mode == "current":
                # payload es dict con timestamp + temperature
                ts = payload.get("timestamp") or payload.get("time")
                temp = payload.get("temperature")
                if ts and temp is not None:
                    points.append({"timestamp": ts, "temperature": temp, "location": payload.get("location")})
            else:
                # forecast: buscar days -> lista de dicts {date, temp_min, temp_max}
                days = payload.get("days") or []
                for d in days:
                    # usar temp_max como punto representativo a mediodía
                    date = d.get("date")
                    temp = d.get("temp_max") or d.get("temp_min")
                    if date and temp is not None:
                        # convertir date a ISO con tiempo 12:00 para agregación horaria
                        ts = f"{date}T12:00:00"
                        points.append({"timestamp": ts, "temperature": temp, "location": payload.get("location_id")})
        return points
    except Exception:
        return []


def load_data_separated(realtime_pattern: str = "data/realtime_*.csv", historical_pattern: str = "data/historical_*.csv"):
    """
    Carga datasets exportados por el analizador de notebooks.
    Devuelve dict con keys 'realtime', 'historical'
    """
    result = {"realtime": pd.DataFrame(), "historical": pd.DataFrame()}
    realtime_files = glob.glob(realtime_pattern)
    historical_files = glob.glob(historical_pattern)

    if realtime_files:
        dfs = []
        for f in realtime_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception as e:
                st.warning(f"Error al cargar {f}: {e}")
        if dfs:
            result["realtime"] = pd.concat(dfs, ignore_index=True)
    
    if historical_files:
        dfs = []
        for f in historical_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception as e:
                st.warning(f"Error al cargar {f}: {e}")
        if dfs:
            result["historical"] = pd.concat(dfs, ignore_index=True)
    
    return result

def main():
    """
    Función principal que configura y ejecuta el dashboard.
    """
    # Configuración de la página
    st.set_page_config(
        page_title="Dashboard Meteorológico",
        page_icon="🌤️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Título principal
    st.title("🌤️ Dashboard Meteorológico - ClimAPI")
    st.markdown("---")
    
    # Sidebar para configuración
    st.sidebar.header("⚙️ Configuración")
    
    # Cargar datos base
    data_file = st.sidebar.text_input(
        "📁 Archivo de datos",
        value="data/weather_data.csv",
        help="Ruta al archivo CSV con los datos meteorológicos"
    )

    # Opción: incluir datos de notebooks (realtime vs historical)
    st.sidebar.subheader("📊 Datasets desde Notebooks")
    datasets = load_data_separated()
    
    source_choice = st.sidebar.radio(
        "Fuente de datos:",
        ["Open-Meteo Principal", "Realtime (Notebooks)", "Historical (Notebooks)", "Combinado"]
    )
    
    # Cargar datos según selección
    if source_choice == "Open-Meteo Principal":
        try:
            df = load_from_csv(data_file)
            st.sidebar.success("✓ Datos Open-Meteo cargados")
        except Exception as e:
            st.sidebar.error(f"Error al cargar {data_file}: {e}")
            st.stop()
    elif source_choice == "Realtime (Notebooks)":
        df = datasets["realtime"]
        if df.empty:
            st.sidebar.warning("No hay datos realtime disponibles")
            st.stop()
        st.sidebar.success(f"✓ {len(df)} registros realtime cargados")
    elif source_choice == "Historical (Notebooks)":
        df = datasets["historical"]
        if df.empty:
            st.sidebar.warning("No hay datos historical disponibles")
            st.stop()
        st.sidebar.success(f"✓ {len(df)} registros historical cargados")
    else:  # Combinado
        df_main = load_from_csv(data_file)
        df_combined = pd.concat([
            df_main,
            datasets["realtime"],
            datasets["historical"]
        ], ignore_index=True)
        df = df_combined if not df_combined.empty else df_main
        st.sidebar.success(f"✓ Combinación de {len(df)} registros cargada")

    # Opciones adicionales de APIs
    st.sidebar.subheader("🔗 APIs Adicionales")
    include_mb = st.sidebar.checkbox("🔗 Incluir MeteoBlue (backend)", value=False)
    include_owm = st.sidebar.checkbox("🔗 Incluir OpenWeatherMap (CSV)", value=False)
    include_radar = st.sidebar.checkbox("🔗 Incluir RADAR IDEAM (CSV)", value=False)

    # Cargar CSVs adicionales si existen
    if include_owm:
        df_owm = _load_api_csv_as_standard("data/openweathermap.csv")
        if not df_owm.empty:
            df = pd.concat([df, df_owm], axis=0, ignore_index=False).sort_index()
            st.sidebar.success("✓ OpenWeatherMap agregado")
    
    if include_radar:
        df_radar = _load_api_csv_as_standard("data/radar_ideam.csv")
        if not df_radar.empty:
            df = pd.concat([df, df_radar], axis=0, ignore_index=False).sort_index()
            st.sidebar.success("✓ RADAR IDEAM agregado")

    if df.empty:
        st.error("❌ No hay datos disponibles. Ejecuta main.py para obtener datos.")
        st.stop()

    # Información general en el sidebar
    st.sidebar.markdown("### 📊 Información General")
    st.sidebar.metric("Total de registros", len(df))
    st.sidebar.metric(
        "Rango de fechas",
        f"{df.index.min().strftime('%Y-%m-%d')} a {df.index.max().strftime('%Y-%d-%m')}"
    )
    
    # Estadísticas básicas
    if 'temperatura_c' in df.columns:
        st.sidebar.metric("🌡️ Temp. Promedio", f"{df['temperatura_c'].mean():.1f} °C")
        st.sidebar.metric("🌡️ Temp. Máxima", f"{df['temperatura_c'].max():.1f} °C")
        st.sidebar.metric("🌡️ Temp. Mínima", f"{df['temperatura_c'].min():.1f} °C")
    
    # Selector de rango de fechas
    st.sidebar.markdown("### 📅 Filtro de Fechas")
    min_date = df.index.min().date()
    max_date = df.index.max().date()
    
    date_range = st.sidebar.date_input(
        "Selecciona el rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Validar que se seleccionaron dos fechas
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = min_date
        end_date = max_date
    
    # Convertir a datetime para el filtrado
    start_datetime = pd.Timestamp(start_date)
    end_datetime = pd.Timestamp(end_date) + pd.Timedelta(days=1)  # Incluir el día completo
    
    # Contenido principal
    col1, col2 = st.columns(2)
    
    with col1:
        if 'temperatura_c' in df.columns:
            st.plotly_chart(
                create_temperature_chart(df, (start_datetime, end_datetime)),
                use_container_width=True
            )
        
        if 'precipitacion_mm' in df.columns:
            st.plotly_chart(
                create_precipitation_chart(df, (start_datetime, end_datetime)),
                use_container_width=True
            )
    
    with col2:
        if 'humedad_porcentaje' in df.columns:
            st.plotly_chart(
                create_humidity_chart(df, (start_datetime, end_datetime)),
                use_container_width=True
            )
        
        if 'velocidad_viento_kmh' in df.columns:
            st.plotly_chart(
                create_wind_speed_chart(df, (start_datetime, end_datetime)),
                use_container_width=True
            )
    
    # Tabla de datos
    st.markdown("---")
    st.subheader("📋 Datos Detallados")
    df_filtered = df.loc[start_datetime:end_datetime]
    st.dataframe(df_filtered, use_container_width=True)
    
    # Botón para descargar datos filtrados
    csv = df_filtered.to_csv()
    st.download_button(
        label="📥 Descargar datos filtrados (CSV)",
        data=csv,
        file_name=f"weather_data_{start_date}_{end_date}.csv",
        mime="text/csv"
    )
    st.sidebar.markdown("---")
    st.sidebar.info("📖 Dashboard Meteorológico v1.0")


if __name__ == "__main__":
    main()

