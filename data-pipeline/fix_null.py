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

# Get all columns for transformers table and drop NOT NULL constraint
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='transformers'")
for row in cur.fetchall():
    col = row[0]
    if col not in ['id', 'transformer_code']: # keep PK and unique key not null
        try:
            cur.execute(f"ALTER TABLE transformers ALTER COLUMN {col} DROP NOT NULL;")
        except:
            pass

print("Dropped NOT NULL constraints.")
