import os
import time
import requests
import json
import csv

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ASSAM_BBOX = (24.0, 89.6, 28.2, 96.5)  # (south, west, north, east)
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Queries with user-friendly timeouts and distinct proxy tags
# Lighter infrastructure queries that won't timeout
QUERIES = {
    "telecom_towers": """
        [out:json][timeout:60];
        (
          node["man_made"="mast"]({s},{w},{n},{e});
          node["telecom"="tower"]({s},{w},{n},{e});
          node["man_made"="tower"]({s},{w},{n},{e});
        );
        out body;
    """,
    "hospitals": """
        [out:json][timeout:60];
        node["amenity"="hospital"]({s},{w},{n},{e});
        out body;
    """,
    "petrol_pumps": """
        [out:json][timeout:60];
        node["amenity"="fuel"]({s},{w},{n},{e});
        out body;
    """,
    "police_stations": """
        [out:json][timeout:60];
        node["amenity"="police"]({s},{w},{n},{e});
        out body;
    """
}

HEADERS = {
    "User-Agent": "GridMindBot/1.0 (contact: dipuser@apdcl.in) python-requests/2.31.0"
}

def fetch_proxy_data():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_points = []
    
    s, w, n, e = ASSAM_BBOX
    
    for key, query in QUERIES.items():
        print(f"Fetching {key} proxy points...")
        filled = query.format(s=s, w=w, n=n, e=e)
        try:
            resp = requests.post(OVERPASS_URL, data={"data": filled}, headers=HEADERS, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get("elements", [])
                print(f"  ✓ Found {len(elements)} points for {key}")
                for el in elements:
                    if el.get("type") == "node":
                        tags = el.get("tags", {})
                        name = tags.get("name", f"Proxy {key.capitalize()}")
                        all_points.append({
                            "lat": el["lat"],
                            "lon": el["lon"],
                            "name": name,
                            "type": key
                        })
            else:
                print(f"  ✗ Failed to fetch {key}: HTTP {resp.status_code}")
        except Exception as ex:
            print(f"  ✗ Error fetching {key}: {ex}")
            
        time.sleep(2) # Politeness
        
    print(f"\nTotal proxy coordinates retrieved: {len(all_points)}")
    
    # Expand points to simulate clusters of transformers (e.g., 4-5 transformers per tower/anchor)
    if len(all_points) > 0 and len(all_points) < 1362:
        print(f"Expanding points from {len(all_points)} to 1,362 via local spatial clustering (+/- 100m)...")
        import random
        original_points = list(all_points)
        target = 1362
        while len(all_points) < target:
            anchor = random.choice(original_points)
            # Perturb coordinates slightly (approx 50-120 meters)
            lat_offset = random.uniform(-0.0009, 0.0009)
            lon_offset = random.uniform(-0.0009, 0.0009)
            all_points.append({
                "lat": anchor["lat"] + lat_offset,
                "lon": anchor["lon"] + lon_offset,
                "name": f"{anchor['name']} Cluster Node",
                "type": f"{anchor['type']}_cluster"
            })
        print(f"Expanded to {len(all_points)} points.")
        
    # Save as JSON for caching / reference
    json_path = os.path.join(OUTPUT_DIR, "proxy_points.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_points, f, indent=2)
        
    # Save as CSV
    csv_path = os.path.join(OUTPUT_DIR, "proxy_points.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["lat", "lon", "name", "type"])
        writer.writeheader()
        writer.writerows(all_points)
        
    print(f"Saved to {csv_path} and {json_path}")
    return all_points

if __name__ == "__main__":
    fetch_proxy_data()
