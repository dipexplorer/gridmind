import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import scipy.integrate

# Monkey patch trapz for newer scipy compatibility with lifelines unpickling
if not hasattr(scipy.integrate, 'trapz'):
    if hasattr(scipy.integrate, 'trapezoid'):
        scipy.integrate.trapz = scipy.integrate.trapezoid
    elif hasattr(np, 'trapezoid'):
        scipy.integrate.trapz = np.trapezoid

from lifelines import CoxPHFitter
import joblib

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def train_production_models():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "ml_training_dataset.csv")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: Dataset not found at {csv_path}. Please run generate_datasets.py first.")
        return
        
    print(f"Loading training dataset from: {csv_path}")
    df = pd.read_csv(csv_path)
    
    # 1. Train Isolation Forest (Production Anomaly Detection)
    features = ["temperature_c", "load_percentage", "voltage_lv", "current_a", "ambient_temperature", "age_years", "rated_kva"]
    X = df[features]
    
    # Fit unsupervised Isolation Forest
    # contamination=0.30 matches our stratified training set: 15% warning + 15% critical = 30% anomalies
    model = IsolationForest(n_estimators=150, contamination=0.30, random_state=42)
    model.fit(X)
    
    # Save model
    model_dir = os.path.join(base_dir, "ml_models")
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(model, os.path.join(model_dir, "isolation_forest.pkl"))
    print("Successfully trained and saved Isolation Forest model to ml_models/isolation_forest.pkl")
    
    # 2. Train Cox Proportional Hazards Model (Remaining Useful Life)
    # Synthesize survival times based on physical risk label
    np.random.seed(42)
    durations = []
    events = []
    
    for label in df["risk_label"]:
        if label == 2:  # CRITICAL
            durations.append(np.random.randint(1, 15))  # Fails in 1-15 days
            events.append(1)  # Failure event occurred
        elif label == 1:  # WARNING
            durations.append(np.random.randint(15, 90))  # Fails in 15-90 days
            events.append(1)  # Failure event occurred
        else:  # HEALTHY
            durations.append(np.random.randint(90, 3650))  # Lasts up to 10 years
            events.append(np.random.choice([0, 1], p=[0.85, 0.15]))  # Low chance of random failure
            
    df_survival = pd.DataFrame({
        "temperature_c": df["temperature_c"],
        "load_percentage": df["load_percentage"],
        "duration": durations,
        "event": events
    })
    
    # Add small random noise to duration to prevent ties in lifelines fitting
    df_survival["duration"] = df_survival["duration"] + np.random.uniform(0.01, 0.1, size=len(df_survival))
    
    # Fit Cox Proportional Hazards Model
    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_survival, duration_col="duration", event_col="event")
    
    # Save survival model
    joblib.dump(cph, os.path.join(model_dir, "survival_model.pkl"))
    print("Successfully trained and saved Cox Survival model to ml_models/survival_model.pkl")

if __name__ == "__main__":
    train_production_models()
