import os, json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv(".env")
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
for table in ["transformers", "sensor_logs", "outages"]:
    try:
        res = supabase.table(table).select("*").limit(1).execute()
        if res.data:
            print(f"--- {table} columns: ---")
            print(list(res.data[0].keys()))
        else:
            print(f"{table} is empty. Trying to insert a dummy to get error with columns")
    except Exception as e:
        print(f"Error reading {table}: {e}")
