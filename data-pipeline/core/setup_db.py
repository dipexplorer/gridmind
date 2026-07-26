import psycopg2
import os
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

# 1. Update transformers table
try:
    cur.execute("""
    ALTER TABLE transformers
    ADD COLUMN IF NOT EXISTS age_years INTEGER,
    ADD COLUMN IF NOT EXISTS is_metered BOOLEAN,
    ADD COLUMN IF NOT EXISTS current_load_kw FLOAT,
    ADD COLUMN IF NOT EXISTS current_load_pct FLOAT,
    ADD COLUMN IF NOT EXISTS current_oil_temp_c FLOAT,
    ADD COLUMN IF NOT EXISTS current_health_score INTEGER,
    ADD COLUMN IF NOT EXISTS current_failure_risk FLOAT,
    ADD COLUMN IF NOT EXISTS current_status VARCHAR(50),
    ADD COLUMN IF NOT EXISTS last_updated TIMESTAMP WITH TIME ZONE;
    """)
    print("Updated transformers table.")
except Exception as e:
    print(f"Error updating transformers: {e}")

# 2. Create sensor_logs
try:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sensor_logs (
        id SERIAL PRIMARY KEY,
        transformer_id VARCHAR(255) REFERENCES transformers(transformer_id),
        snapshot_at TIMESTAMP WITH TIME ZONE,
        load_kw FLOAT,
        load_pct FLOAT,
        oil_temperature_c FLOAT,
        health_score INTEGER,
        failure_risk FLOAT,
        status VARCHAR(50),
        temperature_c FLOAT,
        humidity_pct FLOAT,
        precipitation_mm FLOAT,
        windspeed_kmh FLOAT,
        is_severe_weather BOOLEAN
    );
    """)
    print("Created sensor_logs table.")
except Exception as e:
    print(f"Error creating sensor_logs: {e}")

# 3. Create outages
try:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS outages (
        id SERIAL PRIMARY KEY,
        transformer_id VARCHAR(255) REFERENCES transformers(transformer_id),
        started_at TIMESTAMP WITH TIME ZONE,
        resolved_at TIMESTAMP WITH TIME ZONE,
        status VARCHAR(50),
        cause VARCHAR(255),
        affected_consumers_estimated INTEGER,
        health_score_at_outage INTEGER,
        failure_risk_at_outage FLOAT,
        UNIQUE(transformer_id, started_at)
    );
    """)
    print("Created outages table.")
except Exception as e:
    print(f"Error creating outages: {e}")

conn.close()
print("DB setup complete.")
