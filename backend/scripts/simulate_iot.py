import sys
import os
import time
import random
import datetime

# Add the parent directory to sys.path so we can import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.asset import Transformer
from models.timeseries import LoadReading
from tasks.scoring import score_all_transformers

def run_simulator():
    print("🚀 Starting GridMind IoT Simulator...")
    db = SessionLocal()
    
    try:
        transformers = db.query(Transformer).all()
        if not transformers:
            print("❌ No transformers found in the database. Please add transformers first.")
            return

        print(f"📡 Tracking {len(transformers)} transformers.")
        
        loop_count = 0
        while True:
            loop_count += 1
            now = datetime.datetime.utcnow()
            print(f"\n[{now.strftime('%H:%M:%S')}] Generating synthetic IoT telemetry (Iteration {loop_count})...")
            
            for t in transformers:
                # 90% chance normal, 10% chance anomaly for demo purposes
                is_anomaly = random.random() < 0.10
                
                if is_anomaly:
                    # Spike values
                    voltage = random.uniform(180.0, 200.0) # Low voltage dip
                    current = random.uniform(80.0, 120.0)  # High current
                    oil_temp = random.uniform(85.0, 110.0) # High temp
                else:
                    # Normal values
                    voltage = random.uniform(220.0, 240.0)
                    current = random.uniform(20.0, 45.0)
                    oil_temp = random.uniform(45.0, 65.0)
                    
                reading = LoadReading(
                    transformer_id=t.id,
                    time=now,
                    voltage_v=voltage,
                    current_a=current,
                    oil_temperature_c=oil_temp,
                    ambient_temperature_c=random.uniform(25.0, 35.0)
                )
                db.add(reading)
            
            db.commit()
            print("✅ Telemetry saved to database.")

            # Every 3 loops (approx 30 seconds), trigger the AI Background Scoring
            if loop_count % 3 == 0:
                print("🧠 Forcing AI Scoring Run to analyze latest telemetry...")
                try:
                    score_all_transformers()
                    print("✅ AI Scoring completed. Any critical alerts were broadcasted via WebSockets.")
                except Exception as e:
                    print(f"⚠️ AI Scoring failed: {e}")
                    
            print("💤 Waiting 10 seconds before next ping...")
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n🛑 Simulator stopped by user.")
    except Exception as e:
        print(f"\n❌ Simulator crashed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_simulator()
