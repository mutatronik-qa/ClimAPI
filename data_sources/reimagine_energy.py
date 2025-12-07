# src/data_sources/reimagine_energy.py
"""Cliente para Reimagine Energy"""

class ReimagineEnergyClient:
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key")
        self.base_url = "https://api.reimagine-energy.ai/v1"
    
    def get_solar_forecast(self, lat: float, lon: float, hours: int = 48) -> Dict:
        """Pronóstico de generación solar para horas próximas."""
        # Implementación específica según documentación
        pass
