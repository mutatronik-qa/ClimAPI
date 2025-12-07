# src/data_sources/nsrdb_nasa.py
"""Cliente para NSRDB NASA"""

import requests
from typing import Dict, Any

class NSRDBClient:
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key")  # Registro gratis en nsrdb.nrel.gov
        self.base_url = "https://developer.nrel.gov/api/nsrdb/v2/solar"
    
    def get_solar_data(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Obtiene datos de radiación solar.
        
        Retorna: irradiance (W/m²), clearsky_ghi, etc.
        """
        params = {
            "api_key": self.api_key,
            "lat": lat,
            "lon": lon,
            "attributes": ["ghi", "dni", "dhi"],
            "leap_year": "false",
            "interval": "30",  # minutos
            "full_name": "ClimAPI User",
            "email": "user@climapi.com",
            "mailing_list": False,
            "reason": "Research"
        }
        
        response = requests.get(self.base_url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
