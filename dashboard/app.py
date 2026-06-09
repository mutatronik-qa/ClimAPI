"""
Streamlit Dashboard
Uses weather_service (single source of truth), no duplicate logic.
Non-blocking with caching.
"""
import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import logging
from datetime import datetime, timedelta

# Make sure backend package is importable when running from dashboard folder
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Internal imports (after path setup)
from src.data_sources.siata_cliente import SIATADownloader
from src.data_sources.ideam_radar_downloader import IDEAMRadarDownloader
from backend.weather_service import get_service

# Get service instance
service = get_service()

# ====================
# Cached Service Calls
# ====================

@st.cache_data(ttl=1200)
def fetch_weather(lat: float, lon: float, source: str = None):
    """Fetch weather - cached (20 min) with timeout."""
    try:
        result = service.get_weather(lat=lat, lon=lon, source=source, use_cache=True)
        return {"data": result}
    except Exception as e:
        logger.error(f"Weather fetch error: {e}")
        return {"error": str(e)}


@st.cache_data(ttl=300)
def fetch_sources(fast: bool = True):
    """Fetch sources status - cached (5 min) with optimized speed."""
    try:
        status = service.get_sources_status(use_cache=True, fast=fast)
        return status
    except:
        return []


# ====================
# Dashboard Pages
# ====================

