"""
fetch_weather.py — Step 2 of GridMind Digital Twin Pipeline
============================================================
Maps live weather conditions to each transformer's GPS coordinates using
the Open-Meteo API (100% free, no API key required).

Weather features fetched per location:
  - temperature_2m            (°C) — directly affects oil temperature
  - relative_humidity_2m      (%)  — humidity accelerates insulation degradation
  - precipitation              (mm) — rainfall / flooding risk
  - windspeed_10m             (km/h) — storm / physical damage risk
  - weathercode               (WMO code) — storm / thunderstorm detection

Input:  data-pipeline/output/transformers_osm.csv  (from extract_osm.py)
        OR  data/processed_datasets/transformers.csv  (existing CSV fallback)

Output: data-pipeline/output/transformers_with_weather.csv

Usage:
  python fetch_weather.py
"""

import csv
import json
import os
import time
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))

# Priority: OSM-extracted first, fall back to manually-processed CSV
INPUT_CANDIDATES = [
    os.path.join(OUTPUT_DIR, "transformers_osm.csv"),
    os.path.join(PROJECT_DIR, "data", "processed_datasets", "transformers.csv"),
]

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "transformers_with_weather.csv")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather codes indicating severe conditions (thunderstorm/heavy rain/snow)
SEVERE_CODES = {
    95, 96, 99,   # Thunderstorm
    65, 67,        # Heavy rain / freezing rain
    75, 77,        # Heavy snow
    82,            # Violent rain shower
}

# ---------------------------------------------------------------------------
# Batch weather fetch (Open-Meteo supports up to 100 coords per request)
# ---------------------------------------------------------------------------

def fetch_weather_batch(rows: list) -> dict:
    """
    Fetch weather for a batch of rows (max 100 per API call).
    Returns dict keyed by (lat, lon) tuple → weather dict.
    """
    latitudes  = [str(r["latitude"])  for r in rows]
    longitudes = [str(r["longitude"]) for r in rows]

    params = {
        "latitude":   ",".join(latitudes),
        "longitude":  ",".join(longitudes),
        "current_weather": "true",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,windspeed_10m,weathercode",
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }

    resp = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    results = {}

    # When multiple locations requested, API returns a list; single → dict
    if isinstance(data, list):
        entries = data
    else:
        entries = [data]

    for i, entry in enumerate(entries):
        row = rows[i]
        key = (str(row["latitude"]), str(row["longitude"]))

        current = entry.get("current_weather", {})
        hourly  = entry.get("hourly", {})

        # Latest hourly values (index 0 = current hour)
        temp        = current.get("temperature",  hourly.get("temperature_2m",  [None])[0])
        humidity    = hourly.get("relative_humidity_2m", [None])[0]
        precip      = hourly.get("precipitation",        [0])[0]
        wind        = current.get("windspeed",    hourly.get("windspeed_10m",    [0])[0])
        wcode       = current.get("weathercode",  hourly.get("weathercode",      [0])[0])

        results[key] = {
            "temperature_c":    round(float(temp    or 25), 2),
            "humidity_pct":     round(float(humidity or 60), 2),
            "precipitation_mm": round(float(precip  or 0),  2),
            "windspeed_kmh":    round(float(wind    or 0),  2),
            "weather_code":     int(wcode or 0),
            "is_severe_weather": int(wcode or 0) in SEVERE_CODES,
        }

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_transformers() -> list:
    for path in INPUT_CANDIDATES:
        if os.path.exists(path):
            print(f"  Using input: {path}")
            rows = []
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        rows.append({
                            **row,
                            "latitude":  float(row.get("Latitude")  or row.get("latitude")  or 0),
                            "longitude": float(row.get("Longitude") or row.get("longitude") or 0),
                        })
                    except ValueError:
                        continue  # skip rows with bad coordinates
            print(f"  Loaded {len(rows):,} transformers")
            return rows
    raise FileNotFoundError("No transformer CSV found. Run extract_osm.py first.")


def fetch_all_weather(rows: list) -> list:
    # Filter out rows without valid coordinates
    valid = [r for r in rows if r["latitude"] and r["longitude"]]
    print(f"  Fetching weather for {len(valid):,} locations (batches of 100)...")

    weather_map = {}
    batch_size = 100

    for i in range(0, len(valid), batch_size):
        batch = valid[i : i + batch_size]
        print(f"  → Batch {i // batch_size + 1} / {(len(valid) - 1) // batch_size + 1}")
        try:
            batch_result = fetch_weather_batch(batch)
            weather_map.update(batch_result)
        except requests.exceptions.RequestException as e:
            print(f"    ✗ API error: {e} — filling with defaults for this batch")
            for r in batch:
                key = (str(r["latitude"]), str(r["longitude"]))
                weather_map[key] = {
                    "temperature_c": 30.0, "humidity_pct": 70.0,
                    "precipitation_mm": 0.0, "windspeed_kmh": 10.0,
                    "weather_code": 0, "is_severe_weather": False,
                }
        time.sleep(1)  # gentle rate limit

    # Merge weather back into rows
    enriched = []
    for row in valid:
        key = (str(row["latitude"]), str(row["longitude"]))
        weather = weather_map.get(key, {
            "temperature_c": 30.0, "humidity_pct": 70.0,
            "precipitation_mm": 0.0, "windspeed_kmh": 10.0,
            "weather_code": 0, "is_severe_weather": False,
        })
        enriched.append({**row, **weather})

    return enriched


def save_output(rows: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not rows:
        print("  ✗ No rows to save.")
        return

    fieldnames = list(rows[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    severe_count = sum(1 for r in rows if r.get("is_severe_weather"))
    print(f"\n  ✓ {len(rows):,} transformers enriched with live weather → {OUTPUT_FILE}")
    print(f"  ⚡ {severe_count} locations currently under severe weather conditions")


def main():
    print("="*60)
    print("STEP 2: LIVE WEATHER FETCH — Open-Meteo API")
    print("="*60)
    rows     = load_transformers()
    enriched = fetch_all_weather(rows)
    save_output(enriched)
    print("\nNext step: python digital_twin_engine.py")


if __name__ == "__main__":
    main()
