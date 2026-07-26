import json, psycopg2, os, uuid
from dotenv import load_dotenv

load_dotenv("../backend/.env")

conn = psycopg2.connect(
    dbname=os.environ.get("POSTGRES_DB", "postgres"),
    user=os.environ.get("POSTGRES_USER", "postgres"),
    password=os.environ.get("POSTGRES_PASSWORD"),
    host=os.environ.get("POSTGRES_HOST"),
    port=os.environ.get("POSTGRES_PORT", 5432)
)
conn.autocommit = True
cur = conn.cursor()

with open("output/digital_twin_snapshot.json", "r") as f:
    records = json.load(f)

# 1. Create mapping of Sub Div Code to Substation ID
substations = {}
for r in records:
    sub_code = r.get("sub_div_code", "133")
    dist = r.get("district", "Unknown")
    if sub_code not in substations:
        code_str = f"SS_{sub_code}"
        name_str = f"{dist} Substation {sub_code}"
        new_id = str(uuid.uuid4())
        # Upsert substation
        cur.execute("""
            INSERT INTO substations (id, name, code, voltage_kv, district)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
        """, (new_id, name_str, code_str, 33, dist))
        row = cur.fetchone()
        substations[sub_code] = row[0]

# 2. Upsert transformers with district, operational_status and substation_id
for r in records:
    sub_id = substations.get(r.get("sub_div_code", "133"))
    district = r.get("district", "Unknown")
    op_status = r.get("operational_status", "IN_SERVICE")

    cur.execute("""
        INSERT INTO transformers (
            transformer_code, rated_kva, age_years, is_metered, 
            current_load_kw, current_load_pct, current_oil_temp_c, 
            current_health_score, current_failure_risk, current_status, last_updated,
            location, substation_id, district, operational_status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)
        ON CONFLICT (transformer_code) DO UPDATE SET
            rated_kva = EXCLUDED.rated_kva,
            age_years = EXCLUDED.age_years,
            is_metered = EXCLUDED.is_metered,
            current_load_kw = EXCLUDED.current_load_kw,
            current_load_pct = EXCLUDED.current_load_pct,
            current_oil_temp_c = EXCLUDED.current_oil_temp_c,
            current_health_score = EXCLUDED.current_health_score,
            current_failure_risk = EXCLUDED.current_failure_risk,
            current_status = EXCLUDED.current_status,
            last_updated = EXCLUDED.last_updated,
            location = EXCLUDED.location,
            substation_id = EXCLUDED.substation_id,
            district = EXCLUDED.district,
            operational_status = EXCLUDED.operational_status
    """, (
        r["transformer_id"], float(r.get("capacity_kva") or 69.5), r.get("age_years", 0), r.get("is_metered", False),
        r.get("load_kw", 0), r.get("load_pct", 0), r.get("oil_temperature_c", 0),
        r.get("health_score", 100), r.get("failure_risk", 0), r.get("status", "normal"), r.get("snapshot_at"),
        float(r["longitude"]), float(r["latitude"]), sub_id, district, op_status
    ))

    # Insert sensor log
    cur.execute("""
        INSERT INTO sensor_logs (
            transformer_code, snapshot_at, load_kw, load_pct, oil_temperature_c, 
            health_score, failure_risk, status, temperature_c, humidity_pct, 
            precipitation_mm, windspeed_kmh, is_severe_weather
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        r["transformer_id"], r.get("snapshot_at"), r.get("load_kw", 0), r.get("load_pct", 0), r.get("oil_temperature_c", 0),
        r.get("health_score", 100), r.get("failure_risk", 0), r.get("status", "normal"),
        r.get("temperature_c", 25), r.get("humidity_pct", 65), r.get("precipitation_mm", 0),
        r.get("windspeed_kmh", 0), r.get("is_severe_weather", False)
    ))

print("PostgreSQL Sync Complete with full fields!")
