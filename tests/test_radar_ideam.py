    # tests/test_radar_ideam.py
"""Tests para RadarIDEAMClient."""

import pytest
from unittest.mock import Mock, patch
from data_sources.radar_ideam import RadarIDEAMClient
from datetime import datetime, timedelta


class TestRadarIDEAMClientInitialization:
    """Tests de inicialización."""
    
    def test_radar_init_with_defaults(self):
        """Debe inicializar con defaults."""
        client = RadarIDEAMClient({})
        assert client.bucket == "s3-radaresideam"
        assert client.region == "us-east-1"
    
    def test_radar_init_with_custom_config(self):
        """Debe inicializar con config personalizada."""
        config = {
            "bucket": "custom-bucket",
            "region": "us-west-2"
        }
        client = RadarIDEAMClient(config)
        assert client.bucket == "custom-bucket"
        assert client.region == "us-west-2"


class TestRadarIDEAMListScans:
    """Tests de listado de scans."""
    
    @patch('src.data_sources.radar_ideam.boto3.client')
    def test_list_available_scans_success(self, mock_boto):
        """Debe listar scans disponibles."""
        mock_s3 = Mock()
        mock_boto.return_value = mock_s3
        
        # Mock respuesta S3
        now = datetime.utcnow()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'radar_2025_12_07_1200.raw',
                    'LastModified': now,
                    'Size': 1024000
                },
                {
                    'Key': 'radar_2025_12_07_1100.raw',
                    'LastModified': now - timedelta(hours=1),
                    'Size': 1024000
                }
            ]
        }
        
        client = RadarIDEAMClient({})
        scans = client.list_available_scans(hours_back=3)
        
        assert len(scans) == 2
        assert scans['key'] == 'radar_2025_12_07_1200.raw'
    
    @patch('src.data_sources.radar_ideam.boto3.client')
    def test_list_available_scans_empty(self, mock_boto):
        """Debe retornar lista vacía si no hay scans."""
        mock_s3 = Mock()
        mock_boto.return_value = mock_s3
        mock_s3.list_objects_v2.return_value = {}
        
        client = RadarIDEAMClient({})
        scans = client.list_available_scans()
        
        assert scans == []


# Ejecutar: pytest tests/test_radar_ideam.py -v
