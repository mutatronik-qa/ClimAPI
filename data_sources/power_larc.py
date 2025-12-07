# src/data_sources/power_larc.py
"""Cliente para NASA POWER API (LARC)"""

import requests

class NASAPOWERClient:
    def __init__(self, config: Dict[str, Any]):
        self.base_url = "https://power.larc.nasa.gov/api/v1/aggregate"
    
    def get_power_data(self, lat: float, lon: float, start: str, end: str) -> Dict:
        """
        Obtiene datos de irradiancia y meteorología.
        
        start/end formato: "YYYYMMdd"
        """
        params = {
            "longitude": lon,
            "latitude": lat,
            "start": start,
            "end": end,
            "community": "SB",
            "parameters": "ALLSKY_SFC_SW_DWN,T2M,RH2M,WS10M",
            "format": "JSON"
        }
        
        response = requests.get(self.base_url, params=params, timeout=15)
        return response.json()
