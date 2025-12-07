from pathlib import Path
import glob
import pandas as pd
import streamlit as st

def load_data_separated(realtime_pattern: str = "data/realtime_*.csv", historical_pattern: str = "data/historical_*.csv"):
    """
    Carga datasets exportados por el analizador. Devuelve dict con keys 'realtime', 'historical'
    """
    result = {"realtime": pd.DataFrame(), "historical": pd.DataFrame()}
    realtime_files = glob.glob(realtime_pattern)
    historical_files = glob.glob(historical_pattern)

    if realtime_files:
        dfs = [pd.read_csv(f) for f in realtime_files]
        result["realtime"] = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    if historical_files:
        dfs = [pd.read_csv(f) for f in historical_files]
        result["historical"] = pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    return result

def main():
    """
    Función principal que configura y ejecuta el dashboard.
    """
    # Reemplazar la carga única por carga separada
    datasets = load_data_separated()
    df_realtime = datasets["realtime"]
    df_historical = datasets["historical"]

    st.sidebar.header("📁 Fuente de datos (analizador ipynb)")
    source_choice = st.sidebar.radio("Mostrar datos:", ["Realtime", "Historical", "Both"])
    if source_choice == "Realtime":
        df = df_realtime
    elif source_choice == "Historical":
        df = df_historical
    else:
        # unir para vista combinada (pero mantener separación interna)
        df = pd.concat([df_realtime, df_historical], ignore_index=True) if not df_realtime.empty or not df_historical.empty else pd.DataFrame()

    if df.empty:
        st.warning("No hay datos cargados por el analizador. Ejecuta main.py para intentar extraer/exportar DataFrames desde los notebooks.")
        st.stop()

    # ...existing code que crea gráficos usando el df seleccionado ...