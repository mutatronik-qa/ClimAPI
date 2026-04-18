"""
Streamlit Dashboard - ClimAPI v3.0
Clean, non-blocking, with map and data laboratory.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# ====================
# Configuration
# ====================

API_URL = "http://localhost:8000"
st.set_page_config(
    page_title="ClimAPI Dashboard",
    page_icon="🌤️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ====================
# Cached API Calls
# ====================

@st.cache_data(ttl=300)
def fetch_weather(lat: float, lon: float, source: str = None, _cache: bool = True) -> Dict[str, Any]:
    """Fetch weather data with caching."""
    try:
        params = {"lat": lat, "lon": lon, "timezone": "America/Bogota", "use_cache": _cache}
        if source:
            params["source"] = source
            
        response = requests.get(f"{API_URL}/weather/current", params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300)
def fetch_forecast(lat: float, lon: float, days: int = 7) -> Dict[str, Any]:
    """Fetch forecast data with caching."""
    try:
        params = {"lat": lat, "lon": lon, "days": days, "timezone": "America/Bogota"}
        response = requests.get(f"{API_URL}/weather/forecast", params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=60)
def fetch_sources() -> List[Dict[str, Any]]:
    """Fetch available sources."""
    try:
        response = requests.get(f"{API_URL}/sources", timeout=5)
        return response.json().get("sources", [])
    except:
        return [{"name": "open-meteo", "is_available": False}]


@st.cache_data(ttl=60)
def fetch_health() -> Dict[str, Any]:
    """Fetch health status."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.json()
    except:
        return {"status": "unknown"}


# ====================
# Data Laboratory - Analysis Functions
# ====================

def calculate_moving_average(df: pd.DataFrame, column: str, window: int = 7) -> pd.Series:
    """Calculate moving average."""
    return df[column].rolling(window=window, min_periods=1).mean()


def detect_anomalies(df: pd.DataFrame, column: str, threshold: float = 2.0) -> pd.Series:
    """Detect anomalies using z-score."""
    mean = df[column].mean()
    std = df[column].std()
    if std == 0:
        return pd.Series([False] * len(df), index=df.index)
    z_scores = abs((df[column] - mean) / std)
    return z_scores > threshold


