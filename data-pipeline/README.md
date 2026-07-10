# GridMind — Live Digital Twin Data Pipeline

Automated pipeline that generates **realistic, live-updating electrical grid data** for GridMind AI — calibrated to real APDCL published statistics.

## Why This Exists

APDCL (and all Indian DISCOMs) don't publish per-transformer telemetry.
Instead, this pipeline creates a **Digital Twin** — a software simulation calibrated to verified real-world numbers:

| Real Source | Value Used |
|---|---|
| APDCL Energy Audit FY2024-25 | AT&C Loss = **18.021%** |
| CEA National Benchmark | DT Failure Rate = **~10%/year** |
| APDCL Audit | 59.25% DTs **unmetered** |
| AERC Tariff Order | Avg unit cost = **₹8.72/kWh** |
| Assam Government Portal | Total DTs = **64,493** |

## Pipeline Architecture

```
OpenStreetMap (Overpass API)
        │  Real substation/transformer GPS locations
        ▼
  extract_osm.py
        │  transformers_osm.csv
        ▼
  fetch_weather.py  ←── Open-Meteo API (live weather)
        │  transformers_with_weather.csv
        ▼
  digital_twin_engine.py
        │  Cox PH failure model + IEC thermal model
        │  Calibrated to 18% T&D loss, 10% failure rate
        │  digital_twin_snapshot.json
        ▼
  supabase_sync.py
        │  UPSERT → transformers table
        │  INSERT → sensor_logs table
        └  UPSERT → outages table (critical only)
```

## Quickstart

```bash
cd data-pipeline

# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure Supabase credentials
cp .env.example .env
# Edit .env and add your SUPABASE_URL and SUPABASE_KEY

# 3. Run the full pipeline
python extract_osm.py       # ~2-3 min (hits OSM API)
python fetch_weather.py     # ~1 min (hits Open-Meteo API)
python digital_twin_engine.py  # <10 seconds
python supabase_sync.py        # ~30 seconds
```

## Scheduling (Cron)

```bash
chmod +x cron_runner.sh

# Run OSM extraction daily at 2am, weather+engine+sync every 30 min
crontab -e
# Add these lines:
0 2 * * * /full/path/to/data-pipeline/cron_runner.sh --osm-only
*/30 * * * * /full/path/to/data-pipeline/cron_runner.sh --skip-osm
```

## Output Files

| File | Description |
|---|---|
| `output/osm_transformers.json` | Raw OSM node data |
| `output/transformers_osm.csv` | Cleaned transformer locations |
| `output/transformers_with_weather.csv` | Locations + live weather |
| `output/digital_twin_snapshot.csv` | Full snapshot (all metrics) |
| `output/digital_twin_snapshot.json` | Same data for Supabase |
| `logs/pipeline_*.log` | Per-run execution logs |

## Dry Run (Test Without DB Writes)

```bash
DRY_RUN=1 python supabase_sync.py
```

## Supabase Tables Required

The sync script writes to these tables (must exist in your Supabase project):

- `transformers` — master asset registry
- `sensor_logs` — append-only time-series readings
- `outages` — active fault/outage events

## Calibration Model Reference

The Digital Twin Engine uses:
- **Cox Proportional Hazard model** for failure risk
- **IEC 60076-7 thermal model** for oil temperature
- **Indian residential load curves** for time-of-day variation
- **Open-Meteo** for real Assam weather conditions
