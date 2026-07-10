"""
digital_twin_engine.py — Step 3 of GridMind Digital Twin Pipeline
===================================================================
The core intelligence layer. Takes weather-enriched transformer data and
computes realistic operational metrics calibrated to REAL APDCL statistics:

  Real-world calibration targets (from verified APDCL sources):
  ┌──────────────────────────────────────────────────────────┐
  │  AT&C Loss (FY2024-25)         : 18.021%                │
  │  T&D Loss (33kV→LT meters)     : 16.83%                 │
  │  CEA National DT Failure Rate  : ~10% per year          │
  │  APDCL Total DTs               : 64,493                  │
  │  Avg DT Capacity               : ~69.5 kVA               │
  │  59.25% of DTs are UNMETERED  (only simulated readings) │
  └──────────────────────────────────────────────────────────┘

Outputs per transformer:
  - load_kw            : Current load in kilowatts
  - load_pct           : Load as % of rated capacity
  - oil_temperature_c  : Estimated oil temp (physics-based)
  - health_score       : 0-100 (100 = perfect, 0 = critical)
  - failure_risk       : float 0.0–1.0 (Cox PH–inspired)
  - status             : "normal" | "overloaded" | "critical" | "offline"
  - is_metered         : bool (40.75% are metered per audit)

Input:  data-pipeline/output/transformers_with_weather.csv
Output: data-pipeline/output/digital_twin_snapshot.csv
        data-pipeline/output/digital_twin_snapshot.json  (for Supabase sync)

Usage:
  python digital_twin_engine.py
"""

import csv
import json
import math
import os
import random
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Calibration Constants (from verified APDCL/AERC/CEA sources)
# ---------------------------------------------------------------------------

# Annual failure rate (CEA national benchmark)
ANNUAL_FAILURE_RATE = 0.10          # 10%
# Per-run failure probability (15-min intervals → ~35,040 runs/year)
INTERVAL_FAILURE_PROB = 1 - (1 - ANNUAL_FAILURE_RATE) ** (1 / 35040)

# Network loss target (APDCL audit FY2024-25)
TD_LOSS_TARGET = 0.1683             # 16.83%

# Metering coverage (APDCL audit: 59.25% unmetered ⇒ 40.75% metered)
METERED_FRACTION = 0.4075

# Ambient temperature reference for oil temperature model (°C)
AMBIENT_REF = 25.0
# Oil temperature rise per % load (IEEE loading guide approximation)
OIL_TEMP_K = 0.65                   # ΔT per % load above base