def show_dashboard():
    """Main dashboard."""
    st.title("🌤️ ClimAPI Weather Dashboard")
    st.markdown("---")
    
    # Sidebar - Location
    st.sidebar.header("📍 Location")
    
    presets = {
        "Medellín": (6.244, -75.581),
        "Bogotá": (4.711, -74.072),
        "Cali": (3.4516, -76.532),
        "Barranquilla": (10.9685, -74.7813),
        "Custom": (None, None)
    }
    
    city = st.sidebar.selectbox("City", list(presets.keys()))
    
    if city == "Custom":
        lat = st.sidebar.number_input("Latitude", value=6.244, step=0.01, format="%.4f")
        lon = st.sidebar.number_input("Longitude", value=-75.581, step=0.01, format="%.4f")
    else:
        lat, lon = presets[city]
    
    # Source selection
    st.sidebar.header("🌐 Sources")
    
    # Skip expensive source check - use hardcoded list for speed
    source_names = ["open-meteo", "openweathermap", "meteoblue", "siata"]
    
    selected_source = st.sidebar.selectbox(
        "Source",
        ["All"] + source_names
    )
    
    source_param = None if selected_source == "All" else selected_source
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh"):
        st.cache_data.clear()
        fetch_weather.clear()
    
    # Fetch data
    with st.spinner("Fetching weather..."):
        weather = fetch_weather(lat, lon, source_param)
    
    if "error" in weather:
        st.error(f"⚠️ Error: {weather['error']}")
        st.info("💡 Try:")
        st.info("- Check your internet connection")
        st.info("- Wait a moment and try again (APIs may be temporarily slow)")
        st.info("- Select a specific source instead of 'All'")
        return
    
    data = weather.get("data", {})
    
    # Display metrics
    st.markdown("### 🌡️ Current Weather")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Temperature", f"{data.get('temperature', 'N/A')}°C" if data.get("temperature") else "N/A")
    with col2:
        st.metric("Humidity", f"{data.get('humidity', 'N/A')}%" if data.get("humidity") else "N/A")
    with col3:
        st.metric("Precipitation", f"{data.get('precipitation', 'N/A')} mm" if data.get("precipitation") else "0 mm")
    with col4:
        st.metric("Wind", f"{data.get('wind_speed', 'N/A')} km/h" if data.get("wind_speed") else "N/A")
    
    st.caption(f"Source: {data.get('source', 'unknown')}")

    # --- NEW: Historical Analysis Section ---
    st.markdown("---")
    st.markdown("### 📈 Historical Analysis")
    history_df = _load_source_history(data.get("source", "combined"), limit=50)
    
    if history_df is not None and not history_df.empty:
        col_chart, col_stats = st.columns([2, 1])
        with col_chart:
            # Simple line chart for temperature
            fig = px.line(history_df, x="timestamp", y="temperature", title="Temperature Trend")
            st.plotly_chart(fig, use_container_width=True)
        with col_stats:
            st.markdown("#### Stats")
            # Ensure temperature is numeric for stats
            temp_numeric = pd.to_numeric(history_df['temperature'], errors='coerce').dropna()
            if not temp_numeric.empty:
                st.write(f"**Records:** {len(history_df)}")
                st.write(f"**Avg Temp:** {temp_numeric.mean():.2f}°C")
                st.write(f"**Max Temp:** {temp_numeric.max():.2f}°C")
            else:
                st.write("No numeric temperature data.")
    else:
        st.info("No historical data available for this source yet.")
    
    # Lazy load with tabs for heavy components
    tab1, tab2, tab3 = st.tabs(["📍 Map & History", "📊 Sources Comparison", "📋 Raw Data"])
    
    with tab1:
        st.markdown("### 🗺️ Location Map")
        with st.spinner("Loading map..."):
            col_map, col_info = st.columns([2, 1])
            
            with col_map:
                m = folium.Map(location=[lat, lon], zoom_start=10)
                # Current marker
                folium.Marker(
                    [lat, lon],
                    popup=f"<b>Current: {city}</b><br>{lat}, {lon}",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)
                
                # Historical markers
                all_history = _load_source_history("combined", limit=200)
                if all_history is not None and not all_history.empty:
                    # Filter unique locations to avoid clutter
                    unique_locs = all_history.drop_duplicates(subset=["lat", "lon"])
                    for _, row in unique_locs.iterrows():
                        if row["lat"] == lat and row["lon"] == lon: continue # skip current
                        folium.CircleMarker(
                            location=[row["lat"], row["lon"]],
                            radius=5,
                            color="blue",
                            fill=True,
                            popup=f"History: {row.get('timestamp')}<br>{row.get('temperature')}°C",
                        ).add_to(m)
                
                st_folium(m, width=600, height=400)
            
            with col_info:
                st.markdown("#### Details")
                st.write(f"**City:** {city}")
                st.write(f"**Lat:** {lat}")
                st.write(f"**Lon:** {lon}")
    
    with tab2:
        st.markdown("### 📊 Sources Comparison")
        # Show all sources if available
        if data.get("all_sources"):
            with st.spinner("Loading comparison..."):
                rows = []
                for src in data["all_sources"]:
                    rows.append({
                        "Source": src.get("source", "?"),
                        "Temperature": f"{src.get('temperature', 'N/A')}°C" if src.get("temperature") else "N/A",
                        "Humidity": f"{src.get('humidity', 'N/A')}%" if src.get("humidity") else "N/A",
                        "Wind": f"{src.get('wind_speed', 'N/A')} km/h" if src.get("wind_speed") else "N/A",
                        "Status": "✅" if src.get("available") else "❌"
                    })
                
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No multiple sources available for comparison.")
    
    with tab3:
        st.markdown("### 📋 Raw Data")
        st.json(data)


