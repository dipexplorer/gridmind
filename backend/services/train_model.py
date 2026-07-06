import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import numpy as np
import scipy.integrate
# Monkey patch trapz for newer scipy compatibility with lifelines
if not hasattr(scipy.integrate, 'trapz'):
    if hasattr(scipy.integrate, 'trapezoid'):
        scipy.integrate.trapz = scipy.integrate.trapezoid
    elif hasattr(np, 'trapezoid'):
        scipy.integrate.trapz = np.trapezoid

from lifelines import CoxPHFitter
import joblib

# Add backend directory to path to enable local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.timeseries import LoadReading

def train_models():
    db = SessionLocal()
    try:
        # 1. Fetch load readings from DB
        readings = db.query(LoadReading).all()
        if not readings:
            print("ERROR: No load readings found in database. Seed data first.")
            return

        # 2. Convert to Pandas DataFrame
        data = []
        for r in readings:
            data.append({
                "transformer_id": str(r.transformer_id),
                "load_percentage": float(r.load_percentage) if r.load_percentage is not None else 0.0,
                "voltage_lv": float(r.voltage_lv) if r.voltage_lv is not None else 0.0,
                "current_a": float(r.current_a) if r.current_a is not None else 0.0,
                "temperature_c": float(r.temperature_c) if r.temperature_c is not None else 0.0,
            })
        df = pd.DataFrame(data)

        # 3. Train Isolation Forest for Anomaly Detection
        features = ["load_percentage", "voltage_lv", "current_a", "temperature_c"]
        X = df[features]

        # contamination=0.1 means we expect roughly 10% anomalies in baseline
        model = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
        model.fit(X)

        # Ensure output directory exists
        os.makedirs("ml_models", exist_ok=True)

        # Save model
        joblib.dump(model, "ml_models/isolation_forest.pkl")
        print("Successfully trained and saved Isolation Forest model to ml_models/isolation_forest.pkl")

        # 4. Train Cox Proportional Hazards Model for Survival Analysis
        # decision_function returns negative values for anomalies, positive for normal
        scores = model.decision_function(X)
        # Scale anomaly score to 0-100 (where 100 is highly anomalous)
        # decision_function range is roughly [-0.5, 0.5]
        anomaly_scores = 100 * (0.5 - scores)
        
        df["anomaly_score"] = anomaly_scores
        # Synthesize duration: transformers with higher anomaly score have shorter "survival" duration
        np.random.seed(42)
        df["duration"] = np.random.randint(100, 3650, size=len(df)) # 100 days to 10 years
        # If score is > 70, we simulate an "event" (failure) occurred with higher probability
        df["event"] = (df["anomaly_score"] > 70).astype(int)
        
        # Fit Cox Proportional Hazards
        # Features to include in hazard function: temperature_c, load_percentage
        survival_df = df[["temperature_c", "load_percentage", "duration", "event"]].copy()
        # Add small random jitter to duration to avoid duplicate times (lifelines requirement)
        survival_df["duration"] = survival_df["duration"] + np.random.uniform(0, 1, size=len(survival_df))
        
        cph = CoxPHFitter(penalizer=0.1)
        cph.fit(survival_df, duration_col="duration", event_col="event")
        
        joblib.dump(cph, "ml_models/survival_model.pkl")
        print("Successfully trained and saved Cox Proportional Hazards model to ml_models/survival_model.pkl")

    except Exception as e:
        print(f"Error during model training: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    train_models()
