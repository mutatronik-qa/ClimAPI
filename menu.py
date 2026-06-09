"""
CLIMAPI - Menú Interactivo (Refactorizado)
==========================================
Utiliza el servicio centralizado (WeatherService) para garantizar
consistencia y rendimiento.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Añadir el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

# Importar servicio centralizado
from backend.weather_service import get_service

def print_banner():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                          CLIMAPI                              ║
    ║         Sistema Integrado de Datos Climáticos                 ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

def menu_principal():
    """Menú principal interactivo utilizando WeatherService."""
    load_dotenv()
    service = get_service()
    
    # Ubicaciones predefinidas de Colombia
    ubicaciones = {
        "1": {"name": "Medellín", "lat": 6.244, "lon": -75.581, "asl": 1495},
        "2": {"name": "Bogotá", "lat": 4.711, "lon": -74.072, "asl": 2640},
        "3": {"name": "Cartagena", "lat": 10.391, "lon": -75.479, "asl": 2},
        "4": {"name": "Cali", "lat": 3.451, "lon": -76.532, "asl": 995},
        "5": {"name": "Barranquilla", "lat": 10.963, "lon": -74.796, "asl": 18},
    }
    
    while True:
        print("\n" + "="*70)
        print("CLIMAPI - Panel de Control Interactivo")
        print("="*70)
        print("\n1. Consulta unificada (Todas las fuentes)")
        print("2. Consultar fuente específica")
        print("3. Verificar integridad de las APIs")
        print("4. Ver historial de consultas")
        print("5. Limpiar caché")
        print("6. Salir")
        
        opcion = input("\nSeleccione una opción: ").strip()
        
        if opcion == "6":
            print("\n👋 ¡Hasta luego!")
            break
            
        if opcion in ["1", "2"]:
            # Selección de ubicación
            print("\nUbicaciones rápidas:")
            for key, loc in ubicaciones.items():
                print(f"{key}. {loc['name']}")
            print("6. Manual (Coordenadas)")
            
            loc_opcion = input("\nUbicación: ").strip()
            
            if loc_opcion in ubicaciones:
                loc = ubicaciones[loc_opcion]
                lat, lon, name = loc["lat"], loc["lon"], loc["name"]
            elif loc_opcion == "6":
                name = input("Nombre: ")
                lat = float(input("Latitud: "))
                lon = float(input("Longitud: "))
            else:
                print("❌ Opción inválida")
                continue

            source = None
            if opcion == "2":
                from backend.sources import SOURCES
                print("\nFuentes disponibles:")
                for i, s in enumerate(SOURCES.keys(), 1):
                    print(f"{i}. {s}")
                s_idx = int(input("\nSeleccione fuente (número): ")) - 1
                source = list(SOURCES.keys())[s_idx]

            if source in ["siata", "ideam-radar"]:
                print(f"\n📡 Actualizando datos regionales/red ({source})...")
            else:
                print(f"\n📡 Consultando datos para {name}...")
                
            result = service.get_weather(lat, lon, source=source)
            
            if result.get("error"):
                print(f"❌ Error: {result['error']}")
            else:
                print(f"\n✅ Resultados ({result.get('source', 'múltiple')}):")
                print(f"   🌡️  Temperatura: {result.get('temperature')}°C")
                print(f"   💧  Humedad:    {result.get('humidity')}%")
                print(f"   🌧️  Lluvia:     {result.get('precipitation')} mm")
                print(f"   💨  Viento:     {result.get('wind_speed')} km/h")
                
                # Guardar automáticamente
                service.save_data(result)
                print("\n💾 Datos guardados en el historial.")

        elif opcion == "3":
            print("\n🔍 Verificando integridad de las APIs...")
            status = service.get_sources_status(fast=True)
            print("\nEstado de las fuentes:")
            for s in status:
                icon = "✅" if s["available"] else "❌"
                print(f" {icon} {s['name'].ljust(15)} | Latencia: {s['response_time']:.3f}s | {s.get('error') or 'OK'}")

        elif opcion == "4":
            print("\n📋 Últimas 10 consultas en historial:")
            import pandas as pd
            from dashboard.app import _load_source_history
            hist = _load_source_history("combined", limit=10)
            if hist is not None:
                print(hist[["timestamp", "temperature", "source"]])
            else:
                print("No hay datos en el historial.")

        elif opcion == "5":
            service.clear_cache()
            print("\n🧹 Caché de sistema y salud limpiado.")

        input("\nPresione ENTER para volver al menú...")

if __name__ == "__main__":
    print_banner()
    menu_principal()
