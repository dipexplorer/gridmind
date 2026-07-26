"""
extract_osm.py — Step 1 of GridMind Digital Twin Pipeline
==========================================================
Queries OpenStreetMap's Overpass API for all electrical infrastructure
(substations, transformers, power lines) within Assam's bounding box.

Bounding box for Assam:
  South: 24.0°N  North: 28.2°N
  West:  89.6°E  East:  96.5°E

Output:
  data-pipeline/output/osm_transformers.json  — raw OSM nodes
  data-pipeline/output/substations.csv        — processed substation list
  data-pipeline/output/transformers_osm.csv   — processed transformer list

Usage:
  python extract_osm.py
"""

import json
import csv
import os
import time
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

ASSAM_BBOX = (24.0, 89.6, 28.2, 96.5)  # (south, west, north, east)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Overpass QL queries for each power feature type
QUERIES = {
    "substations": """
        [out:json][timeout:90];
        node["power"="substation"]({s},{w},{n},{e});
        out body;
        """,
    "transformers": """
        [out:json][timeout:90];
        node["power"="transformer"]({s},{w},{n},{e});
        out body;
        """,
    "towers": """
        [out:json][timeout:90];
        node["power"="tower"]({s},{w},{n},{e});
        out body;
        """,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_overpass_query(query: str, bbox: tuple) -> dict:
    """Submit a query to Overpass API with Assam bounding box substituted."""
    s, w, n, e = bbox
    filled = query.format(s=s, w=w, n=n, e=e)
    print(f"  → Querying Overpass API...")
    resp = requests.post(OVERPASS_URL, data={"data": filled}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def save_json(data: dict, filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Saved {len(data.get('elements', []))} elements → {path}")


def nodes_to_csv(elements: list, filename: str, feature_type: str):
    """Flatten OSM node elements into a clean CSV."""
    path = os.path.join(OUTPUT_DIR, filename)
    fieldnames = [
        "osm_id", "feature_type", "latitude", "longitude",
        "name", "voltage", "capacity_kva", "operator", "ref"
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for el in elements:
            if el.get("type") != "node":
                continue
            tags = el.get("tags", {})
            writer.writerow({
                "osm_id":        el["id"],
                "feature_type":  feature_type,
                "latitude":      el["lat"],
                "longitude":     el["lon"],
                "name":          tags.get("name", ""),
                "voltage":       tags.get("voltage", ""),
                "capacity_kva":  tags.get("transformer:capacity", tags.get("capacity", "")),
                "operator":      tags.get("operator", "APDCL"),
                "ref":           tags.get("ref", ""),
            })
    print(f"  ✓ CSV written → {path}")
    return path


# ---------------------------------------------------------------------------
# Main extraction logic
# ---------------------------------------------------------------------------

def extract_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    results = {}
    for feature, query in QUERIES.items():
        print(f"\n[{feature.upper()}]")
        try:
            data = run_overpass_query(query, ASSAM_BBOX)
            save_json(data, f"osm_{feature}.json")
            csv_path = nodes_to_csv(data.get("elements", []), f"{feature}_osm.csv", feature)
            results[feature] = {
                "count": len(data.get("elements", [])),
                "csv": csv_path,
            }
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Network error for {feature}: {e}")
            results[feature] = {"count": 0, "error": str(e)}

        # Be polite — Overpass has rate limits
        time.sleep(3)

    # Summary
    print("\n" + "="*60)
    print("EXTRACTION SUMMARY")
    print("="*60)
    total = 0
    for feat, info in results.items():
        count = info.get("count", 0)
        total += count
        status = "✓" if count > 0 else "✗"
        print(f"  {status}  {feat:15s}  {count:,} nodes")
    print(f"\n  Total OSM nodes extracted: {total:,}")
    print(f"  Output directory: {OUTPUT_DIR}")
    print("\nNext step: python fetch_weather.py")


if __name__ == "__main__":
    extract_all()
