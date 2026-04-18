"""
Dashboard Streamlit con carga segmentada (lazy loading).

El dashboard se divide en módulos que se cargan bajo demanda,
mejorando el tiempo de inicio y la experiencia del usuario.

Módulos:
- Dashboard (principal): Gráficos de clima
- Mapa: Visualización geográfica con folium
- Análisis: Comparación de fuentes
- Configuración: API keys y ajustes
"""

import streamlit as st
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


# Configuración de página -liviana al inicio
st.set_page_config(
    page_title="ClimAPI Dashboard",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def _init_session():
    """Inicializa estado de sesión."""
    if "source" not in st.session_state:
        st.session_state.source = "open-meteo"
    if "location" not in st.session_state:
        st.session_state.location = {"lat": 6.244, "lon": -75.581, "name": "Medellín"}
    if "date_range" not in st.session_state:
        st.session_state.date_range = None


def _lazy_import_core():
    """Importa core solo cuando se necesita."""
    try:
        from core import get_weather, get_cache, list_sources
        return {"get_weather": get_weather, "get_cache": get_cache, "list_sources": list_sources}
    except ImportError as e:
        st.error(f"Error importando core: {e}")
        return None


def _load_data_safe(source: str, lat: float, lon: float, timezone: str = "America/Bogota") -> Optional[Dict]:
    """Carga datos de forma segura con manejo de errores."""
    core = _lazy_import_core()
    if core is None:
        return None
    
    try:
        return core["get_weather"](source, lat, lon, timezone)
    except Exception as e:
        logger.error(f"Error cargando datos de {source}: {e}")
        st.error(f"Error al obtener datos de {source}: {e}")
        return None


def render_dashboard_page():
    """Renderiza la página principal del dashboard."""
    import pandas as pd
    import plotly.express as px
    from datetime import datetime, timedelta
    
    st.title("🌤️ Dashboard Meteorológico - ClimAPI")
    st.markdown("---")
    
    # Sidebar con configuración
    with st.sidebar:
        st.header("⚙️ Configuración")
        
        # Selector de fuente
        source = st.selectbox(
            "📡 Fuente de datos",
            ["open-meteo", "openweathermap", "meteoblue", "siata"],
            index=0
        )
        st.session_state.source = source
        
        # Selector de ubicación
        location_options = {
            "medellin": ("Medellín", 6.244, -75.581),
            "bogota": ("Bogotá", 4.711, -74.072),
            "cali": ("Cali", 3.452, -76.532),
            "barranquilla": ("Barranquilla", 10.968, -74.781)
        }
        
        selected_city = st.selectbox(
            "📍 Ciudad",
            options=list(location_options.keys()),
            format_func=lambda x: location_options[x][0]
        )
        
        lat, lon = location_options[selected_city][1], location_options[selected_city][2]
        st.session_state.location = {"lat": lat, "lon": lon, "name": location_options[selected_city][0]}
        
        # Rango de fechas
        st.subheader("📅 Rango de Fechas")
        days_back = st.slider("Días hacia atrás", 1, 30, 7)
    
    # Contenedor principal
    with st.spinner(f"🔄 Obteniendo datos de {source}..."):
        data = _load_data_safe(source, lat, lon)
    
    if data is None:
        st.error("❌ No se pudieron obtener datos. Verifica la conexión.")
        st.stop()
    
    # Extraer datos del DataFrame
    try:
        if "data" in data and isinstance(data["data"], pd.DataFrame):
            df = data["data"]
        elif "dataframe" in data:
            df = data["dataframe"]
        else:
            # Intentar convertir directamente
            df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error procesando datos: {e}")
        st.stop()
    
    if df.empty:
        st.warning("⚠️ No hay datos disponibles para los parámetros seleccionados.")
        st.stop()
    
    # Asegurar que timestamp es índice
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
    elif not isinstance(df.index, pd.DatetimeIndex):
        st.warning("⚠️ Los datos no tienen índice de tiempo válido.")
    
    # Filtrar por fecha
    if days_back:
        cutoff = datetime.now() - timedelta(days=days_back)
        df = df[cutoff:]
    
    # Métricas
    st.subheader("📊 Resumen")
    cols = st.columns(4)
    
    with cols[0]:
        if "temperatura_c" in df.columns:
            st.metric("🌡️ Temp. Promedio", f"{df['temperatura_c'].mean():.1f}°C")
    with cols[1]:
        if "humedad_porcentaje" in df.columns:
            st.metric("💧 Humedad", f"{df['humedad_porcentaje'].mean():.0f}%")
    with cols[2]:
        if "precipitacion_mm" in df.columns:
            st.metric("🌧️ Precipitación", f"{df['precipitacion_mm'].sum():.1f} mm")
    with cols[3]:
        if "velocidad_viento_kmh" in df.columns:
            st.metric("💨 Viento", f"{df['velocidad_viento_kmh'].mean():.1f} km/h")
    
    st.markdown("---")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        if "temperatura_c" in df.columns:
            fig_temp = px.line(
                df, 
                y="temperatura_c",
                title="🌡️ Temperatura (°C)",
                color_discrete_sequence=["#FF6B6B"]
            )
            fig_temp.update_layout(hovermode="x unified")
            st.plotly_chart(fig_temp, use_container_width=True)
    
    with col2:
        if "humedad_porcentaje" in df.columns:
            fig_hum = px.line(
                df,
                y="humedad_porcentaje",
                title="💧 Humedad Relativa (%)",
                color_discrete_sequence=["#4ECDC4"]
            )
            fig_hum.update_layout(hovermode="x unified")
            st.plotly_chart(fig_hum, use_container_width=True)
    
    # Precipitación y viento
    col3, col4 = st.columns(2)
    
    with col3:
        if "precipitacion_mm" in df.columns:
            fig_precip = px.bar(
                df,
                y="precipitacion_mm",
                title="🌧️ Precipitación (mm)",
                color_discrete_sequence=["#95E1D3"]
            )
            st.plotly_chart(fig_precip, use_container_width=True)
    
    with col4:
        if "velocidad_viento_kmh" in df.columns:
            fig_wind = px.line(
                df,
                y="velocidad_viento_kmh",
                title="💨 Velocidad del Viento (km/h)",
                color_discrete_sequence=["#F38181"]
            )
            st.plotly_chart(fig_wind, use_container_width=True)
    
    # Tabla de datos
    st.markdown("---")
    st.subheader("📋 Datos Detallados")
    
    with st.expander("Ver tabla de datos"):
        st.dataframe(df.head(100), use_container_width=True)
        
        # Descarga
        csv = df.to_csv()
        st.download_button(
            label="📥 Descargar CSV",
            data=csv,
            file_name=f"weather_data_{source}.csv",
            mime="text/csv"
        )
    
    # Info de fuente
    st.caption(f"📡 Datos de: {source} | Ubicación: {st.session_state.location['name']}")


def render_map_page():
    """Renderiza la página de mapa."""
    import folium
    from streamlit_folium import st_folium
    
    st.title("🗺️ Mapa Meteorológico")
    st.markdown("---")
    
    # Selector de ubicación para el mapa
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("📍 Ubicación")
        
        location = st.session_state.get("location", {"lat": 6.244, "lon": -75.581, "name": "Medellín"})
        
        lat = st.number_input("Latitud", value=location["lat"], step=0.01)
        lon = st.number_input("Longitud", value=location["lon"], step=0.01)
        
        st.info(f"Coordenadas: {lat}, {lon}")
    
    # Crear mapa
    m = folium.Map(location=[lat, lon], zoom_start=10)
    
    # Agregar marcador
    folium.Marker(
        [lat, lon],
        popup=f"📍 {location['name']}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)
    
    # Capa GeoJSON de Colombia (simplificada)
    try:
        geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/COL.geo.json"
        folium.GeoJson(
            geojson_url,
            name="Colombia",
            style_function=lambda x: {"fillColor": "yellow", "color": "black", "weight": 1, "fillOpacity": 0.1}
        ).add_to(m)
    except Exception as e:
        logger.warning(f"Error cargando GeoJSON: {e}")
    
    # Mostrar mapa
    st_folium(m, width=700, height=500)
    
    st.markdown("""
    ### ℹ️ Información
    - Los puntos rojos indican ubicaciones con datos meteorológicos
    - Puedes hacer zoom y mover el mapa para explorar diferentes áreas
    """)


def render_analysis_page():
    """Renderiza página de análisis comparativo."""
    import pandas as pd
    import plotly.express as px
    
    st.title("📊 Análisis Comparativo de Fuentes")
    st.markdown("---")
    
    # Fuentes disponibles
    core = _lazy_import_core()
    if core:
        sources = core["list_sources"]()
        st.subheader("📡 Fuentes Disponibles")
        
        for src in sources:
            with st.expander(f"{src['name']}"):
                st.write(f"- **Gratuito**: {'Sí' if src['is_free'] else 'No'}")
                st.write(f"- **Requiere API Key**: {'Sí' if src['requires_api_key'] else 'No'}")
                st.write(f"- **TTL por defecto**: {src['ttl_default']} segundos")
    
    st.markdown("---")
    st.subheader("📈 Comparación de Datos")
    
    # Comparar fuentes si hay datos
    location = st.session_state.get("location", {"lat": 6.244, "lon": -75.581})
    
    if st.button("🔄 Comparar fuentes"):
        with st.spinner("Obteniendo datos de todas las fuentes..."):
            results = {}
            
            for source_name in ["open-meteo"]:
                try:
                    data = core["get_weather"](source_name, location["lat"], location["lon"])
                    if data and "data" in data:
                        results[source_name] = data["data"]
                except Exception as e:
                    logger.warning(f"Error obteniendo {source_name}: {e}")
            
            if results:
                # Mostrar comparación
                for name, df in results.items():
                    st.write(f"### {name}")
                    st.dataframe(df.head(5))
            else:
                st.warning("No hay datos disponibles para comparar")


def render_config_page():
    """Renderiza página de configuración."""
    import os
    
    st.title("⚙️ Configuración")
    st.markdown("---")
    
    # API Keys
    st.subheader("🔑 API Keys")
    
    # OpenWeatherMap
    st.markdown("**OpenWeatherMap**")
    owm_key = st.text_input(
        "API Key",
        value=os.getenv("OPENWEATHER_API_KEY", ""),
        type="password",
        help="Obtener en https://openweathermap.org/api"
    )
    
    # MeteoBlue
    st.markdown("**MeteoBlue**")
    mb_key = st.text_input(
        "API Key",
        value=os.getenv("METEOBLUE_API_KEY", ""),
        type="password"
    )
    mb_secret = st.text_input(
        "Shared Secret",
        value=os.getenv("METEOBLUE_SHARED_SECRET", ""),
        type="password"
    )
    
    # Caché
    st.markdown("---")
    st.subheader("🗃️ Caché")
    
    col1, col2 = st.columns(2)
    
    with col1:
        ttl = st.slider("TTL (minutos)", 5, 60, 15)
        st.caption(f"Tiempo de vida de los datos en caché: {ttl} minutos")
    
    with col2:
        if st.button("🗑️ Limpiar caché"):
            core = _lazy_import_core()
            if core:
                core["get_cache"]().clear()
                st.success("Caché limpiado")
    
    # Estadísticas de caché
    st.markdown("---")
    st.subheader("📊 Estadísticas")
    
    if st.button("📈 Ver estadísticas"):
        core = _lazy_import_core()
        if core:
            stats = core["get_cache"]().get_stats()
            st.json(stats)


def main():
    """Función principal con navegación."""
    _init_session()
    
    # Navegación
    st.sidebar.title("🧭 Navegación")
    page = st.sidebar.radio(
        "Seleccionar página:",
        ["📊 Dashboard", "🗺️ Mapa", "📊 Análisis", "⚙️ Configuración"]
    )
    
    # Renderizar página seleccionada (carga lazy)
    if page == "📊 Dashboard":
        render_dashboard_page()
    elif page == "🗺️ Mapa":
        render_map_page()
    elif page == "📊 Análisis":
        render_analysis_page()
    elif page == "⚙️ Configuración":
        render_config_page()


if __name__ == "__main__":
    main()