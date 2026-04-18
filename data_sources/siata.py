"""
Cliente para datos del SIATA (Sistema de Alerta Temprana Medellín).

SIATA proporciona datos meteorológicos, hidrológicos y de calidad del aire
para Medellín y el Valle de Aburrá.

Métodos de acceso:
1. REST API: https://www.siata.gov.co/api/ (si disponible)
2. Web Scraping: https://www.siata.gov.co/operacional/
3. WMS/WFS: Si proporciona servicios geoespaciales
"""

import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class SIATAClient:
    """
    Cliente para acceder a datos del SIATA.
    
    Soporta múltiples métodos de obtención de datos:
    - REST API directo (si está disponible)
    - Web scraping del portal operacional
    - Fallback a datos estáticos
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa cliente SIATA.
        
        Args:
            config: Diccionario con:
                - api_url: URL base del SIATA (default: https://www.siata.gov.co)
                - timeout: Timeout para requests (default: 15s)
                - retry_attempts: Intentos de reconexión (default: 3)
        """
        self.config = config or {}
        self.base_url = config.get("api_url", "https://www.siata.gov.co")
        self.operacional_url = config.get(
            "operational_url",
            f"{self.base_url.rstrip('/')}/operacional/"
        )
        self.timeout = config.get("timeout", 15)
        self.retry_attempts = config.get("retry_attempts", 3)
        self.session = requests.Session()
        
        logger.info(f"SIATAClient inicializado con URL: {self.base_url}")
    
    def get_weather_current(self, location: str = "medellin") -> Optional[Dict[str, Any]]:
        """
        Obtiene datos meteorológicos actuales.
        
        Args:
            location: Ubicación ("medellin", "bello", "envigado", etc.)
        
        Returns:
            Diccionario con:
            {
                "timestamp": "2025-12-07T...",
                "temperature": 22.5,
                "humidity": 65.0,
                "precipitation": 0.5,
                "wind_speed": 3.2,
                "source": "siata"
            }
        """
        try:
            # Intentar API REST primero
            logger.debug(f"Intentando obtener datos SIATA para {location}...")
            weather_data = self._fetch_from_api(location)
            if weather_data:
                logger.info(f"✓ Datos obtenidos desde API SIATA")
                return weather_data
            
            # Fallback: web scraping
            logger.debug("API no disponible. Intentando web scraping...")
            weather_data = self._scrape_weather_data()
            if weather_data:
                logger.info(f"✓ Datos obtenidos por web scraping")
                return weather_data
            
            logger.warning(f"No se pudieron obtener datos SIATA para {location}")
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo datos SIATA: {e}", exc_info=True)
            return None
    
    def _fetch_from_api(self, location: str) -> Optional[Dict[str, Any]]:
        """
        Intenta obtener datos desde API REST del SIATA.
        
        Prueba múltiples endpoints conocidos:
        - https://www.siata.gov.co/api/v1/weather/{location}
        - https://www.siata.gov.co/api/weather/current
        - https://www.siata.gov.co/rest/Stations
        """
        try:
            endpoints = [
                f"{self.base_url}/api/v1/weather/{location}",
                f"{self.base_url}/api/weather/current",
                f"{self.base_url}/rest/Stations",
            ]
            
            for endpoint in endpoints:
                try:
                    logger.debug(f"Probando endpoint: {endpoint}")
                    response = self.session.get(endpoint, timeout=self.timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"✓ Respuesta exitosa de {endpoint}")
                        return self._normalize_siata_response(data)
                        
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} no disponible: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error en _fetch_from_api: {e}", exc_info=True)
            return None
    
    def _scrape_weather_data(self) -> Optional[Dict[str, Any]]:
        """
        Extrae datos meteorológicos mediante web scraping.
        
        Accede a https://www.siata.gov.co/operacional/ y busca
        elementos HTML comunes en dashboards meteorológicos.
        """
        try:
            logger.debug(f"Accediendo a {self.operacional_url}...")
            response = self.session.get(self.operacional_url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            weather_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "source": "siata_scrape",
                "data": {}
            }
            
            # Buscar temperatura
            # Busca patrones como: <span class="temp">22.5°C</span>
            temp_patterns = [
                ('temperature|temp', 'Temperatura'),
                ('humidity|humedad', 'Humedad'),
                ('precipitation|precipitación|lluvia', 'Precipitación'),
                ('wind|viento|velocidad', 'Viento'),
            ]
            
            for pattern, name in temp_patterns:
                elements = soup.find_all(re.compile(pattern, re.IGNORECASE))
                if elements:
                    try:
                        text = elements.get_text(strip=True)
                        # Extraer número flotante
                        match = re.search(r'(\d+\.?\d*)', text)
                        if match:
                            value = float(match.group(1))
                            key = pattern.split('|')
                            weather_data["data"][key] = value
                            logger.debug(f"  {name}: {value}")
                    except (ValueError, AttributeError):
                        pass
            
            if weather_data["data"]:
                logger.info(f"✓ Datos extraídos por web scraping: {weather_data['data']}")
                return weather_data
            
            logger.warning("No se encontraron datos en el HTML")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error de conexión en web scraping: {e}")
            return None
        except Exception as e:
            logger.error(f"Error en web scraping: {e}", exc_info=True)
            return None
    
    def _normalize_siata_response(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza respuesta del SIATA al esquema estándar.
        
        Mapea campos variables del SIATA a nombres estándar.
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "temperature": raw_data.get("temperature") or raw_data.get("temp"),
            "humidity": raw_data.get("humidity") or raw_data.get("humedad"),
            "precipitation": raw_data.get("precipitation") or raw_data.get("precipitacion"),
            "wind_speed": raw_data.get("wind_speed") or raw_data.get("viento"),
            "source": "siata",
            "raw": raw_data
        }
    
    def get_stations_info(self) -> List[Dict[str, Any]]:
        """
        Obtiene información de estaciones meteorológicas del SIATA.
        
        Returns:
            Lista de estaciones con nombre, ubicación, variables, etc.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/rest/Stations",
                timeout=self.timeout
            )
            if response.status_code == 200:
                stations = response.json()
                logger.info(f"✓ {len(stations)} estaciones obtenidas")
                return stations
            return []
        except Exception as e:
            logger.error(f"Error obteniendo estaciones: {e}")
            return []
    
    def get_air_quality(self, location: str = "medellin") -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de calidad del aire si están disponibles.
        
        Args:
            location: Ubicación específica
        
        Returns:
            Diccionario con índices de calidad del aire (AQI, PM2.5, PM10, O3, etc.)
        """
        try:
            endpoints = [
                f"{self.base_url}/api/v1/air-quality/{location}",
                f"{self.base_url}/api/quality/current",
            ]
            
            for endpoint in endpoints:
                try:
                    response = self.session.get(endpoint, timeout=self.timeout)
                    if response.status_code == 200:
                        return response.json()
                except Exception as e:
                    logger.debug(f"Endpoint {endpoint} no disponible: {e}")
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo calidad del aire: {e}")
            return None
