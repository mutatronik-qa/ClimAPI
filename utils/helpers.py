"""Simple helper utilities."""
import csv
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def save_to_csv(data: Dict[str, Any], filepath: str) -> None:
    """Save weather data to CSV file."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    file_exists = Path(filepath).exists()
    
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['timestamp', 'temperature', 'humidity', 'precipitation', 'wind_speed', 'source']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': data.get('timestamp', datetime.now().isoformat()),
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity'),
            'precipitation': data.get('precipitation'),
            'wind_speed': data.get('wind_speed'),
            'source': data.get('source', 'unknown')
        })


def save_all_sources(results: List[Dict[str, Any]], base_dir: str = "data") -> None:
    """Save each source's data to separate CSV and merged to one."""
    raw_dir = Path(base_dir) / "raw"
    processed_dir = Path(base_dir) / "processed"
    
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Save each source individually
    for result in results:
        source = result.get('source', 'unknown')
        filepath = raw_dir / f"{source}.csv"
        save_to_csv(result, str(filepath))
    
    # Save merged (only valid data)
    valid_results = [r for r in results if r.get('temperature') is not None]
    if valid_results:
        merged_path = processed_dir / "weather.csv"
        for result in valid_results:
            save_to_csv(result, str(merged_path))


def load_from_csv(filepath: str) -> List[Dict[str, Any]]:
    """Load weather data from CSV."""
    results = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
    except FileNotFoundError:
        pass
    
    return results


def validate_coordinates(lat: float, lon: float) -> None:
    """Validate coordinates."""
    if not -90 <= lat <= 90:
        raise ValueError(f"Invalid latitude: {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"Invalid longitude: {lon}")