def analyze_trends(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze trends in weather data."""
    analysis = {}
    
    for col in ["temperature", "humidity", "precipitation", "wind_speed"]:
        if col not in df.columns:
            continue
            
        series = df[col].dropna()
        if len(series) < 2:
            continue
        
        # Moving averages
        ma_7 = calculate_moving_average(df, col, 7)
        ma_30 = calculate_moving_average(df, col, 30) if len(series) > 30 else ma_7
        
        # Anomalies
        anomalies = detect_anomalies(df, col)
        
        analysis[col] = {
            "mean": float(series.mean()),
            "std": float(series.std()),
            "min": float(series.min()),
            "max": float(series.max()),
            "trend": "increasing" if ma_7.iloc[-1] > ma_7.iloc[0] else "decreasing",
            "anomaly_count": int(anomalies.sum()),
            "anomaly_percentage": float(anomalies.sum() / len(df) * 100)
        }
    
    return analysis


# ====================
# Dashboard Pages
# ====================

def show_dashboard():
    """Main dashboard view."""
    st.title("🌤️ ClimAPI Weather Dashboard")
    st.markdown("---")
    
    # Sidebar - Location Selection
    st.sidebar.header("📍 Location")
    
    presets = {
        "Medellín": (6.244, -75.581),
        "Bogotá": (4.711, -74.072),
        "Cali": (3.4516, -76.532),
        "Barranquilla": (10.9685, -74.7813),
        "Cartagena": (10.391, -75.483),
        "Custom": (None, None)
    }
    
    city = st.sidebar.selectbox("City", list(presets.keys()))
    
    if city == "Custom":
        lat = st.sidebar.number_input("Latitude", value=6.244, step=0.01, format="%.4f")
        lon = st.sidebar.number_input("Longitude", value=-75.581, step=0.01, format="%.4f")
    else:
        lat, lon = presets[city]
    
    # Source Selection
    st.sidebar.header("🌐 Data Sources")
    sources = fetch_sources()
    source_names = [s["name"] for s in sources]
    source_status = {s["name"]: s.get("is_available", False) for s in sources}
    
    selected_source = st.sidebar.selectbox(
        "Weather Source",
        ["All"] + source_names,
        format_func=lambda x: f"{'✅' if source_status.get(x, False) else '❌'} {x}" if x != "All" else x
    )
    
    source_param = None if selected_source == "All" else selected_source
    
    # Refresh button
    col1, col2 = st.sidebar.columns(2)
    if col1.button("🔄 Refresh"):
        st.cache_data.clear()
        fetch_weather.clear()
    if col2.button("🗑️ Clear Cache"):
        try:
            requests.delete(f"{API_URL}/cache")
            st.sidebar.success("Cache cleared!")
        except:
            st.sidebar.error("Failed to clear cache")
    
    # Fetch weather data
    with st.spinner("Fetching weather data..."):
        weather = fetch_weather(lat, lon, source_param)
    
    if "error" in weather:
        st.error(f"Error: {weather['error']}")
        st.info("Make sure the API is running: `python api/main.py`")
        return
    
    data = weather.get("data", {})
    
    # Current Weather Display
    st.markdown("### 🌡️ Current Weather")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Temperature", f"{data.get('temperature', 'N/A')}°C" if data.get("temperature") else "N/A")
    with col2:
        st.metric("Humidity", f"{data.get('humidity', 'N/A')}%" if data.get("humidity") else "N/A")
    with col3:
        precip = data.get("precipitation", 0)
        st.metric("Precipitation", f"{precip:.1f} mm" if precip else "0 mm")
    with col4:
        wind = data.get("wind_speed", 0)
        st.metric("Wind Speed", f"{wind:.1f} km/h" if wind else "N/A")
    
    st.caption(f"📡 Source: {data.get('source', 'unknown')} | Updated: {weather.get('fetched_at', '')[:19]}")
    
    # Map Section
    st.markdown("---")
    st.markdown("### 🗺️ Location Map")
    
    col_map, col_info = st.columns([2, 1])
    
    with col_map:
        m = folium.Map(location=[lat, lon], zoom_start=10)
        folium.Marker(
            [lat, lon],
            popup=f"<b>{city}</b><br>Lat: {lat}<br>Lon: {lon}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)
        st_folium(m, width=600, height=400)
    
    with col_info:
        st.markdown("#### Location Details")
        st.write(f"**City:** {city}")
        st.write(f"**Latitude:** {lat}")
        st.write(f"**Longitude:** {lon}")
        st.write(f"**Timezone:** America/Bogota")
    
    # Forecast Section
    st.markdown("---")
    st.markdown("### 📈 Weather Forecast")
    
    forecast = fetch_forecast(lat, lon, days=7)
    
    if "error" not in forecast and forecast.get("data"):
        df_forecast = pd.DataFrame(forecast["data"])
        df_forecast["timestamp"] = pd.to_datetime(df_forecast["timestamp"])
        df_forecast = df_forecast.set_index("timestamp")
        
        # Temperature chart
        fig = px.line(
            df_forecast,
            y="temperature",
            title="Temperature Forecast (°C)",
            markers=True,
            color_discrete_sequence=["#FF6B6B"]
        )
        fig.update_layout(xaxis_title="Time", yaxis_title="Temperature (°C)")
        st.plotly_chart(fig, use_container_width=True)
        
        # Precipitation chart
        fig2 = px.bar(
            df_forecast,
            y="precipitation",
            title="Precipitation Forecast (mm)",
            color_discrete_sequence=["#4ECDC4"]
        )
        fig2.update_layout(xaxis_title="Time", yaxis_title="Precipitation (mm)")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Forecast data not available")


def show_laboratory():
    """Data Laboratory - Analysis and Trends."""
    st.title("🔬 Data Laboratory")
    st.markdown("---")
    
    # Load sample data for analysis
    st.markdown("### 📊 Data Analysis")
    
    # Generate sample historical data for demonstration
    dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
    import numpy as np
    
    np.random.seed(42)
    data = {
        "timestamp": dates,
        "temperature": 20 + 5 * np.sin(np.linspace(0, 4*np.pi, 90)) + np.random.normal(0, 2, 90),
        "humidity": 70 + 10 * np.cos(np.linspace(0, 3*np.pi, 90)) + np.random.normal(0, 5, 90),
        "precipitation": np.maximum(0, 2 * np.random.exponential(1, 90)),
        "wind_speed": 5 + 3 * np.random.randn(90)
    }
    
    df = pd.DataFrame(data)
    df = df.set_index("timestamp")
    
    # Display raw data
    with st.expander("📋 Raw Data"):
        st.dataframe(df.head(30), use_container_width=True)
    
    # Trend Analysis
    st.markdown("### 📈 Trend Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Temperature trends
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["temperature"], name="Temperature", line=dict(color="#FF6B6B")))
        fig.add_trace(go.Scatter(x=df.index, y=calculate_moving_average(df, "temperature", 7), name="MA 7 days", line=dict(color="#F38181", dash="dash")))
        fig.add_trace(go.Scatter(x=df.index, y=calculate_moving_average(df, "temperature", 30), name="MA 30 days", line=dict(color="#FCE38A", dash="dot")))
        fig.update_layout(title="Temperature with Moving Averages", xaxis_title="Date", yaxis_title="°C")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Humidity trends
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df.index, y=df["humidity"], name="Humidity", line=dict(color="#4ECDC4")))
        fig2.add_trace(go.Scatter(x=df.index, y=calculate_moving_average(df, "humidity", 7), name="MA 7 days", line=dict(color="#45B7AA", dash="dash")))
        fig2.update_layout(title="Humidity with Moving Averages", xaxis_title="Date", yaxis_title="%")
        st.plotly_chart(fig2, use_container_width=True)
    
    # Anomaly Detection
    st.markdown("### ⚠️ Anomaly Detection")
    
    analysis = analyze_trends(df)
    
    for col, stats in analysis.items():
        if stats:
            with st.expander(f"🔍 {col.title()} Analysis"):
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Mean", f"{stats['mean']:.2f}")
                col_b.metric("Std Dev", f"{stats['std']:.2f}")
                col_c.metric("Trend", stats['trend'].title())
                col_d.metric("Anomalies", f"{stats['anomaly_count']} ({stats['anomaly_percentage']:.1f}%)")
                
                # Plot anomalies
                anomalies = detect_anomalies(df, col)
                if anomalies.sum() > 0:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=df.index, y=df[col], name=col, line=dict(color="#95E1D3")))
                    anomaly_points = df[anomalies]
                    fig.add_trace(go.Scatter(
                        x=anomaly_points.index, 
                        y=anomaly_points[col], 
                        mode="markers", 
                        name="Anomaly",
                        marker=dict(color="red", size=10, symbol="x")
                    ))
                    fig.update_layout(title=f"{col.title()} - Anomalies Highlighted")
                    st.plotly_chart(fig, use_container_width=True)
    
    # Statistics Summary
    st.markdown("### 📊 Statistics Summary")
    st.dataframe(df.describe(), use_container_width=True)


def show_sources_page():
    """Sources Status Page."""
    st.title("📡 Weather Sources Status")
    st.markdown("---")
    
    health = fetch_health()
    sources = fetch_sources()
    
    # Overall status
    st.markdown("### System Health")
    status_color = "🟢" if health.get("status") == "healthy" else "🟡" if health.get("status") == "degraded" else "🔴"
    st.write(f"{status_color} Status: **{health.get('status', 'unknown').upper()}**")
    
    # Source details
    st.markdown("### Source Details")
    
    for src in sources:
        status_icon = "🟢" if src.get("is_available") else "🔴"
        free_icon = "✅" if src.get("is_free") else "💰"
        
        with st.expander(f"{status_icon} {src['name']} {free_icon}"):
            col1, col2, col3 = st.columns(3)
            col1.metric("Available", "Yes" if src.get("is_available") else "No")
            col2.metric("Free", "Yes" if src.get("is_free") else "No")
            col3.metric("Response Time", f"{src.get('response_time', 0):.3f}s")


def main():
    """Main entry point with navigation."""
    st.sidebar.title("🧭 Navigation")
    
    page = st.sidebar.radio("Go to:", ["Dashboard", "Data Laboratory", "Sources"])
    
    if page == "Dashboard":
        show_dashboard()
    elif page == "Data Laboratory":
        show_laboratory()
    elif page == "Sources":
        show_sources_page()


if __name__ == "__main__":
    main()