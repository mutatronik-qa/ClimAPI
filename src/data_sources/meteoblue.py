import hashlib
import hmac
import requests
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from urllib.parse import quote
from dotenv import load_dotenv


class MeteoblueClient:
    """Cliente para consumir los datos de la API de Meteoblue"""
    
    def __init__(self, api_key: str, shared_secret: Optional[str] = None, 
                 data_dir: str = "data"):
        """
        Inicializa el cliente de Meteoblue
        
        Args:
            api_key: Tu API key de Meteoblue
            shared_secret: Secret compartido para firmar requests (opcional)
            data_dir: Directorio base para guardar datos e imágenes
        """
        self.api_key = api_key
        self.shared_secret = shared_secret
        self.base_url = "https://my.meteoblue.com"
        self.data_dir = Path(data_dir)
        
        # Crear directorios si no existen
        self.images_dir = self.data_dir / "images_meteo_blue"
        self.meteoblue_dir = self.data_dir / "data_meteoblue"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.meteoblue_dir.mkdir(parents=True, exist_ok=True)
    
    def _sign_url(self, query: str, expire: Optional[int] = None) -> str:
        """
        Firma una URL con HMAC-SHA256
        
        Args:
            query: Query string a firmar (debe incluir el path y expire)
            expire: Timestamp de expiración (ya debe estar en query)
            
        Returns:
            URL firmada completa
        """
        if not self.shared_secret:
            print("⚠️  ADVERTENCIA: No se proporcionó shared_secret. La API puede rechazar la solicitud.")
            return f"{self.base_url}{query}"
        
        # Calcular firma
        sig = hmac.new(
            self.shared_secret.encode(), 
            query.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return f"{self.base_url}{query}&sig={sig}"
    
    def _signed_query_for_meteogram(self, lat, lon, asl, city, tz="America/Bogota", 
                                    lang="es", dpi=72, look="CELSIUS_MILLIMETER_KILOMETER_PER_HOUR"):
        """Genera una URL firmada para descargar un meteograma (método seguro)."""
        expire = int((datetime.now() + timedelta(minutes=10)).timestamp())
        city_enc = quote(city, safe="")
        tz_enc = quote(tz, safe="")

        query = (
            f"/images/meteogram?lat={lat}&lon={lon}&asl={asl}"
            f"&tz={tz_enc}&apikey={self.api_key}&expire={expire}"
            f"&format=png&dpi={dpi}&lang={lang}&look={look}&city={city_enc}"
        )

        if not self.shared_secret:
            return f"{self.base_url}{query}&secret_share=climapi"

        sig = hmac.new(
            self.shared_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{self.base_url}{query}&sig={sig}"
    
    def get_forecast(self, lat: float, lon: float, asl: int = 0, 
                     expire: Optional[int] = None, 
                     save_data: bool = True,
                     location_name: str = "location") -> Dict[str, Any]:
        """
        Obtiene el pronóstico del tiempo para una ubicación
        
        Args:
            lat: Latitud
            lon: Longitud
            asl: Altitud sobre el nivel del mar (metros)
            expire: Timestamp de expiración (opcional)
            save_data: Si guardar los datos en JSON
            location_name: Nombre de la ubicación para el archivo
            
        Returns:
            Diccionario con los datos del pronóstico
        """
        # Generar expire si no se proporciona
        if expire is None:
            expire = int((datetime.now() + timedelta(days=365)).timestamp())
        
        # Construir query string (ORDEN EXACTO según documentación de Meteoblue)
        query = f"/packages/basic-day?lat={lat}&lon={lon}&asl={asl}&format=json&apikey={self.api_key}&expire={expire}"
        
        # Firmar URL
        url = self._sign_url(query, expire=expire)
        
        # Hacer request
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Guardar datos si se solicita
        if save_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"forecast_{location_name.lower().replace(' ', '_')}_{timestamp}.json"
            filepath = self.meteoblue_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"📊 Datos guardados en: {filepath}")
        
        return data
    
    def get_meteogram_image(self, lat: float, lon: float, asl: int = 0,
                           location_name: str = "Location",
                           timezone: str = "America/Bogota",
                           temp_units: str = "C",
                           precip_units: str = "mm",
                           wind_units: str = "kmh",
                           lang: str = "en",
                           dpi: int = 72,
                           expire: Optional[int] = None,
                           save_image: bool = True) -> bytes:
        """
        Obtiene la imagen del meteograma para una ubicación
        
        Args:
            lat: Latitud
            lon: Longitud
            asl: Altitud sobre el nivel del mar (metros)
            location_name: Nombre de la ubicación
            timezone: Zona horaria
            temp_units: Unidades de temperatura (C, F)
            precip_units: Unidades de precipitación (mm, inch)
            wind_units: Unidades de viento (kmh, mph, ms, kn, bft)
            lang: Idioma (en, es, de, fr, etc.)
            dpi: DPI de la imagen
            expire: Timestamp de expiración (opcional)
            save_image: Si guardar la imagen automáticamente
            
        Returns:
            Bytes de la imagen PNG
        """
        # Generar expire si no se proporciona
        if expire is None:
            expire = int((datetime.now() + timedelta(days=365)).timestamp())
        
        # CRÍTICO: URL-encode el location_name ANTES de incluirlo en la query para la firma
        # Pero mantener la query sin encodear para la firma
        location_encoded = quote(location_name)
        
        # Construir query string SIN encodear para la firma
        query = (f"/images/meteogram?lat={lat}&lon={lon}&asl={asl}"
                f"&tz={timezone}&apikey={self.api_key}&expire={expire}"
                f"&format=png&dpi={dpi}&lang={lang}"
                f"&temperature_units={temp_units}&precipitation_units={precip_units}"
                f"&windspeed_units={wind_units}&location_name={location_name}")
        
        # Firmar URL
        url = self._sign_url(query, expire=expire)
        
        # Hacer request
        response = requests.get(url)
        response.raise_for_status()
        
        image_data = response.content
        
        # Guardar imagen si se solicita
        if save_image:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meteogram_{location_name.lower().replace(' ', '_')}_{timestamp}.png"
            filepath = self.images_dir / filename
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            print(f"🖼️  Imagen guardada en: {filepath}")
        
        return image_data
    
    def get_weather_summary(self, lat: float, lon: float, asl: int = 0,
                           location_name: str = "Location",
                           days: int = 7) -> Dict[str, Any]:
        """
        Obtiene un resumen completo del clima con todos los datos disponibles
        
        Args:
            lat: Latitud
            lon: Longitud
            asl: Altitud sobre el nivel del mar (metros)
            location_name: Nombre de la ubicación
            days: Número de días a mostrar (por defecto 7)
            
        Returns:
            Diccionario con resumen del clima
        """
        forecast = self.get_forecast(lat, lon, asl, save_data=False, location_name=location_name)
        
        summary = {
            "location": location_name,
            "coordinates": {"lat": lat, "lon": lon, "asl": asl},
            "forecast": []
        }
        
        if 'data_day' in forecast:
            data = forecast['data_day']
            num_days = min(days, len(data.get('time', [])))
            
            for i in range(num_days):
                day_data = {
                    "date": data['time'][i],
                    "temperature": {
                        "max": data.get('temperature_max', [None])[i],
                        "min": data.get('temperature_min', [None])[i],
                        "mean": data.get('temperature_mean', [None])[i]
                    },
                    "wind": {
                        "speed_mean": data.get('windspeed_mean', [None])[i],
                        "speed_max": data.get('windspeed_max', [None])[i],
                        "direction": data.get('winddirection', [None])[i]
                    },
                    "precipitation": data.get('precipitation', [None])[i],
                    "precipitation_probability": data.get('precipitation_probability', [None])[i],
                    "humidity": data.get('humidity_mean', [None])[i],
                    "pressure": data.get('pressure_mean', [None])[i],
                    "cloudcover": data.get('cloudcover', [None])[i]
                }
                summary["forecast"].append(day_data)
        
        return summary


# Ejemplo de uso
if __name__ == "__main__":
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener configuración desde variables de entorno
    API_KEY = os.getenv("METEOBLUE_API_KEY")
    SHARED_SECRET = os.getenv("METEOBLUE_SHARED_SECRET")
    BASE_URL = os.getenv("METEOBLUE_BASE_URL", "https://my.meteoblue.com")
    
    # Validar configuración
    if not API_KEY or not SHARED_SECRET:
        print("=" * 60)
        print("❌ ERROR DE CONFIGURACIÓN")
        print("=" * 60)
        print("\nFaltan variables de entorno requeridas.")
        print("\n📖 Pasos para configurar:")
        print("1. Copia el archivo .env.example a .env")
        print("   cp .env.example .env")
        print("2. Edita .env y añade tus credenciales:")
        print("   METEOBLUE_API_KEY=tu_api_key")
        print("   METEOBLUE_SHARED_SECRET=tu_shared_secret")
        print("\n⚠️  IMPORTANTE: Nunca subas el archivo .env a git")
        print("=" * 60)
        exit(1)
    
    # Crear cliente
    client = MeteoblueClient(API_KEY, SHARED_SECRET)
    
    # Definir ubicaciones
    locations = [
        {"name": "Medellin", "lat": 6.245, "lon": -75.5715, "asl": 1405},
        {"name": "Bogota", "lat": 4.711, "lon": -74.0721, "asl": 2640},
        {"name": "Cartagena", "lat": 10.391, "lon": -75.4794, "asl": 2},
    ]
    
    # Consultar pronóstico para cada ubicación
    print("=" * 60)
    print("PRONÓSTICOS DEL TIEMPO")
    print("=" * 60)
    
    for location in locations:
        print(f"\n📍 {location['name']}")
        print("-" * 60)
        
        try:
            # Obtener pronóstico
            forecast = client.get_forecast(
                lat=location['lat'],
                lon=location['lon'],
                asl=location['asl'],
                save_data=True,
                location_name=location['name']
            )
            
            # Mostrar información básica
            if 'data_day' in forecast:
                data = forecast['data_day']
                print(f"Fecha inicio: {data['time'][0]}")
                print(f"Temperatura máxima: {data['temperature_max'][0]}°C")
                print(f"Temperatura mínima: {data['temperature_min'][0]}°C")
                print(f"Precipitación: {data.get('precipitation', [0])[0]} mm")
                
                # Velocidad del viento
                if 'windspeed_mean' in data:
                    print(f"Velocidad viento (media): {data['windspeed_mean'][0]} km/h")
                if 'windspeed_max' in data:
                    print(f"Velocidad viento (máxima): {data['windspeed_max'][0]} km/h")
                if 'winddirection' in data:
                    print(f"Dirección del viento: {data['winddirection'][0]}°")
                
                # Información adicional si está disponible
                if 'humidity_mean' in data:
                    print(f"Humedad media: {data['humidity_mean'][0]}%")
                if 'pressure_mean' in data:
                    print(f"Presión atmosférica: {data['pressure_mean'][0]} hPa")
            
            # Descargar meteograma
            client.get_meteogram_image(
                lat=location['lat'],
                lon=location['lon'],
                asl=location['asl'],
                location_name=location['name'],
                save_image=True
            )
            
        except requests.exceptions.HTTPError as e:
            print(f"❌ Error al consultar: {e}")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
    
    print("\n" + "=" * 60)
    print("Consultas completadas")
    print("=" * 60)