def show_sources():
    """Sources status page with lazy loading."""
    st.title("📡 API Integrity & Status")
    st.markdown("---")
    
    col_ctrl1, col_ctrl2 = st.columns([2, 1])
    with col_ctrl1:
        check_type = st.radio("Check Type", ["Quick (3-5s)", "Full (10-15s)"], horizontal=True)
    with col_ctrl2:
        if st.button("🔄 Force Re-check"):
            st.cache_data.clear()
            fetch_sources.clear()
            
    is_fast = "Quick" in check_type
    
    st.info(f"⏳ Checking sources health ({check_type})...")
    
    with st.spinner("🔍 Verifying all API endpoints..."):
        sources = fetch_sources(fast=is_fast)
    
    if not sources:
        st.error("❌ Could not check sources. System might be offline or services are unreachable.")
        return
    
    # Summary metrics
    available_count = sum(1 for s in sources if s.get("available"))
    avg_resp = sum(s.get("response_time", 0) for s in sources) / len(sources)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Available", f"{available_count}/{len(sources)}")
    m2.metric("Avg Response", f"{avg_resp:.2f}s")
    m3.metric("System Integrity", "Healthy" if available_count > 2 else "Degraded", delta=None)
    
    st.markdown("### Source Details")
    for src in sources:
        status = "🟢 Available" if src.get("available") else "🔴 Unavailable"
        
        with st.expander(f"{src['name']} - {status}"):
            st.write(f"**Status:** {'✅ Online' if src.get('available') else '❌ Offline/Error'}")
            st.write(f"**Response Time:** {src.get('response_time', 'N/A'):.3f}s")
            if src.get("error"):
                st.error(f"**Error Details:** {src['error']}")
            
            # Show last check time if available
            if src.get("_checked_at"):
                dt = datetime.fromtimestamp(src["_checked_at"])
                st.caption(f"Last checked: {dt.strftime('%Y-%m-%d %H:%M:%S')}")


def _get_data_path() -> Path:
    return Path(ROOT_DIR) / "data"


def _load_source_history(source: str, limit: int = 100) -> pd.DataFrame | None:
    data_dir = _get_data_path()
    raw_path = data_dir / "raw" / f"{source}.csv"
    processed_path = data_dir / "processed" / "weather.csv"
    path_to_read = None

    if raw_path.exists():
        path_to_read = raw_path
    elif processed_path.exists():
        path_to_read = processed_path
    else:
        return None

    try:
        dtype_spec = {
            'temperature': 'float32',
            'humidity': 'float32',
            'precipitation': 'float32',
            'wind_speed': 'float32',
            'source': 'category',
            'lat': 'float32',
            'lon': 'float32'
        }
        
        df = pd.read_csv(
            path_to_read,
            parse_dates=["timestamp"],
            dtype={k: v for k, v in dtype_spec.items() if k in pd.read_csv(path_to_read, nrows=0).columns},
            on_bad_lines="skip",
            engine="c"
        )
    except Exception:
        return None

    if df.empty:
        return None

    if path_to_read == processed_path:
        if "source" not in df.columns:
            return None
        df = df[df["source"] == source]
        if df.empty:
            return None

    return df.sort_values("timestamp").tail(limit)


def _get_ideam_radar_sites() -> list[dict]:
    """Returns the official 4 IDEAM radar locations."""
    return [
        {"name": "Radar Barrancabermeja", "lat": 7.0, "lon": -73.8, "info": "Región Santander / Magdalena Medio"},
        {"name": "Radar Guaviare", "lat": 2.5, "lon": -72.6, "info": "Región Amazonía / Orinoquía"},
        {"name": "Radar Munchique", "lat": 2.5, "lon": -76.9, "info": "Región Cauca / Pacífico"},
        {"name": "Radar Carimagua", "lat": 4.5, "lon": -71.3, "info": "Región Meta / Llanos Orientales"},
    ]


@st.cache_data(ttl=1200)
def fetch_radar_status(lat: float, lon: float):
    """Fetch IDEAM radar metadata (20 min)."""
    try:
        return service.get_weather(lat=lat, lon=lon, source="ideam-radar", use_cache=True)
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=900)
def fetch_siata_history(limit: int = 100):
    """Load saved SIATA history from the local data folder (15 min)."""
    return _load_source_history("siata", limit)


