"""
CLI - Command Line Interface for Weather Data
Simple, powerful, with clean table output.

Usage:
    python cli.py current --lat 6.24 --lon -75.58
    python cli.py sources
    python cli.py save --lat 6.24 --lon -75.58
    python cli.py history
"""
import argparse
import csv
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Use the weather service
from backend.weather_service import get_service
from backend.sources import SOURCES, PRIORITY, get_source


def print_header(title: str):
    """Print formatted header."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}\n")


def print_table(headers: list, rows: list):
    """Print a simple table."""
    if not rows:
        print("  No data")
        return
    
    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Print header
    header_row = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_row)
    print("-" * len(header_row))
    
    # Print rows
    for row in rows:
        print(" | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)))


def cmd_current(args):
    """Get current weather."""
    print_header(f"Current Weather: {args.lat}, {args.lon}")
    
    service = get_service()
    
    start = time.time()
    result = service.get_weather(
        lat=args.lat,
        lon=args.lon,
        source=args.source,
        use_cache=not args.no_cache
    )
    elapsed = time.time() - start
    
    if result.get("error") and not result.get("temperature"):
        print(f"❌ Error: {result.get('error')}")
        return 1
    
    # Print main data
    print(f"🌡️  Temperature: {result.get('temperature', 'N/A')}°C")
    print(f"💧  Humidity:    {result.get('humidity', 'N/A')}%")
    print(f"🌧️  Precipitation: {result.get('precipitation', 'N/A')} mm")
    print(f"💨  Wind Speed:  {result.get('wind_speed', 'N/A')} km/h")
    print(f"📡 Source:      {result.get('source', 'N/A')}")
    print(f"⏱️  Response:    {elapsed:.2f}s")
    print(f"🕐 Timestamp:   {result.get('timestamp', 'N/A')}")
    
    # Print all sources if requested
    if args.all_sources and result.get("all_sources"):
        print("\n📊 All Sources:")
        print_table(
            ["Source", "Temperature", "Humidity", "Precipitation", "Wind", "Error"],
            [
                [
                    r.get("source", "?"),
                    f"{r.get('temperature', 'N/A')}",
                    f"{r.get('humidity', 'N/A')}",
                    f"{r.get('precipitation', 'N/A')}",
                    f"{r.get('wind_speed', 'N/A')}",
                    r.get("error", "-")[:30]
                ]
                for r in result.get("all_sources", [])
            ]
        )
    
    # Save if requested
    if args.save:
        service.save_data(result)
        print(f"\n💾 Saved to data/raw/{result.get('source', 'unknown')}.csv")
    
    return 0


def cmd_sources(args):
    """List all sources with status."""
    print_header("Weather Sources")
    
    service = get_service()
    status = service.get_sources_status()
    
    print_table(
        ["Source", "Status", "Response Time", "Error"],
        [
            [
                s["name"],
                "✅ Available" if s["available"] else "❌ Unavailable",
                f"{s['response_time']:.3f}s",
                (s.get("error") or "-")[:40]
            ]
            for s in status
        ]
    )
    
    print(f"\n📌 Priority order: {', '.join(PRIORITY)}")
    
    return 0


def cmd_save(args):
    """Save weather data to CSV."""
    print_header(f"Saving Weather Data: {args.lat}, {args.lon}")
    
    service = get_service()
    
    # Get data from all sources
    result = service.get_weather(args.lat, args.lon, use_cache=not args.no_cache)
    saved = False
    
    if result.get("temperature"):
        service.save_data(result)
        saved = True
    
    # Save all sources individually, including radar metadata and SIATA results
    for src_name in SOURCES:
        src_result = service._call_source(src_name, args.lat, args.lon)
        if src_result.get("source"):
            service.save_data(src_result)
            saved = True
    
    if not saved:
        print(f"❌ No data to save")
        return 1

    print(f"✅ Data saved successfully")
    print(f"   - Raw data: data/raw/")
    print(f"   - Merged data: data/processed/weather.csv")
    return 0


def cmd_history(args):
    """Show historical data from CSV."""
    print_header("Historical Data")
    
    data_dir = Path("data/processed")
    
    if not data_dir.exists():
        print("❌ No historical data found")
        print("   Run: python cli.py save --lat 6.24 --lon -75.58")
        return 1
    
    # Try to load CSV
    import csv
    
    filepath = data_dir / "weather.csv"
    if not filepath.exists():
        print("❌ No weather.csv found")
        return 1
    
    # Read and display
    rows = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)
        
        # Show last N entries
        limit = args.limit
        for row in all_rows[-limit:]:
            rows.append([
                row.get("timestamp", "")[:19],
                row.get("temperature", ""),
                row.get("humidity", ""),
                row.get("source", "")
            ])
    
    if rows:
        print_table(
            ["Timestamp", "Temperature", "Humidity", "Source"],
            rows
        )
        print(f"\n📊 Total records: {len(all_rows)}")
    else:
        print("❌ No records")
    
    return 0


def cmd_test_source(args):
    """Test a specific source."""
    print_header(f"Testing Source: {args.source}")
    
    source_func = get_source(args.source)
    
    if not source_func:
        print(f"❌ Unknown source: {args.source}")
        print(f"   Available: {', '.join(SOURCES.keys())}")
        return 1
    
    lat = args.lat or 6.244
    lon = args.lon or -75.581
    
    start = time.time()
    result = source_func(lat, lon)
    elapsed = time.time() - start
    
    print(f"⏱️  Response time: {elapsed:.3f}s")
    print(f"\n📦 Result:")
    
    for key, value in result.items():
        print(f"   {key}: {value}")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ClimAPI CLI - Weather data from command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py current --lat 6.24 --lon -75.58
  python cli.py current --lat 6.24 --lon -75.58 --all-sources
  python cli.py sources
  python cli.py save --lat 6.24 --lon -75.58
  python cli.py history
  python cli.py test-source open-meteo
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # current command
    current_parser = subparsers.add_parser("current", help="Get current weather")
    current_parser.add_argument("--lat", type=float, required=True, help="Latitude")
    current_parser.add_argument("--lon", type=float, required=True, help="Longitude")
    current_parser.add_argument("--source", type=str, help="Specific source (e.g., open-meteo)")
    current_parser.add_argument("--all-sources", action="store_true", help="Show all sources")
    current_parser.add_argument("--save", action="store_true", help="Save to CSV")
    current_parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    current_parser.set_defaults(func=cmd_current)
    
    # sources command
    sources_parser = subparsers.add_parser("sources", help="List all sources")
    sources_parser.set_defaults(func=cmd_sources)
    
    # save command
    save_parser = subparsers.add_parser("save", help="Save weather data")
    save_parser.add_argument("--lat", type=float, required=True, help="Latitude")
    save_parser.add_argument("--lon", type=float, required=True, help="Longitude")
    save_parser.add_argument("--no-cache", action="store_true", help="Bypass cache")
    save_parser.set_defaults(func=cmd_save)
    
    # history command
    history_parser = subparsers.add_parser("history", help="Show historical data")
    history_parser.add_argument("--limit", type=int, default=10, help="Number of records")
    history_parser.set_defaults(func=cmd_history)
    
    # test-source command
    test_parser = subparsers.add_parser("test-source", help="Test a specific source")
    test_parser.add_argument("source", help="Source name")
    test_parser.add_argument("--lat", type=float, help="Latitude")
    test_parser.add_argument("--lon", type=float, help="Longitude")
    test_parser.set_defaults(func=cmd_test_source)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n❌ Cancelled")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())