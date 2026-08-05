import os
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report, confusion_matrix
)
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

    features = [
        "temperature_c", "load_percentage", "voltage_lv",
        "current_a", "ambient_temperature", "age_years",
        "rated_kva", "power_factor",
        "load_ratio", "current_ratio", "voltage_deviation",
        "temperature_rise", "stress_index"
    ]

    # ─── 1. Train Isolation Forest (Production Anomaly Detection) ─────────────
    #
    # CORRECTED METHODOLOGY (5 issues fixed from original approach):
    #
    # Problem 1 – Same data for train & test (inflated accuracy ~96.5%):
    #   Old:  iso_forest.fit(X); predictions = iso_forest.predict(X)
    #   Fix:  Split SAFE data 80/20; evaluate on unseen test split.
    #
    # Problem 2 – Abnormal rows in training data:
    #   Old:  model.fit(X)  ← X contained WARNING + CRITICAL rows
    #   Fix:  safe_df = df[df["risk_label"] == 0]; model.fit(X_safe_train)
    #         Isolation Forest learns "what normal looks like", not anomalies.
    #
    # Problem 3 – contamination=0.12 was artificially exact:
    #   Old:  contamination = settings.ANOMALY_CONTAMINATION  # = 0.12
    #         Dataset had exactly 12.13% anomalies → suspiciously convenient.
    #   Fix:  contamination="auto" → sklearn uses default 0.1 heuristic,
    #         independent of known label distribution.
    #
    # Problem 4 – WARNING class missing from evaluation:
    #   Old script produced no WARNING row in classification report.
    #   Fix:  Explicit per-class reporting for SAFE, WARNING, CRITICAL.
    #
    # Problem 5 – Treating IF as a 3-class classifier:
    #   IF inherently outputs Normal / Anomalous (binary).
    #   Fix:  Binary evaluation: SAFE=Normal(0), WARNING+CRITICAL=Anomaly(1).
    #         Per-class false-positive rates reported separately for clarity.

    print("\n" + "="*60)
    print("1. Training Isolation Forest (Anomaly Detection)")
    print("="*60)

    # Step A: Separate SAFE (normal) samples from anomalous samples
    safe_df     = df[df["risk_label"] == 0]
    warning_df  = df[df["risk_label"] == 1]
    critical_df = df[df["risk_label"] == 2]

    n_safe     = len(safe_df)
    n_warning  = len(warning_df)
    n_critical = len(critical_df)
    print(f"Dataset:  SAFE={n_safe}  WARNING={n_warning}  CRITICAL={n_critical}  Total={len(df)}")

    # Step B: 80/20 split of SAFE data
    # Train only on SAFE (healthy transformer behaviour)
    X_safe = safe_df[features].values
    X_safe_train, X_safe_test = train_test_split(
        X_safe, test_size=0.2, random_state=42
    )
    print(f"SAFE split:  {len(X_safe_train)} training  |  {len(X_safe_test)} unseen testing")

    # Step C: Build evaluation set = unseen SAFE + ALL WARNING + ALL CRITICAL
    X_warning  = warning_df[features].values
    X_critical = critical_df[features].values

    X_eval = np.vstack([X_safe_test, X_warning, X_critical])
    # Binary ground truth: 0=Normal(SAFE), 1=Anomaly(WARNING or CRITICAL)
    y_eval = np.array(
        [0] * len(X_safe_test) +
        [1] * len(X_warning) +
        [1] * len(X_critical)
    )
    # Keep 3-class labels for per-class false-positive reporting
    y_eval_multi = np.array(
        [0] * len(X_safe_test) +
        [1] * len(X_warning) +
        [2] * len(X_critical)
    )
    print(f"Evaluation: {len(X_safe_test)} SAFE + {n_warning} WARNING + {n_critical} CRITICAL = {len(X_eval)} samples")

    # Step D: Train on SAFE-only, contamination="auto" (no label leakage)
    model = IsolationForest(
        n_estimators=150,
        contamination="auto",   # sklearn default heuristic, not derived from labels
        random_state=42
    )
    model.fit(X_safe_train)

    # Step E: Evaluate — IF returns +1 (normal) and -1 (anomaly)
    raw_preds = model.predict(X_eval)               # +1 or -1
    y_pred    = np.where(raw_preds == 1, 0, 1)      # remap: normal=0, anomaly=1

    # ─── Binary metrics (SAFE vs Anomaly)
    acc  = accuracy_score(y_eval, y_pred)
    prec = precision_score(y_eval, y_pred, zero_division=0)
    rec  = recall_score(y_eval, y_pred, zero_division=0)    # anomaly recall
    f1   = f1_score(y_eval, y_pred, zero_division=0)

    print(f"\nIsolation Forest — Binary Evaluation (Normal vs Anomaly)")
    print(f"  Accuracy : {acc*100:.1f}%")
    print(f"  Precision: {prec:.4f}  (of flagged, how many are true anomalies)")
    print(f"  Recall   : {rec:.4f}  (of true anomalies, how many caught)")
    print(f"  F1-Score : {f1:.4f}")

    # ─── Per-class false-positive / catch rates for transparency
    print(f"\nPer-class detection rates:")
    for label, name in [(0, "SAFE"), (1, "WARNING"), (2, "CRITICAL")]:
        mask  = y_eval_multi == label
        flagged = (y_pred[mask] == 1).sum()
        total   = mask.sum()
        pct     = (flagged / total * 100) if total > 0 else 0
        print(f"  {name:<10}: {flagged:>4}/{total:<4} flagged as anomaly ({pct:.2f}%)")

    print(f"\nNote: ~20% SAFE false-positives is expected improvement target,")
    print(f"not an artifact of inflated evaluation like the old 96.5% result.")

    # Step F: Save production model — trained on SAFE-only for runtime prediction
    model_dir = os.path.join(base_dir, "ml_models")
    os.makedirs(model_dir, exist_ok=True)
    joblib.dump(model, os.path.join(model_dir, "isolation_forest.pkl"))
    print(f"\nSaved: isolation_forest.pkl  (trained on {len(X_safe_train)} SAFE samples)")

    # ─── 2. Train Cox Proportional Hazards Model (Remaining Useful Life) ────
    print("\n" + "="*60)
    print("2. Training Cox Proportional Hazards (Survival / RUL)")
    print("="*60)

    np.random.seed(42)
    durations = []
    events    = []

    for label in df["risk_label"]:
        if label == 2:      # CRITICAL — fails in 1–15 days
            durations.append(np.random.randint(1, 15))
            events.append(1)
        elif label == 1:    # WARNING — fails in 15–90 days
            durations.append(np.random.randint(15, 90))
            events.append(1)
        else:               # SAFE — lasts up to 10 years, low random failure chance
            durations.append(np.random.randint(90, 3650))
            events.append(np.random.choice([0, 1], p=[0.85, 0.15]))

    df_survival = df[features].copy()
    df_survival["duration"] = durations
    df_survival["event"]    = events
    # Small noise to prevent tied duration values in lifelines
    df_survival["duration"] += np.random.uniform(0.01, 0.1, size=len(df_survival))

    cph = CoxPHFitter(penalizer=0.1)
    cph.fit(df_survival, duration_col="duration", event_col="event")

    joblib.dump(cph, os.path.join(model_dir, "survival_model.pkl"))
    print("Saved: survival_model.pkl")

    # ─── 3. Train Benchmark Classifiers (Random Forest + XGBoost) ────────────
    print("\n" + "="*60)
    print("3. Training Benchmark Classifiers (RF + XGBoost)")
    print("="*60)

    from xgboost import XGBClassifier
    from sklearn.ensemble import RandomForestClassifier

    X_all = df[features]
    y_all = df["risk_label"]

    print("Training benchmark Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X_all, y_all)
    joblib.dump(rf, os.path.join(model_dir, "benchmark_random_forest.pkl"))
    print("Saved: benchmark_random_forest.pkl")

    print("Training benchmark XGBoost...")
    xgb = XGBClassifier(
        n_estimators=100,
        random_state=42,
        use_label_encoder=False,
        eval_metric="mlogloss"
    )
    xgb.fit(X_all, y_all)
    joblib.dump(xgb, os.path.join(model_dir, "benchmark_xgboost.pkl"))
    print("Saved: benchmark_xgboost.pkl")

    print("\n" + "="*60)
    print("All models trained and saved successfully.")
    print("="*60)


if __name__ == "__main__":
    train_production_models()
