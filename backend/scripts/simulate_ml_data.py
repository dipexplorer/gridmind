import os
import random
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import DB Models
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.asset import Transformer
from models.timeseries import LoadReading

from core.config import settings
DB_URL = settings.DATABASE_URL


engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def simulate_telemetry():
    print("🔌 Starting Telemetry Simulation for ML Model...")
    db = SessionLocal()
    
    try:
        # Fetch up to 10 random transformers
        transformers = db.query(Transformer).limit(10).all()
        if not transformers:
            print("❌ No transformers found in database. Please run the seed script first.")
            return

        print(f"📊 Found {len(transformers)} transformers. Generating data...\n")

        readings_to_insert = []
        now = datetime.now(timezone.utc)

        for i, t in enumerate(transformers):
            # Make half of them normal and half anomalous
            if i % 2 == 0:
                # 🟢 NORMAL / HEALTHY TELEMETRY
                status = "🟢 HEALTHY"
                load_pct = random.uniform(30.0, 70.0)      # Normal Load (30-70%)
                temp_c = random.uniform(40.0, 65.0)        # Normal Oil Temp (40-65°C)
                v_lv = random.uniform(400.0, 425.0)        # Normal Voltage
                curr_a = random.uniform(50.0, 150.0)       # Normal Current
            else:
                # 🔴 ANOMALOUS / CRITICAL TELEMETRY
                status = "🔴 ANOMALOUS (High Risk)"
                load_pct = random.uniform(110.0, 140.0)    # Overload! (> 100%)
                temp_c = random.uniform(85.0, 110.0)       # Overheating! (> 85°C)
                v_lv = random.uniform(350.0, 390.0)        # Voltage Drop
                curr_a = random.uniform(300.0, 400.0)      # High Current Spike
                
            print(f"-> Transformer [{t.transformer_code}] | Profile: {status}")
            print(f"   Load: {load_pct:.2f}% | Temp: {temp_c:.2f}°C | Voltage: {v_lv:.2f}V\n")

            reading = LoadReading(
                time=now,
                transformer_id=t.id,
                load_kw=(float(t.rated_kva) * (load_pct/100) * 0.9) if t.rated_kva else 100.0,
                load_kvar=random.uniform(5.0, 20.0),
                load_percentage=load_pct,
                voltage_lv=v_lv,
                current_a=curr_a,
                temperature_c=temp_c,
                source="SIMULATION_SCRIPT"
            )
            readings_to_insert.append(reading)

        # Bulk insert into DB
        db.add_all(readings_to_insert)
        db.commit()
        print(f"✅ Successfully injected {len(readings_to_insert)} readings into Supabase PostgreSQL!")
        print("🚀 Celery ML Background Task will now pick these up and calculate Anomaly Scores & SHAP values.")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    simulate_telemetry()