def render_radar_page():
    """Render radar and SIATA history page with lazy loading."""
    st.title("🛰️ Red de Radares IDEAM y SIATA Regional")
    st.markdown("---")
    st.markdown(
        "Esta sección monitorea el estado global de la red de radares del IDEAM y el historial de descargas regionales de SIATA. "
        "A diferencia de otras fuentes, estas operan a nivel de red o región, no por consulta de coordenadas individuales."
    )

    presets = {
        "Medellín": (6.244, -75.581),
        "Bogotá": (4.711, -74.072),
        "Cali": (3.4516, -76.532),
        "Barranquilla": (10.9685, -74.7813),
        "Custom": (None, None)
    }
    city = st.selectbox("Ciudad base", list(presets.keys()), index=0)

    if city == "Custom":
        lat = st.number_input("Latitud", value=6.244, step=0.01, format="%.4f")
        lon = st.number_input("Longitud", value=-75.581, step=0.01, format="%.4f")
    else:
        lat, lon = presets[city]

    radar_sites = _get_ideam_radar_sites()
    
    # Lazy load with tabs
    tab1, tab2, tab3 = st.tabs(["🗺️ Mapa Radar", "📊 Historial SIATA", "📈 Historial IDEAM"])
    
    with tab1:
        st.markdown("### 🗺️ Radar IDEAM")
        with st.spinner("Cargando mapa..."):
            radar_status = fetch_radar_status(lat, lon)
            ideam_history = _load_source_history("ideam-radar", limit=200)
            
            map_center = [lat, lon]
            m = folium.Map(location=map_center, zoom_start=6)
            folium.Marker([lat, lon], popup=f"<b>{city}</b><br>{lat}, {lon}", icon=folium.Icon(color="blue", icon="star")).add_to(m)

            for radar in radar_sites:
                folium.CircleMarker(
                    location=[radar["lat"], radar["lon"]],
                    radius=8,
                    color="orange",
                    fill=True,
                    fill_color="orange",
                    popup=f"<b>{radar['name']}</b><br>{radar['info']}",
                ).add_to(m)

            if ideam_history is not None and not ideam_history.empty:
                st.markdown("#### Búsquedas IDEAM guardadas")
                history_count = len(ideam_history)
                st.write(f"Se han guardado {history_count} búsquedas IDEAM con coordenadas.")
                
                # Vectorized: filter valid coordinates once
                valid_history = ideam_history.dropna(subset=['lat', 'lon'])
                
                for lat_hist, lon_hist, timestamp in zip(valid_history['lat'], valid_history['lon'], valid_history.get('timestamp', [''])):
                    folium.CircleMarker(
                        location=[lat_hist, lon_hist],
                        radius=5,
                        color="blue",
                        fill=True,
                        fill_color="blue",
                        popup=f"<b>IDEAM búsqueda</b><br>{timestamp}",
                    ).add_to(m)

            st_folium(m, width=700, height=450)

            st.markdown("### 📌 Estado de la última búsqueda IDEAM")
            if radar_status.get("error"):
                st.error(f"No se pudo consultar IDEAM radar: {radar_status['error']}")
            else:
                st.write(f"**Fuente:** {radar_status.get('source', 'ideam-radar')}")
                st.write(f"**Objetos encontrados:** {radar_status.get('files_count', 'N/A')}")
                st.write(f"**Nota:** {radar_status.get('note', 'Sin nota disponible')}")
                if radar_status.get("sample_files"):
                    st.write("**Archivos de ejemplo:**")
                    for obj in radar_status["sample_files"]:
                        st.write(f"- {obj}")
    
    with tab2:
        st.markdown("### 🌐 Datos Regionales SIATA (Web Scraping)")
        st.info("SIATA proporciona datos específicos para el Valle de Aburrá. Estos datos se obtienen mediante web scraping del sitio operacional.")
        
        # --- NUEVA SECCIÓN DE DESCARGA ---
        if st.button("🚀 Iniciar Descarga Completa SIATA"):
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            log_placeholder = st.empty()
            
            try:
                status_placeholder.warning("⏳ Descargando datos de SIATA... Por favor, espere.")
                downloader = SIATADownloader()
                
                # Simulación de progreso para mejorar la UX
                for i in range(1, 101, 20):
                    progress_bar.progress(i)
                    log_placeholder.text(f"Explorando directorios nivel {i//33 + 1}...")
                
                downloader.download_all(max_depth=2)
                progress_bar.progress(100)
                status_placeholder.success("✅ Descarga de SIATA completada con éxito.")
                log_placeholder.text("Inventario generado en data/siata_historico/inventario.csv")
            except Exception as e:
                status_placeholder.error(f"❌ Error durante la descarga: {e}")

        with st.spinner("Cargando historial de SIATA..."):
            siata_history = fetch_siata_history(limit=200)

            if siata_history is None or siata_history.empty:
                st.info(
                    "No hay historial local de SIATA. Realiza una consulta desde el menú o CLI para descargar datos actuales."
                )
            else:
                siata_history = siata_history.sort_values("timestamp")
                siata_history["timestamp"] = pd.to_datetime(siata_history["timestamp"], errors="coerce")
                siata_display = siata_history.copy()

                if "temperatura" in siata_display.columns or "temperature" in siata_display.columns:
                    chart_columns = [col for col in ["temperatura", "temperature", "humidity", "humedad_porcentaje"] if col in siata_display.columns]
                    siata_plot = siata_display.set_index("timestamp")[chart_columns]
                    if not siata_plot.empty:
                        st.line_chart(siata_plot)

                st.markdown("#### Últimos registros SIATA")
                col_list = [col for col in ["timestamp", "temperature", "temperatura_c", "humidity", "humedad_porcentaje", "precipitation", "precipitacion_mm", "wind_speed", "velocidad_viento_kmh"] if col in siata_display.columns]
                st.dataframe(
                    siata_display[col_list].tail(15),
                    use_container_width=True
                )
    
    with tab3:
        st.markdown("### 📡 Descarga de Radar IDEAM")
        st.info("Descarga los datos más recientes desde los servidores de AWS del IDEAM (delay de 24h).")
        
        col_radar, col_days = st.columns(2)
        with col_radar:
            radar_to_download = st.selectbox("Radar", ["Barrancabermeja", "Guaviare", "Munchique", "Carimagua"])
        with col_days:
            days_back = st.slider("Días atrás", 1, 7, 2)

        if st.button(f"📥 Descargar Datos Radar {radar_to_download}"):
            status_radar = st.empty()
            progress_radar = st.progress(0)
            log_radar = st.empty()
            
            try:
                status_radar.warning(f"⏳ Descargando últimos {days_back} días del radar {radar_to_download}...")
                downloader = IDEAMRadarDownloader()
                
                for d in range(days_back):
                    progress_radar.progress(int(((d+1)/days_back)*100))
                    log_radar.text(f"Procesando día {d+1} de {days_back}...")
                    # Descarga del día específico
                    downloader.descargar_ultimos_datos(radar=radar_to_download, dias=1)
                
                progress_radar.progress(100)
                status_radar.success(f"✅ Descarga de {radar_to_download} completada.")
                log_radar.text("Archivos guardados en data/Radar_IDEAM/")
                downloader.generar_inventario(radar_to_download)
            except Exception as e:
                status_radar.error(f"❌ Error: {e}")

        st.markdown("---")
        st.markdown("#### 📋 Historial Local de Radar")
        with st.spinner("Cargando historial IDEAM..."):
            ideam_history = _load_source_history("ideam-radar", limit=200)
            if ideam_history is None or ideam_history.empty:
                st.info("No hay historial de IDEAM disponible.")
            else:
                st.dataframe(ideam_history.tail(20), use_container_width=True)



def main():
    """Main entry."""
    st.sidebar.title("🧭 Navigation")
    
    page = st.sidebar.radio("Go to:", ["Dashboard", "Sources", "Radar + SIATA"])
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Sources":
        show_sources()
    else:
        render_radar_page()


if __name__ == "__main__":
    main()