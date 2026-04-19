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
from datetime import datetime

# Make sure backend package is importable when running from dashboard folder
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import backend service directly (no HTTP calls)
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


@st.cache_data(ttl=600)
def fetch_sources():
    """Fetch sources status - cached (10 min)."""
    try:
        status = service.get_sources_status()
        return [
            {
                "name": s["name"],
                "available": s["available"],
                "response_time": round(s["response_time"], 3)
            }
            for s in status
        ]
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
    
    # Lazy load with tabs for heavy components
    tab1, tab2, tab3 = st.tabs(["📍 Map", "📊 Comparison", "📋 Details"])
    
    with tab1:
        st.markdown("### 🗺️ Location Map")
        with st.spinner("Loading map..."):
            col_map, col_info = st.columns([2, 1])
            
            with col_map:
                m = folium.Map(location=[lat, lon], zoom_start=10)
                folium.Marker(
                    [lat, lon],
                    popup=f"<b>{city}</b><br>{lat}, {lon}",
                    icon=folium.Icon(color="blue", icon="info-sign")
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
                        "Status": "✅" if src.get("temperature") else "❌"
                    })
                
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
        else:
            st.info("No multiple sources available for comparison.")
    
    with tab3:
        st.markdown("### 📋 Raw Data")
        st.json(data)


def show_sources():
    """Sources status page with lazy loading."""
    st.title("📡 Weather Sources")
    st.markdown("---")
    st.info("⏳ Checking sources health (can take 10-15 seconds)...")
    
    with st.spinner("🔍 Checking all sources..."):
        sources = fetch_sources()
    
    if not sources:
        st.error("❌ Could not check sources. Some APIs may be down.")
        return
    
    for src in sources:
        status = "🟢 Available" if src.get("available") else "🔴 Unavailable"
        
        with st.expander(f"{src['name']} - {status}"):
            st.write(f"**Available:** {src['available']}")
            st.write(f"**Response Time:** {src.get('response_time', 'N/A'):.3f}s")


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
    return [
        {"name": "Radar IDEAM - Medellín", "lat": 6.244, "lon": -75.581, "info": "Región Valle de Aburrá"},
        {"name": "Radar IDEAM - Bogotá", "lat": 4.711, "lon": -74.072, "info": "Región Cundinamarca"},
        {"name": "Radar IDEAM - Cali", "lat": 3.4516, "lon": -76.532, "info": "Región Valle del Cauca"},
        {"name": "Radar IDEAM - Barranquilla", "lat": 10.9685, "lon": -74.7813, "info": "Región Caribe"},
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
    st.title("🛰️ Radar IDEAM y SIATA")
    st.markdown("---")
    st.markdown(
        "Visualiza los radares IDEAM con los puntos históricos ya consultados y el historial guardado de SIATA."
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
        st.markdown("### 📈 Historial de SIATA")
        with st.spinner("Cargando historial de SIATA..."):
            siata_history = fetch_siata_history(limit=200)

            if siata_history is None or siata_history.empty:
                st.info(
                    "No hay historial local de SIATA. Guarda datos con `python cli.py save --lat 6.24 --lon -75.58` para activar el historial."
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
        st.markdown("### 📊 Historial IDEAM")
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