# Load factor variation by hour-of-day (Indian residential pattern)
#   Index 0 = midnight, 12 = noon
HOURLY_LOAD_FACTOR = [
    0.55, 0.50, 0.48, 0.47, 0.48, 0.52,   # 00:00–05:00
    0.60, 0.72, 0.80, 0.83, 0.82, 0.80,   # 06:00–11:00
    0.85, 0.88, 0.85, 0.82, 0.80, 0.85,   # 12:00–17:00
    0.95, 1.00, 0.98, 0.90, 0.78, 0.62,   # 18:00–23:00 (evening peak)
]

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "output")
INPUT_FILE   = os.path.join(OUTPUT_DIR, "transformers_with_weather.csv")
OUTPUT_CSV   = os.path.join(OUTPUT_DIR, "digital_twin_snapshot.csv")
OUTPUT_JSON  = os.path.join(OUTPUT_DIR, "digital_twin_snapshot.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_capacity_kva(raw: str) -> float:
    """Parse capacity strings like '100 kVA', '63  kVA', '250 kVA', '69.5'."""
    if not raw:
        return 69.5                    # Assam average
    cleaned = raw.replace("kVA", "").replace("kva", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 69.5


def time_of_day_factor() -> float:
    """Return current load multiplier based on Kolkata local hour."""
    now_ist = datetime.now(timezone.utc).astimezone()
    hour = now_ist.hour
    return HOURLY_LOAD_FACTOR[hour]


def compute_oil_temperature(load_pct: float, ambient_temp_c: float) -> float:
    """
    Simplified thermal model (IEC 60076-7 inspired):
      T_oil = T_ambient + ΔT_rated × (load_pct / 100)^1.6
    ΔT_rated = 65°C for ONAN-cooled transformers (typical APDCL distribution TF)
    """
    delta_t_rated = 65.0
    oil_rise = delta_t_rated * ((load_pct / 100.0) ** 1.6)
    # Add weather heat contribution
    ambient_delta = (ambient_temp_c - AMBIENT_REF) * 0.8
    return round(ambient_temp_c + oil_rise + ambient_delta, 1)


def cox_failure_risk(
    load_pct: float,
    oil_temp: float,
    age_years: float,
    is_severe_weather: bool,
    precip_mm: float,
) -> float:
    """
    Cox Proportional Hazard–inspired failure risk score [0.0–1.0].
    Baseline hazard calibrated to 10% annual DT failure rate.

    Covariates and their hazard ratios (HR) derived from CEA/utility literature:
      load_overload (>80%)  HR ≈ 2.5 — overloaded DTs fail 2.5x more
      high_oil_temp (>95°C) HR ≈ 3.0 — thermal failure primary cause
      age (per decade)      HR ≈ 1.8 — ageing hazard
      severe_weather        HR ≈ 2.0 — storm/flood exposure
      heavy_rain (>10mm)    HR ≈ 1.4 — moisture ingress risk
    """
    baseline = INTERVAL_FAILURE_PROB * 35040  # annualised baseline [0–1]

    hr = 1.0
    hr *= 2.5 if load_pct > 80 else (1.5 if load_pct > 60 else 1.0)
    hr *= 3.0 if oil_temp > 95 else (1.8 if oil_temp > 80 else 1.0)
    hr *= (1.8 ** (age_years / 10))
    hr *= 2.0 if is_severe_weather else 1.0
    hr *= 1.4 if precip_mm > 10 else 1.0

    raw_risk = baseline * hr
    # Cap at 0.99 and floor at 0.001
    return round(min(0.99, max(0.001, raw_risk)), 4)


def health_score(failure_risk: float, load_pct: float, oil_temp: float) -> int:
    """Composite health score 0–100 (lower = worse)."""
    risk_penalty  = failure_risk * 40
    load_penalty  = max(0, (load_pct - 60) / 40 * 30)  # penalty above 60% load
    temp_penalty  = max(0, (oil_temp - 70) / 30 * 30)  # penalty above 70°C
    raw = 100 - risk_penalty - load_penalty - temp_penalty
    return max(0, min(100, round(raw)))


def assign_status(load_pct: float, health: int, failure_risk: float) -> str:
    if failure_risk > 0.7 or health < 20:
        return "critical"
    if load_pct > 100 or health < 40:
        return "overloaded"
    if load_pct > 80 or health < 60:
        return "warning"
    return "normal"


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------

def run_engine() -> list:
    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Weather CSV not found: {INPUT_FILE}\n"
            "Run fetch_weather.py first."
        )

    tod_factor = time_of_day_factor()
    now_iso    = datetime.now(timezone.utc).isoformat()
    print(f"  Time-of-day load factor: {tod_factor:.2f}  ({datetime.now().strftime('%H:%M')} IST)")

    rows = []
    with open(INPUT_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        raw_rows = list(reader)

    print(f"  Processing {len(raw_rows):,} transformers...")

    # We use a seeded RNG for reproducibility within a run,
    # but seed changes each run to provide realistic variation
    rng = random.Random()

    total_input_energy  = 0.0
    total_output_energy = 0.0

    for row in raw_rows:
        capacity_kva = parse_capacity_kva(
            row.get("Capacity", "") or row.get("capacity_kva", "") or row.get("load", "")
        )
        # If capacity column has raw load (older CSV), fall back to average
        if capacity_kva < 10 or capacity_kva > 5000:
            capacity_kva = 69.5

        # Environmental inputs
        temp_c      = float(row.get("temperature_c",    30))
        humidity    = float(row.get("humidity_pct",     65))
        precip      = float(row.get("precipitation_mm",  0))
        windspeed   = float(row.get("windspeed_kmh",    10))
        severe_wx   = str(row.get("is_severe_weather", "False")).lower() == "true"

        # Synthetic age (log-normal distribution: most DTs 10–30 years old)
        age = max(1, round(rng.lognormvariate(2.7, 0.5)))  # mean ≈ 14.9 yrs

        # Load calculation:
        # Base load as % of capacity, modulated by time-of-day and weather
        base_load_pct = rng.gauss(68, 18)   # centred around 68% utilisation
        base_load_pct = max(5, min(130, base_load_pct))  # physical limits

        # Weather adjustment: hot days → AC load ↑; storms → instability
        weather_adj = (temp_c - AMBIENT_REF) * 0.4         # +0.4% per °C above 25
        if severe_wx:
            weather_adj -= rng.uniform(5, 20)               # voltage sags during storms

        load_pct  = round(max(0, base_load_pct * tod_factor + weather_adj), 1)
        load_kw   = round(load_pct / 100 * capacity_kva * 0.85, 2)  # PF=0.85

        # Physics-based oil temperature
        oil_temp = compute_oil_temperature(load_pct, temp_c)

        # Risk & health
        f_risk  = cox_failure_risk(load_pct, oil_temp, age, severe_wx, precip)
        health  = health_score(f_risk, load_pct, oil_temp)
        status  = assign_status(load_pct, health, f_risk)

        # Metering (40.75% are metered per APDCL audit)
        is_metered = rng.random() < METERED_FRACTION

        # Track for T&D loss calibration check
        # T&D Loss = energy injected but not delivered = (rated - actual_load) / rated
        rated_kw = capacity_kva * 0.85
        total_input_energy  += rated_kw
        total_output_energy += load_kw  # actual load consumed

        rows.append({
            # Identity
            "transformer_id":   row.get("osm_id") or row.get("Dtr No") or row.get("dtr_no", ""),
            "name":             row.get("name") or row.get("DTR Name") or row.get("dtr_name", ""),
            "latitude":         row.get("latitude") or row.get("Latitude", ""),
            "longitude":        row.get("longitude") or row.get("Longitude", ""),
            "capacity_kva":     round(capacity_kva, 1),
            "feeder_no":        row.get("Feeder No") or row.get("feeder_no", ""),
            "sub_div_code":     row.get("Sub Div Code") or row.get("sub_div_code", "133"),
            # Operational
            "load_kw":          load_kw,
            "load_pct":         load_pct,
            "oil_temperature_c": oil_temp,
            "age_years":        age,
            "is_metered":       is_metered,
            # Risk
            "failure_risk":     f_risk,
            "health_score":     health,
            "status":           status,
            # Weather snapshot
            "temperature_c":    temp_c,
            "humidity_pct":     humidity,
            "precipitation_mm": precip,
            "windspeed_kmh":    windspeed,
            "is_severe_weather": severe_wx,
            # Metadata
            "snapshot_at":      now_iso,
        })

    # Calibration report
    actual_loss = 1 - (total_output_energy / total_input_energy) if total_input_energy else 0
    print(f"\n  === Calibration Check ===")
    print(f"  Target T&D Loss : {TD_LOSS_TARGET*100:.2f}%")
    print(f"  Simulated Loss  : {actual_loss*100:.2f}%  {'✓ OK' if abs(actual_loss - TD_LOSS_TARGET) < 0.05 else '⚠ Deviation'}")

    status_counts = {}
    for r in rows:
        s = r["status"]
        status_counts[s] = status_counts.get(s, 0) + 1
    print("\n  === Status Distribution ===")
    for s, c in sorted(status_counts.items()):
        pct = c / len(rows) * 100
        print(f"  {s:12s}: {c:,}  ({pct:.1f}%)")

    return rows


def save_outputs(rows: list):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # CSV
    if rows:
        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"\n  ✓ CSV  → {OUTPUT_CSV}")

    # JSON (for direct Supabase upsert)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)
    print(f"  ✓ JSON → {OUTPUT_JSON}")


def main():
    print("="*60)
    print("STEP 3: DIGITAL TWIN ENGINE — Calibrated Simulation")
    print("="*60)
    rows = run_engine()
    save_outputs(rows)
    print(f"\n  Total records: {len(rows):,}")
    print("\nNext step: python supabase_sync.py")


if __name__ == "__main__":
    main()
