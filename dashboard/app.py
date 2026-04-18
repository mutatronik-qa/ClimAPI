"""
Streamlit Dashboard
Uses weather_service (single source of truth), no duplicate logic.
Non-blocking with caching.
"""
import os
import sys
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

@st.cache_data(ttl=300)
def fetch_weather(lat: float, lon: float, source: str = None):
    """Fetch weather - cached."""
    try:
        result = service.get_weather(lat=lat, lon=lon, source=source, use_cache=True)
        return {"data": result}
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=60)
def fetch_sources():
    """Fetch sources status - cached."""
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
    sources = fetch_sources()
    source_names = [s["name"] for s in sources]
    
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
        st.error(f"Error: {weather['error']}")
        st.info("Make sure API is running: python main.py")
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
    
    # Map
    st.markdown("---")
    st.markdown("### 🗺️ Location Map")
    
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
    
    # Show all sources if available
    if data.get("all_sources"):
        st.markdown("---")
        st.markdown("### 📊 All Sources")
        
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


def show_sources():
    """Sources status page."""
    st.title("📡 Weather Sources")
    st.markdown("---")
    
    sources = fetch_sources()
    
    for src in sources:
        status = "🟢 Available" if src.get("available") else "🔴 Unavailable"
        
        with st.expander(f"{src['name']} - {status}"):
            st.write(f"**Available:** {src['available']}")
            st.write(f"**Response Time:** {src.get('response_time', 'N/A'):.3f}s")


def main():
    """Main entry."""
    st.sidebar.title("🧭 Navigation")
    
    page = st.sidebar.radio("Go to:", ["Dashboard", "Sources"])
    
    if page == "Dashboard":
        show_dashboard()
    else:
        show_sources()


if __name__ == "__main__":
    main()