# src/data_sources/radar_ideam.py
"""
Cliente para Radar IDEAM desde AWS S3.

IDEAM (Instituto de Hidrología, Meteorología y Estudios Ambientales) 
proporciona datos de radar en formato binario en AWS S3.

Bucket: s3-radaresideam (acceso público)
Región: us-east-1
Formato: Archivos RAW binarios procesables con Py-ART

Documentación:
- AWS Registry: https://registry.opendata.aws/ideam-radares/
- Py-ART: https://docs.openradarscience.org/
- XRADAR: https://docs.openradarscience.org/projects/xradar/

Acceso SIN AWS credentials (públicamente):
aws s3 ls --no-sign-request s3://s3-radaresideam/
"""

import boto3
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

try:
    import pyart  # Py-ART para procesamiento de radar
    HAS_PYART = True
except ImportError:
    HAS_PYART = False
    logger.warning("pyart no está instalado. Instala con: pip install arm-pyart")

class RadarIDEAMClient:
    """Cliente para datos de Radar IDEAM desde AWS S3."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config or {}
        self.bucket = config.get("bucket", "s3-radaresideam")
        self.region = config.get("region", "us-east-1")
        self.timeout = config.get("timeout", 30)
        
        # Cliente S3 sin credenciales (acceso público)
        self.s3_client = boto3.client(
            's3',
            region_name=self.region,
            config=boto3.session.Config(
                signature_version=boto3.UNSIGNED  # Acceso público
            )
        )
        
        logger.info(f"RadarIDEAMClient inicializado para bucket {self.bucket}")
    
    def list_available_scans(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """
        Lista archivos de radar disponibles en las últimas N horas.
        
        Returns:
            Lista de dicts con {key, timestamp, size}
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket,
                MaxKeys=1000
            )
            
            if 'Contents' not in response:
                logger.warning("No se encontraron archivos en el bucket")
                return []
            
            cutoff = datetime.utcnow() - timedelta(hours=hours_back)
            available = []
            
            for obj in response['Contents']:
                key = obj['Key']
                modified = obj['LastModified'].replace(tzinfo=None)
                
                # Filtrar archivos recientes
                if modified > cutoff:
                    available.append({
                        "key": key,
                        "timestamp": modified.isoformat(),
                        "size": obj['Size'],
                        "date": modified.date().isoformat(),
                        "time": modified.time().isoformat()
                    })
            
            logger.info(f"✓ {len(available)} scans disponibles en últimas {hours_back}h")
            return sorted(available, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error listando scans: {e}")
            return []
    
    def get_latest_scan(self, location: str = "medellin") -> Optional[Dict[str, Any]]:
        """
        Obtiene el scan de radar más reciente.
        
        Args:
            location: "medellin", "bogota", etc.
        
        Returns:
            Diccionario con datos del radar procesados
        """
        try:
            scans = self.list_available_scans(hours_back=3)  # Últimas 3 horas
            
            if not scans:
                logger.warning("No hay scans recientes disponibles")
                return None
            
            # Obtener el más reciente
            latest_scan = scans
            logger.info(f"Procesando scan: {latest_scan['key']}")
            
            # Descargar y procesar
            radar_data = self._download_and_process_scan(latest_scan['key'])
            
            return {
                "timestamp": latest_scan['timestamp'],
                "location": location,
                "source": "ideam_radar",
                "data": radar_data
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo último scan: {e}")
            return None
    
    def _download_and_process_scan(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Descarga archivo binario de radar desde S3 y extrae información.
        
        Usa Py-ART si está disponible para procesamiento completo.
        """
        try:
            # Descargar archivo temporal
            tmp_file = f"/tmp/radar_{datetime.utcnow().timestamp()}.raw"
            
            logger.info(f"Descargando {s3_key} desde S3...")
            self.s3_client.download_file(self.bucket, s3_key, tmp_file)
            logger.info(f"✓ Descargado: {tmp_file}")
            
            if HAS_PYART:
                return self._process_with_pyart(tmp_file)
            else:
                return self._process_raw_binary(tmp_file)
            
        except Exception as e:
            logger.error(f"Error descargando/procesando: {e}")
            return None
    
    def _process_with_pyart(self, filepath: str) -> Dict[str, Any]:
        """
        Procesa archivo de radar usando Py-ART.
        
        Extrae:
        - Reflectividad (dBZ)
        - Velocidad radial (m/s)
        - Ancho espectral
        - Precipitación estimada
        """
        try:
            # Leer archivo de radar
            radar = pyart.io.read(filepath)
            
            # Extraer campos principales
            data = {
                "radar_fields": list(radar.fields.keys()),
                "range": {
                    "min": float(radar.range['data'].min()),
                    "max": float(radar.range['data'].max()),
                    "units": radar.range['units']
                },
                "reflectivity": {
                    "min": float(radar.fields['reflectivity']['data'].min()),
                    "max": float(radar.fields['reflectivity']['data'].max()),
                    "mean": float(np.nanmean(radar.fields['reflectivity']['data']))
                },
                "sweep_count": radar.nsweeps,
                "azimuth": {
                    "min": float(radar.azimuth['data'].min()),
                    "max": float(radar.azimuth['data'].max())
                }
            }
            
            # Si hay datos de velocidad
            if 'velocity' in radar.fields:
                vel_data = radar.fields['velocity']['data']
                data["velocity"] = {
                    "min": float(np.nanmin(vel_data)),
                    "max": float(np.nanmax(vel_data)),
                    "mean": float(np.nanmean(vel_data))
                }
            
            logger.info(f"✓ Radar procesado: {len(data)} campos extraídos")
            return data
            
        except Exception as e:
            logger.error(f"Error con Py-ART: {e}")
            return {"error": str(e)}
    
    def _process_raw_binary(self, filepath: str) -> Dict[str, Any]:
        """
        Procesa archivo binario sin Py-ART (solo información básica).
        """
        try:
            file_size = Path(filepath).stat().st_size
            
            logger.warning("Py-ART no disponible. Información básica solamente.")
            
            return {
                "file_path": filepath,
                "file_size_bytes": file_size,
                "status": "raw_binary",
                "info": "Instala arm-pyart para procesamiento completo",
                "install_cmd": "pip install arm-pyart"
            }
            
        except Exception as e:
            logger.error(f"Error procesando binario: {e}")
            return {"error": str(e)}
    
    def get_precipitation_estimate(self, reflectivity: float) -> float:
        """
        Estima precipitación desde reflectividad (dBZ).
        
        Usa relación Marshall-Palmer: Z = 200 * R^1.6
        Inversa: R = (Z/200)^(1/1.6)
        
        Args:
            reflectivity: Reflectividad en dBZ
        
        Returns:
            Tasa de precipitación estimada en mm/h
        """
        try:
            # Relación Marshall-Palmer inversa
            z_linear = 10 ** (reflectivity / 10)  # Convertir de dBZ a Z
            rain_rate = (z_linear / 200.0) ** (1.0 / 1.6)
            return max(0, rain_rate)  # No permitir valores negativos
        except Exception as e:
            logger.error(f"Error estimando precipitación: {e}")
            return 0.0
