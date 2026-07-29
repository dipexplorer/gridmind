import os
import joblib
import pandas as pd
import numpy as np
import random

base_dir = "/home/dipuser/DIP/INTERNSHIP/APDCL/backend"
model_path = os.path.join(base_dir, "ml_models", "isolation_forest.pkl")
model = joblib.load(model_path)

print("Loaded Isolation Forest model successfully.")
features = ["temperature_c", "load_percentage", "voltage_lv", "current_a"]

# Test normal
normal_data = []
for h in range(24):
    temp = 32.0 + random.uniform(-2, 2)
    load = random.uniform(50, 70)
    voltage = 410.0
    current = 80.0
    normal_data.append([temp, load, voltage, current])
df_norm = pd.DataFrame(normal_data, columns=features)
raw_norm = model.decision_function(df_norm)
score_norm = 35 - (raw_norm * 200)
print(f"Normal Raw Scores: Min={np.min(raw_norm):.4f}, Max={np.max(raw_norm):.4f}, Mean={np.mean(raw_norm):.4f}")
print(f"Normal Anomaly Score Mean: {np.mean(score_norm):.2f}")

# Test anomalous
anom_data = []
for h in range(24):
    temp = 95.0 + random.uniform(-2, 2)
    load = random.uniform(115, 130)
    voltage = 360.0
    current = 200.0
    anom_data.append([temp, load, voltage, current])
df_anom = pd.DataFrame(anom_data, columns=features)
raw_anom = model.decision_function(df_anom)
score_anom = 35 - (raw_anom * 200)
print(f"Anomalous Raw Scores: Min={np.min(raw_anom):.4f}, Max={np.max(raw_anom):.4f}, Mean={np.mean(raw_anom):.4f}")
print(f"Anomalous Anomaly Score Mean: {np.mean(score_anom):.2f}")
