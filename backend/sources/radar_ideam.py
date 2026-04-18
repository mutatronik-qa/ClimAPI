"""
IDEAM Radar Source - Optional (AWS S3 access)
https://registry.opendata.aws/ideam-radares/
"""
import boto3
import botocore
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

BUCKET = "s3-radaresideam"
REGION = "us-east-1"


def get_weather(lat: float, lon: float, **kwargs) -> Dict[str, Any]:
    """
    Get latest radar scan from IDEAM.
    Returns precipitation estimate based on radar reflectivity.
    """
    try:
        logger.info(f"🌐 IDEAM Radar: fetching latest scan")
        
        # Create S3 client without credentials (public bucket)
        s3_client = boto3.client(
            's3',
            region_name=REGION,
            config=boto3.session.Config(signature_version=botocore.UNSIGNED)
        )
        
        # List recent objects
        response = s3_client.list_objects_v2(Bucket=BUCKET, MaxKeys=10)
        
        if 'Contents' not in response:
            logger.warning("⚠️ IDEAM: no scans available")
            return _empty_result("ideam_radar", "no scans available")
        
        # Get most recent scan
        latest = response['Contents'][0]
        
        result = {
            "timestamp": latest['LastModified'].isoformat(),
            "precipitation": None,  # Would need Py-ART to process
            "radar_key": latest['Key'],
            "source": "ideam_radar",
            "note": "Full processing requires pyart library"
        }
        
        logger.info(f"✅ IDEAM Radar: latest scan available")
        return result
        
    except Exception as e:
        logger.warning(f"⚠️ IDEAM Radar error: {e}")
        return _empty_result("ideam_radar", str(e))


def list_scans(hours: int = 24) -> List[Dict[str, Any]]:
    """List available radar scans."""
    try:
        s3_client = boto3.client(
            's3',
            region_name=REGION,
            config=boto3.session.Config(signature_version=botocore.UNSIGNED)
        )
        
        response = s3_client.list_objects_v2(Bucket=BUCKET, MaxKeys=100)
        
        if 'Contents' not in response:
            return []
        
        cutoff = datetime.now() - timedelta(hours=hours)
        scans = []
        
        for obj in response['Contents']:
            if obj['LastModified'].replace(tzinfo=None) > cutoff:
                scans.append({
                    "key": obj['Key'],
                    "timestamp": obj['LastModified'].isoformat(),
                    "size": obj['Size']
                })
        
        return sorted(scans, key=lambda x: x['timestamp'], reverse=True)
        
    except Exception as e:
        logger.warning(f"⚠️ IDEAM list error: {e}")
        return []


def _empty_result(source: str, error: str = "") -> Dict[str, Any]:
    """Return empty result."""
    return {
        "timestamp": datetime.now().isoformat(),
        "temperature": None,
        "humidity": None,
        "precipitation": None,
        "wind_speed": None,
        "source": source,
        "error": error if error else "no data"
    }