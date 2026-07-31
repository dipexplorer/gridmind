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
    features = [
        "temperature_c", "load_percentage", "voltage_lv", 
        "current_a", "ambient_temperature", "age_years", 
        "rated_kva", "power_factor",
        "load_ratio", "current_ratio", "voltage_deviation", 
        "temperature_rise", "stress_index"
    ]
    X = df[features]
    
    # Fit unsupervised Isolation Forest
    # contamination = actual anomaly rate: (WARNING + CRITICAL) / total
    # With corrected physics: ~(344 + 869) / 10000 ≈ 0.12
    # Pulled from config so it can be overridden via environment variable.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core.config import settings
    contamination = settings.ANOMALY_CONTAMINATION  # default: 0.05, set to 0.12 in config
    model = IsolationForest(n_estimators=150, contamination=contamination, random_state=42)
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
            
    df_survival = df[features].copy()
    df_survival["duration"] = durations
    df_survival["event"] = events
    
    # Add small random noise to duration to prevent ties in lifelines fitting
    df_survival["duration"] = df_survival["duration"] + np.random.uniform(0.01, 0.1, size=len(df_survival))
    
    # Fit Cox Proportional Hazards Model
    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_survival, duration_col="duration", event_col="event")
    
    # Save survival model
    joblib.dump(cph, os.path.join(model_dir, "survival_model.pkl"))
    print("Successfully trained and saved Cox Survival model to ml_models/survival_model.pkl")

    # 3. Train Benchmark XGBoost & Random Forest
    from xgboost import XGBClassifier
    from sklearn.ensemble import RandomForestClassifier

    y = df["risk_label"]

    print("Training benchmark Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    joblib.dump(rf, os.path.join(model_dir, "benchmark_random_forest.pkl"))
    print("Successfully saved Random Forest benchmark.")

    print("Training benchmark XGBoost...")
    xgb = XGBClassifier(n_estimators=100, random_state=42, use_label_encoder=False, eval_metric="mlogloss")
    xgb.fit(X, y)
    joblib.dump(xgb, os.path.join(model_dir, "benchmark_xgboost.pkl"))
    print("Successfully saved XGBoost benchmark.")

if __name__ == "__main__":
    train_production_models()
