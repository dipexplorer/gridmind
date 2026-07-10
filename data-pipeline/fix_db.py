import psycopg2, os
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

# Make transformer_code UNIQUE if it isn't already, so we can use it as a foreign key
try:
    cur.execute("ALTER TABLE transformers ADD CONSTRAINT unique_transformer_code UNIQUE(transformer_code);")
    print("Added unique constraint to transformer_code.")
except Exception as e:
    pass

try:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sensor_logs (
        id SERIAL PRIMARY KEY,
        transformer_code VARCHAR(255) REFERENCES transformers(transformer_code),
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
    print(e)

try:
    cur.execute("""
    CREATE TABLE IF NOT EXISTS outages (
        id SERIAL PRIMARY KEY,
        transformer_code VARCHAR(255) REFERENCES transformers(transformer_code),
        started_at TIMESTAMP WITH TIME ZONE,
        resolved_at TIMESTAMP WITH TIME ZONE,
        status VARCHAR(50),
        cause VARCHAR(255),
        affected_consumers_estimated INTEGER,
        health_score_at_outage INTEGER,
        failure_risk_at_outage FLOAT,
        UNIQUE(transformer_code, started_at)
    );
    """)
    print("Created outages table.")
except Exception as e:
    print(e)

print("DB fix complete.")
