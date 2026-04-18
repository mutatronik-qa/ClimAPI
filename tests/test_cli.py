"""
Tests for cli.py - Command line interface
"""
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO
import sys
from cli import cmd_current, cmd_sources, cmd_save, cmd_history, cmd_test_source


class TestCLI:
    """Test CLI commands."""

    @patch('cli.get_service')
    def test_cmd_current_success(self, mock_get_service):
        """Test current weather command success."""
        mock_service = MagicMock()
        mock_service.get_weather.return_value = {
            "temperature": 25.0,
            "humidity": 60.0,
            "precipitation": 0.0,
            "wind_speed": 5.0,
            "source": "open-meteo",
            "timestamp": "2024-01-01T12:00:00"
        }
        mock_get_service.return_value = mock_service

        # Mock args
        args = MagicMock()
        args.lat = 6.24
        args.lon = -75.58
        args.source = None
        args.all_sources = False
        args.save = False
        args.no_cache = False

        exit_code = cmd_current(args)

        assert exit_code == 0
        mock_service.get_weather.assert_called_once()

    @patch('cli.get_service')
    def test_cmd_current_error(self, mock_get_service):
        """Test current weather command with error."""
        mock_service = MagicMock()
        mock_service.get_weather.return_value = {
            "error": "All sources failed"
        }
        mock_get_service.return_value = mock_service

        args = MagicMock()
        args.lat = 6.24
        args.lon = -75.58
        args.source = None
        args.all_sources = False
        args.save = False
        args.no_cache = False

        exit_code = cmd_current(args)

        assert exit_code == 1

    @patch('cli.get_service')
    def test_cmd_sources(self, mock_get_service):
        """Test sources command."""
        mock_service = MagicMock()
        mock_service.get_sources_status.return_value = [
            {"name": "open-meteo", "available": True, "response_time": 0.5, "error": None},
            {"name": "openweathermap", "available": False, "response_time": 1.0, "error": "API key"}
        ]
        mock_get_service.return_value = mock_service

        args = MagicMock()
        exit_code = cmd_sources(args)

        assert exit_code == 0
        mock_service.get_sources_status.assert_called_once()

    @patch('cli.get_service')
    def test_cmd_save_success(self, mock_get_service):
        """Test save command success."""
        mock_service = MagicMock()
        mock_service.get_weather.return_value = {"temperature": 25.0}
        mock_get_service.return_value = mock_service

        args = MagicMock()
        args.lat = 6.24
        args.lon = -75.58
        args.no_cache = False

        exit_code = cmd_save(args)

        assert exit_code == 0

    @patch('cli.get_service')
    def test_cmd_save_no_data(self, mock_get_service):
        """Test save command with no data."""
        mock_service = MagicMock()
        mock_service.get_weather.return_value = {"error": "No data"}
        mock_get_service.return_value = mock_service

        args = MagicMock()
        args.lat = 6.24
        args.lon = -75.58
        args.no_cache = False

        exit_code = cmd_save(args)

        assert exit_code == 1

    @patch('cli.get_service')
    @patch('cli.Path')
    @patch('builtins.open')
    def test_cmd_history(self, mock_open, mock_path, mock_get_service):
        """Test history command."""
        # Mock file exists
        mock_path.return_value.exists.return_value = True

        # Mock CSV data
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock CSV reader
        with patch('cli.csv.DictReader') as mock_reader:
            mock_reader.return_value = [
                {"timestamp": "2024-01-01T12:00:00", "temperature": "25.0", "humidity": "60", "source": "test"}
            ]

            args = MagicMock()
            args.limit = 10

            exit_code = cmd_history(args)

            assert exit_code == 0

    @patch('cli.get_service')
    def test_cmd_test_source_success(self, mock_get_service):
        """Test test-source command success."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        with patch('backend.sources.get_source') as mock_get_source:
            mock_get_source.return_value = lambda lat, lon, **kwargs: {"temperature": 25.0, "source": "test"}

            args = MagicMock()
            args.source = "open-meteo"
            args.lat = 6.24
            args.lon = -75.58

            exit_code = cmd_test_source(args)

            assert exit_code == 0

    @patch('cli.get_service')
    def test_cmd_test_source_unknown(self, mock_get_service):
        """Test test-source command with unknown source."""
        args = MagicMock()
        args.source = "unknown"

        exit_code = cmd_test_source(args)

        assert exit_code == 1