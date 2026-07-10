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

try:
    cur.execute("ALTER TABLE transformers ALTER COLUMN id SET DEFAULT gen_random_uuid();")
    print("Added default uuid to id.")
except Exception as e:
    print(e)
