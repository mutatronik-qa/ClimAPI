"""
Punto de entrada principal de ClimAPI.

Proporciona interfaz CLI para:
- Iniciar el Dashboard Streamlit
- Iniciar la API FastAPI
- Ejecutar tareas de consola
- Verificar configuración

Uso:
    python run.py dashboard    # Iniciar dashboard
    python run.py api          # Iniciar API
    python run.py check        # Verificar configuracion
    python run.py test         # Probar fuentes de datos
"""

import sys
import argparse
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_dashboard():
    """Inicia el dashboard Streamlit."""
    import subprocess
    
    dashboard_path = PROJECT_ROOT / "dashboard" / "main.py"
    
    if not dashboard_path.exists():
        dashboard_path = PROJECT_ROOT / "dashboard" / "app.py"
    
    logger.info("Iniciando Dashboard Streamlit...")
    subprocess.run(["streamlit", "run", str(dashboard_path)])


def cmd_api():
    """Inicia el servidor FastAPI."""
    import uvicorn
    
    logger.info("Iniciando API FastAPI...")
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


def cmd_check():
    """Verifica la configuracion del sistema."""
    from config import get_settings
    
    settings = get_settings()
    
    print("\n" + "=" * 50)
    print("CONFIGURACION DE CLIMAPI")
    print("=" * 50)
    
    print("\n[Directorios]")
    print(f"   - Data: {settings.data_dir}")
    print(f"   - Cache: {settings.cache_dir}")
    print(f"   - TTL: {settings.cache_ttl_minutes} minutos")
    
    print("\n[Fuentes de datos]")
    print("   [OK] Open-Meteo (gratuito)")
    
    owm_key = settings.get("OPENWEATHER_API_KEY")
    mb_key = settings.get("METEOBLUE_API_KEY")
    
    if owm_key:
        print("   [OK] OpenWeatherMap (API key configurada)")
    else:
        print("   [--] OpenWeatherMap (sin API key)")
    
    if mb_key:
        print("   [OK] MeteoBlue (API key configurada)")
    else:
        print("   [--] MeteoBlue (sin API key)")
    
    print("\n[Directorios del proyecto]")
    for dir_name in ["data", "cache", "logs"]:
        path = Path(dir_name)
        if path.exists():
            files = list(path.glob("*"))
            print(f"   [OK] {dir_name}/ ({len(files)} archivos)")
        else:
            print(f"   [--] {dir_name}/ (no existe)")
    
    print("\n" + "=" * 50)


def cmd_test():
    """Prueba las fuentes de datos."""
    from core import get_source, list_sources
    
    print("\n" + "=" * 50)
    print("PROBANDO FUENTES DE DATOS")
    print("=" * 50)
    
    lat, lon = 6.244, -75.581
    
    print(f"\nUbicacion: Medellin ({lat}, {lon})")
    
    sources = list_sources()
    print(f"\nFuentes disponibles: {len(sources)}")
    
    for src in sources:
        status = "OK" if src["is_free"] else "$"
        print(f"   [{status}] {src['name']}")
    
    print("\nProbando Open-Meteo...")
    
    try:
        source = get_source("open-meteo")
        if source:
            data = source.fetch_current(lat, lon)
            if data and data.get("data"):
                records = len(data["data"])
                print(f"   [OK] Obtenidos {records} registros")
            else:
                print("   [--] Sin datos")
        else:
            print("   [--] Fuente no disponible")
    except Exception as e:
        print(f"   [ERROR] {e}")
    
    print("\n" + "=" * 50)


def cmd_cache_stats():
    """Muestra estadisticas del cache."""
    from core import get_cache
    
    cache = get_cache()
    stats = cache.get_stats()
    
    print("\n" + "=" * 50)
    print("ESTADISTICAS DEL CACHE")
    print("=" * 50)
    
    metrics = stats.get("metrics", {})
    print(f"\n[Metricas]")
    print(f"   - Hits: {metrics.get('hits', 0)}")
    print(f"   - Misses: {metrics.get('misses', 0)}")
    print(f"   - Hit Rate: {metrics.get('hit_rate_percent', 0)}%")
    print(f"   - Entradas: {stats.get('entries', 0)}")
    print(f"   - Directorio: {stats.get('directory', 'N/A')}")
    
    print("\n" + "=" * 50)


def cmd_combine():
    """Combina datos de todas las fuentes."""
    from core import get_source
    
    lat, lon = 6.244, -75.581
    
    print("\n" + "=" * 50)
    print("COMBINANDO DATOS DE MULTIPLES FUENTES")
    print("=" * 50)
    
    all_data = {}
    sources_to_try = ["open-meteo"]
    
    for src_name in sources_to_try:
        try:
            source = get_source(src_name)
            if source:
                data = source.fetch_current(lat, lon)
                if data and data.get("data"):
                    all_data[src_name] = data["data"]
                    print(f"   [OK] {src_name}: {len(data['data'])} registros")
                else:
                    print(f"   [--] {src_name}: sin datos")
        except Exception as e:
            print(f"   [ERROR] {src_name}: {e}")
    
    if all_data:
        import pandas as pd
        
        dfs = []
        for name, records in all_data.items():
            df = pd.DataFrame(records)
            df["source"] = name
            dfs.append(df)
        
        if dfs:
            combined = pd.concat(dfs, ignore_index=True)
            
            output_path = PROJECT_ROOT / "data" / "weather_data_combined.csv"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            combined.to_csv(output_path, index=False)
            
            print(f"\n[OK] Datos combinados guardados en: {output_path}")
            print(f"   Total: {len(combined)} registros")
    
    print("\n" + "=" * 50)


def main():
    """Punto de entrada CLI."""
    parser = argparse.ArgumentParser(
        description="ClimAPI - API Meteorologica con multiples fuentes"
    )
    
    parser.add_argument(
        "command",
        choices=["dashboard", "api", "check", "test", "cache-stats", "combine"],
        help="Comando a ejecutar"
    )
    
    args = parser.parse_args()
    
    commands = {
        "dashboard": cmd_dashboard,
        "api": cmd_api,
        "check": cmd_check,
        "test": cmd_test,
        "cache-stats": cmd_cache_stats,
        "combine": cmd_combine
    }
    
    commands[args.command]()


if __name__ == "__main__":
    main()