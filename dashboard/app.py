"""
Streamlit Dashboard - Clean, non-blocking, with map.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
st.set_page_config(page_title="ClimAPI Dashboard", page_icon="🌤️", layout="wide")

# Cache decorator for API calls
@st.cache_data(ttl=300)
def fetch_weather(lat: float, lon: float, source: str = None):
    """Fetch weather data from API with caching."""
    try:
        params = {"lat": lat, "lon": lon, "timezone": "America/Bogota"}
        if source:
            params["source"] = source
            
        response = requests.get(f"{API_URL}/weather/current", params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=60)
def fetch_sources():
    """Fetch available sources."""
    try:
        response = requests.get(f"{API_URL}/sources", timeout=5)
        return response.json().get("sources", [])
    except:
        return [{"name": "open-meteo", "status": "unknown"}]


def show_dashboard():
    """Main dashboard view."""
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
        lat = st.sidebar.number_input("Latitude", value=6.244, step=0.01)
        lon = st.sidebar.number_input("Longitude", value=-75.581, step=0.01)
    else:
        lat, lon = presets[city]
    
    # Source selection
    st.sidebar.header("🌐 Sources")
    sources = fetch_sources()
    source_names = [s["name"] for s in sources]
    source_status = {s["name"]: s.get("status", "unknown") for s in sources}
    
    selected_source = st.sidebar.selectbox(
        "Weather Source",
        ["All"] + source_names,
        format_func=lambda x: f"{x} ({source_status.get(x, '?')})" if x != "All" else x
    )
    
    source_param = None if selected_source == "All" else selected_source
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh", type="primary"):
        st.cache_data.clear()
        fetch_weather.clear()
    
    # Fetch data
    with st.spinner("Fetching weather data..."):
        weather = fetch_weather(lat, lon, source_param)
    
    if "error" in weather:
        st.error(f"Error: {weather['error']}")
        st.info("Make sure the API is running: `python main.py`")
        return
    
    data = weather.get("data", {})
    
    # Show sources info
    if "sources_responded" in data:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📡 Source Status")
        for src in data.get("sources_responded", []):
            st.sidebar.success(f"✅ {src}")
        for src in data.get("sources_failed", []):
            st.sidebar.warning(f"❌ {src}")
    
    # Current weather cards
    st.markdown("### 🌡️ Current Weather")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Temperature", f"{data.get('temperature', 'N/A')}°C" if data.get("temperature") else "N/A")
    with col2:
        st.metric("Humidity", f"{data.get('humidity', 'N/A')}%" if data.get("humidity") else "N/A")
    with col3:
        st.metric("Precipitation", f"{data.get('precipitation', 'N/A')} mm" if data.get("precipitation") else "N/A")
    with col4:
        wind = data.get("wind_speed", 0)
        st.metric("Wind", f"{wind:.1f} km/h" if wind else "N/A")
    
    # Source info
    st.caption(f"Data source: {data.get('source', 'unknown')}")
    
    # Map
    st.markdown("---")
    st.markdown("### 🗺️ Location Map")
    
    col_map, col_info = st.columns([2, 1])
    
    with col_map:
        m = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker(
            [lat, lon],
            popup=f"{city}: {lat}, {lon}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)
        st_folium(m, width=500, height=350)
    
    with col_info:
        st.markdown("#### Location Details")
        st.write(f"**City:** {city}")
        st.write(f"**Latitude:** {lat}")
        st.write(f"**Longitude:** {lon}")
        st.write(f"**Timezone:** America/Bogota")
        if data.get("timestamp"):
            st.write(f"**Updated:** {data['timestamp'][:19]}")


def show_sources_page():
    """Sources status page."""
    st.title("📡 Weather Sources Status")
    st.markdown("---")
    
    sources = fetch_sources()
    
    for src in sources:
        status = src.get("status", "unknown")
        color = "🟢" if status == "ok" else "🟡" if status == "no_data" else "🔴"
        
        with st.expander(f"{color} {src['name']}"):
            st.write(f"**Status:** {status}")
            st.write(f"**Response Time:** {src.get('response_time', 'N/A'):.2f}s" if isinstance(src.get("response_time"), float) else "N/A")


def main():
    """Main entry point."""
    st.sidebar.title("🧭 Navigation")
    
    page = st.sidebar.radio("Go to:", ["Dashboard", "Sources"])
    
    if page == "Dashboard":
        show_dashboard()
    else:
        show_sources_page()


if __name__ == "__main__":
    main()