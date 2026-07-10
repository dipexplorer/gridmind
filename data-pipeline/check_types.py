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
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='transformers'")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]}")
