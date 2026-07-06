import os
import sys
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sklearn.ensemble import IsolationForest
import joblib

# Add the parent directory to sys.path to import from core and models
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from models.asset import Transformer
from models.timeseries import LoadReading

# Setup Database Connection
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def generate_telemetry_data(session, transformers, days=30):
    print(f"Generating {days} days of dummy telemetry data for {len(transformers)} transformers...")
    
    # Check if data already exists to avoid massive duplication
    existing_count = session.query(LoadReading).count()
    if existing_count > 0:
        print(f"Found {existing_count} existing telemetry records. Deleting old records for clean seed...")
        session.query(LoadReading).delete()
        session.commit()

    now = datetime.now()
    readings = []
    
    # We will make 10% of transformers have "anomalous" behavior
    anomalous_tfs = random.sample(transformers, max(1, int(len(transformers) * 0.1)))
    anomalous_ids = [t.id for t in anomalous_tfs]

    for t in transformers:
        is_anomalous = t.id in anomalous_ids
        
        # Base stats for this transformer
        base_temp = 45.0
        base_load = 60.0
        
        # Generate hourly data
        for i in range(days * 24):
            timestamp = now - timedelta(hours=i)
            
            # Normal diurnal cycle (higher load/temp during day)
            hour_factor = np.sin(timestamp.hour / 24.0 * 2 * np.pi - np.pi/2) # -1 at midnight, 1 at noon
            
            if is_anomalous and i < 72: 
                # Last 3 days have anomalous behavior for these specific transformers
                # e.g., high temp, low load (cooling failure)
                temp = base_temp + random.uniform(30, 50) # Very high temp
                load = base_load + random.uniform(-20, 10) # Normal/Low load
            else:
                temp = base_temp + (hour_factor * 15) + random.uniform(-5, 5)
                load = base_load + (hour_factor * 25) + random.uniform(-10, 10)
            
            voltage = 400 + random.uniform(-10, 10)
            rated_kva_float = float(t.rated_kva)
            current = (load / 100 * rated_kva_float * 1000) / (1.732 * voltage) # Approximate current

            reading = LoadReading(
                time=timestamp,
                transformer_id=t.id,
                load_kw=(load / 100) * rated_kva_float * 0.9,
                load_kvar=(load / 100) * rated_kva_float * 0.4,
                load_percentage=max(0, min(load, 150)), # clamp 0-150
                voltage_lv=voltage,
                current_a=current,
                temperature_c=max(20, min(temp, 120)), # clamp 20-120
                source='SIMULATION'
            )
            readings.append(reading)
            
            if len(readings) >= 5000:
                session.bulk_save_objects(readings)
                session.commit()
                readings = []

    if readings:
        session.bulk_save_objects(readings)
        session.commit()
        
    print(f"Data generation complete.")

def train_isolation_forest(session):
    print("Fetching data for training Isolation Forest model...")
    # Fetch data into pandas
    query = session.query(LoadReading.temperature_c, LoadReading.load_percentage, LoadReading.voltage_lv, LoadReading.current_a).statement
    df = pd.read_sql(query, session.bind)
    
    if df.empty:
        print("No data found for training!")
        return

    print(f"Training on {len(df)} records...")
    
    # Features used for anomaly detection
    features = ['temperature_c', 'load_percentage', 'voltage_lv', 'current_a']
    X = df[features].fillna(0)

    # Train Isolation Forest
    model = IsolationForest(contamination=settings.ANOMALY_CONTAMINATION, random_state=42, n_jobs=-1)
    model.fit(X)

    # Save model
    os.makedirs(settings.MODEL_DIR, exist_ok=True)
    model_path = os.path.join(settings.MODEL_DIR, "isolation_forest.pkl")
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

def main():
    session = SessionLocal()
    try:
        transformers = session.query(Transformer).all()
        if not transformers:
            print("No transformers found in database. Please add substations/transformers first.")
            return
            
        generate_telemetry_data(session, transformers, days=30)
        train_isolation_forest(session)
    finally:
        session.close()

if __name__ == "__main__":
    main()
