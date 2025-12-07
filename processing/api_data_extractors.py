"""
Extractores específicos para cada API.
Obtiene datos de cada fuente y los guarda en CSV separados y normalizados.
"""
import pandas as pd
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
import json

from data_sources.open_meteo import get_weather_data
from data_sources.openweathermap import OpenWeatherMap
from processing.data_normalizer import DataNormalizer
from processing.data_quality_report import DataQualityReport

logger = logging.getLogger(__name__)

class APIDataExtractor:
    """Extrae datos de cada API y los guarda por separado."""
    
    def __init__(self, output_dir: Path = Path("data/raw_api_data")):
        """
        Inicializa el extractor.
        
        Args:
            output_dir: Directorio donde guardar los datos por API
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectorios para cada API
        self.dirs = {
            "open-meteo": self.output_dir / "open-meteo",
            "openweathermap": self.output_dir / "openweathermap",
            "meteoblue": self.output_dir / "meteoblue",
            "siata": self.output_dir / "siata",
            "radar_ideam": self.output_dir / "radar_ideam",
            "normalized": self.output_dir / "normalized",
            "reports": self.output_dir / "reports",
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def extract_openmeteo(self, lat: float, lon: float, timezone: str = "America/Bogota", 
                         city: str = "Medellín") -> Tuple[pd.DataFrame, Dict]:
        """
        Extrae datos de Open-Meteo.
        
        Returns:
            (DataFrame normalizado, metadatos)
        """
        logger.info(f"🔄 Extrayendo datos de Open-Meteo ({lat}, {lon})...")
        
        try:
            # Obtener datos raw
            raw_response = get_weather_data(lat, lon, timezone)
            
            # Guardar respuesta raw
            raw_file = self.dirs["open-meteo"] / f"raw_{datetime.now().isoformat()}.json"
            with open(raw_file, 'w') as f:
                json.dump(raw_response, f, indent=2, default=str)
            logger.info(f"   ✓ Datos raw guardados en: {raw_file}")
            
            # Normalizar
            df = DataNormalizer.normalize_openmeteo(raw_response, lat, lon, city)
            
            if df.empty:
                logger.warning("   ⚠️  DataFrame normalizado está vacío")
                return df, {"status": "empty"}
            
            # Guardar CSV normalizado
            csv_file = self.dirs["open-meteo"] / f"normalized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"   ✓ CSV normalizado guardado: {csv_file}")
            
            # Generar reporte de calidad
            quality_report = DataQualityReport.generate(df, "open-meteo")
            report_file = self.dirs["reports"] / f"open-meteo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(quality_report, f, indent=2, default=str)
            logger.info(f"   ✓ Reporte de calidad: {report_file}")
            
            metadata = {
                "status": "success",
                "records": len(df),
                "columns": list(df.columns),
                "raw_file": str(raw_file),
                "csv_file": str(csv_file),
                "report_file": str(report_file),
                "date_range": {
                    "start": str(df["timestamp"].min()) if "timestamp" in df.columns else None,
                    "end": str(df["timestamp"].max()) if "timestamp" in df.columns else None,
                }
            }
            
            return df, metadata
        
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo Open-Meteo: {e}", exc_info=True)
            return pd.DataFrame(), {"status": "error", "error": str(e)}
    
    def extract_openweathermap(self, city: str = "Medellín", 
                              api_key: Optional[str] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Extrae datos de OpenWeatherMap.
        
        Returns:
            (DataFrame normalizado, metadatos)
        """
        logger.info(f"🔄 Extrayendo datos de OpenWeatherMap ({city})...")
        
        try:
            # Crear cliente
            owm_config = {
                "api_key": api_key or "demo",
                "units": "metric"
            }
            owm_client = OpenWeatherMap(owm_config)
            
            # Obtener datos raw
            raw_response = owm_client.get_weather_data(city)
            
            # Guardar respuesta raw
            raw_file = self.dirs["openweathermap"] / f"raw_{city}_{datetime.now().isoformat()}.json"
            with open(raw_file, 'w') as f:
                json.dump(raw_response, f, indent=2, default=str)
            logger.info(f"   ✓ Datos raw guardados en: {raw_file}")
            
            # Normalizar
            df = DataNormalizer.normalize_openweathermap(raw_response, city)
            
            if df.empty:
                logger.warning("   ⚠️  DataFrame normalizado está vacío")
                return df, {"status": "empty"}
            
            # Guardar CSV normalizado
            csv_file = self.dirs["openweathermap"] / f"normalized_{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"   ✓ CSV normalizado guardado: {csv_file}")
            
            # Generar reporte de calidad
            quality_report = DataQualityReport.generate(df, "openweathermap")
            report_file = self.dirs["reports"] / f"openweathermap_{city}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(quality_report, f, indent=2, default=str)
            logger.info(f"   ✓ Reporte de calidad: {report_file}")
            
            metadata = {
                "status": "success",
                "records": len(df),
                "columns": list(df.columns),
                "city": city,
                "raw_file": str(raw_file),
                "csv_file": str(csv_file),
                "report_file": str(report_file),
            }
            
            return df, metadata
        
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo OpenWeatherMap: {e}", exc_info=True)
            return pd.DataFrame(), {"status": "error", "error": str(e)}
    
    def extract_siata(self, lat: float = 6.244, lon: float = -75.581) -> Tuple[pd.DataFrame, Dict]:
        """
        Extrae datos de SIATA (si hay archivo CSV disponible).
        
        Returns:
            (DataFrame normalizado, metadatos)
        """
        logger.info(f"🔄 Buscando datos de SIATA...")
        
        try:
            # Buscar archivos SIATA
            siata_files = list(Path("data").glob("*siata*.csv"))
            
            if not siata_files:
                logger.warning("   ⚠️  No se encontraron archivos SIATA")
                return pd.DataFrame(), {"status": "not_found"}
            
            df_combined = None
            for siata_file in siata_files:
                df = pd.read_csv(siata_file)
                
                if df_combined is None:
                    df_combined = df
                else:
                    df_combined = pd.concat([df_combined, df], ignore_index=True)
            
            # Normalizar
            df_normalized = DataNormalizer.normalize_siata(
                df_combined.to_dict('records'), 
                lat, lon, "Medellín"
            )
            
            if df_normalized.empty:
                logger.warning("   ⚠️  DataFrame normalizado está vacío")
                return df_normalized, {"status": "empty"}
            
            # Guardar CSV normalizado
            csv_file = self.dirs["siata"] / f"normalized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df_normalized.to_csv(csv_file, index=False)
            logger.info(f"   ✓ CSV normalizado guardado: {csv_file}")
            
            # Generar reporte
            quality_report = DataQualityReport.generate(df_normalized, "siata")
            report_file = self.dirs["reports"] / f"siata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(quality_report, f, indent=2, default=str)
            logger.info(f"   ✓ Reporte de calidad: {report_file}")
            
            metadata = {
                "status": "success",
                "records": len(df_normalized),
                "source_files": [str(f) for f in siata_files],
                "csv_file": str(csv_file),
                "report_file": str(report_file),
            }
            
            return df_normalized, metadata
        
        except Exception as e:
            logger.error(f"   ❌ Error extrayendo SIATA: {e}", exc_info=True)
            return pd.DataFrame(), {"status": "error", "error": str(e)}
    
    def extract_all(self, lat: float = 6.244, lon: float = -75.581, 
                   city: str = "Medellín", owm_api_key: Optional[str] = None) -> Dict:
        """
        Extrae datos de todas las APIs disponibles.
        
        Returns:
            Dict con resultados por API
        """
        logger.info("=" * 60)
        logger.info("🌐 Extrayendo datos de todas las APIs...")
        logger.info("=" * 60)
        
        results = {}
        
        # Open-Meteo
        logger.info("\n1️⃣  Open-Meteo")
        df_om, meta_om = self.extract_openmeteo(lat, lon, city=city)
        results["open-meteo"] = {
            "dataframe": df_om,
            "metadata": meta_om
        }
        
        # OpenWeatherMap
        logger.info("\n2️⃣  OpenWeatherMap")
        df_owm, meta_owm = self.extract_openweathermap(city, owm_api_key)
        results["openweathermap"] = {
            "dataframe": df_owm,
            "metadata": meta_owm
        }
        
        # SIATA
        logger.info("\n3️⃣  SIATA")
        df_siata, meta_siata = self.extract_siata(lat, lon)
        results["siata"] = {
            "dataframe": df_siata,
            "metadata": meta_siata
        }
        
        # Generar reporte consolidado
        logger.info("\n" + "=" * 60)
        logger.info("📊 Generando reporte consolidado...")
        
        consolidado = {
            "timestamp": datetime.now().isoformat(),
            "location": {"latitude": lat, "longitude": lon, "city": city},
            "apis": {}
        }
        
        for api_name, result in results.items():
            consolidado["apis"][api_name] = result["metadata"]
        
        # Guardar reporte consolidado
        report_file = self.dirs["reports"] / f"consolidado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(consolidado, f, indent=2, default=str)
        logger.info(f"✓ Reporte consolidado: {report_file}")
        
        logger.info("=" * 60)
        logger.info("✅ Extracción completada")
        logger.info("=" * 60)
        
        return results