"""
GridMind Academic ML Benchmark Suite
======================================
This module implements a rigorous 5-model supervised classification benchmark
to satisfy academic requirements for:
  - Model comparison (Random Forest, XGBoost, KNN, Logistic Regression, SVM)
  - Standard metrics: Accuracy, Precision, Recall, F1-Score, ROC-AUC
  - Confusion matrices and ROC curve visualization

Why supervised classification here when Isolation Forest is unsupervised?
--------------------------------------------------------------------------
Isolation Forest cannot produce standard accuracy metrics because it has no
ground-truth labels in production. This benchmark module:
  1. Generates a synthetic labeled dataset (with known failure ground-truth).
  2. Trains 5 different supervised classifiers on the SAME dataset.
  3. Produces a side-by-side performance comparison table and ROC-AUC JSON.
  4. Exports results to ml_models/benchmark_results.json for the API to serve.
"""

import os
import json
import logging
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
    roc_curve, auc
)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

import joblib

logger = logging.getLogger(__name__)


# ─── Step 1: Synthetic Labeled Dataset Generation ─────────────────────────────

def generate_labeled_dataset(n_samples: int = 5000, random_state: int = 42) -> tuple:
    """
    Generates a synthetic SCADA telemetry dataset with known failure labels.

    Why synthetic? We do not have 10 years of APDCL labeled failure history.
    The physics-based rules below mirror real transformer failure conditions:
      - Thermal degradation: temp > 85°C + load > 90% → HIGH risk
      - Insulation failure:  temp > 90°C + voltage drop  → CRITICAL
      - Normal operation:    temp < 65°C + load < 75%   → LOW/SAFE

    Returns:
        X (np.ndarray): Feature matrix of shape (n_samples, 4)
        y (np.ndarray): Labels — 0=SAFE, 1=WARNING, 2=CRITICAL
        feature_names (list): Names of the 4 input features
    """
    np.random.seed(random_state)

    # Generate base telemetry with realistic ranges
    temp_c       = np.random.uniform(30.0, 110.0, n_samples)
    load_pct     = np.random.uniform(15.0, 140.0, n_samples)
    voltage_lv   = np.random.uniform(350.0, 430.0, n_samples)
    current_a    = np.random.uniform(20.0, 400.0, n_samples)

    # Physics-based label assignment (simulates engineering domain knowledge)
    labels = np.zeros(n_samples, dtype=int)  # Default: SAFE (0)

    warning_mask = (
        (temp_c > 70) & (temp_c <= 85) |
        (load_pct > 80) & (load_pct <= 95) |
        (voltage_lv < 385)
    )
    critical_mask = (
        ((temp_c > 85) & (load_pct > 90)) |
        ((temp_c > 90) & (voltage_lv < 380)) |
        (load_pct > 110)
    )

    labels[warning_mask]  = 1  # WARNING
    labels[critical_mask] = 2  # CRITICAL

    # Add realistic noise to prevent perfect separation (real-world variance)
    noise_flip_idx = np.random.choice(n_samples, size=int(n_samples * 0.03), replace=False)
    labels[noise_flip_idx] = np.random.randint(0, 3, size=len(noise_flip_idx))

    X = np.column_stack([temp_c, load_pct, voltage_lv, current_a])
    feature_names = ["temperature_c", "load_percentage", "voltage_lv", "current_a"]

    logger.info(f"Generated {n_samples} samples: "
                f"SAFE={sum(labels==0)}, WARNING={sum(labels==1)}, CRITICAL={sum(labels==2)}")
    return X, labels, feature_names


# ─── Step 2: Define all 5 Benchmark Models ────────────────────────────────────

def get_benchmark_models() -> dict:
    """
    Returns a dictionary of 5 classifier instances for benchmarking.

    Why these specific models?
    - Random Forest:     Ensemble tree model; robust to outliers and noise.
    - XGBoost:           State-of-the-art gradient boosting; highest accuracy on tabular data.
    - KNN:               Distance-based; simple baseline for comparison.
    - Logistic Reg.:     Linear classifier; interpretable baseline.
    - SVM:               Maximum-margin classifier; strong on small feature sets.
    """
    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=200,       # 200 trees for stable ensemble voting
            max_depth=12,           # Prevent overfitting on synthetic data
            class_weight="balanced",# Handle class imbalance (failures are rare)
            random_state=42,
            n_jobs=-1               # Use all CPU cores
        ),
        "Logistic Regression": LogisticRegression(
            max_iter=1000,          # Increase iterations for convergence
            C=1.0,                  # Regularization strength (1/lambda)
            class_weight="balanced",
            random_state=42,
            multi_class="multinomial"
        ),
        "K-Nearest Neighbors": KNeighborsClassifier(
            n_neighbors=7,          # K=7 — odd number to avoid ties
            metric="euclidean",     # Straight-line distance in feature space
            weights="distance"      # Closer neighbors have higher influence
        ),
        "SVM": SVC(
            kernel="rbf",           # Radial Basis Function — non-linear boundary
            C=1.0,                  # Regularization
            gamma="scale",          # Kernel coefficient
            class_weight="balanced",
            probability=True,       # Required for ROC-AUC calculation
            random_state=42
        ),
    }

    if XGBOOST_AVAILABLE:
        models["XGBoost"] = XGBClassifier(
            n_estimators=200,       # 200 boosting rounds (faster than 300)
            learning_rate=0.05,     # Small step size prevents overfitting
            max_depth=6,            # Maximum tree depth per round
            subsample=0.8,          # Row sampling per tree
            colsample_bytree=0.8,   # Feature sampling per tree
            eval_metric="mlogloss", # Multi-class log loss
            random_state=42,
            n_jobs=-1
        )
    else:
        # Fallback: Gradient Boosting from sklearn if XGBoost not installed
        models["GradientBoosting"] = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42
        )

    return models


# ─── Step 3: Training, Evaluation, and Metrics Calculation ────────────────────

def run_benchmark(save_path: str = "ml_models/benchmark_results.json") -> dict:
    """
    Runs the full 5-model benchmark pipeline:
      1. Generate labeled dataset.
      2. Split into train/test (80/20).
      3. Scale features (required for KNN, LR, SVM).
      4. Train each model.
      5. Calculate all metrics.
      6. Save results to JSON.

    Returns:
        dict: Complete benchmark results with all metrics and ROC data.
    """
    logger.info("=== GridMind Academic ML Benchmark Starting ===")

    # Step 1: Generate data
    X, y, feature_names = generate_labeled_dataset(n_samples=5000)

    # Step 2: Train-test split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # Step 3: Feature scaling
    # Why? KNN, SVM, and Logistic Regression are sensitive to feature scale.
    # Temperature is 30-110, but Current can be 20-400. Without scaling,
    # Current would dominate the distance calculations completely.
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled  = scaler.transform(X_test)  # Use SAME scaler — no data leakage!

    # Save the scaler for API use
    os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else "ml_models", exist_ok=True)
    joblib.dump(scaler, "ml_models/benchmark_scaler.pkl")

    # Step 4: Get models
    models = get_benchmark_models()
    class_names = ["SAFE", "WARNING", "CRITICAL"]

    # ─── Collect Results
    all_results = {}
    roc_data    = {}

    for model_name, model in models.items():
        logger.info(f"  Training {model_name}...")

        # Some models need scaled data (distance/gradient based)
        # Tree-based models (RF, XGBoost) do NOT need scaling
        needs_scaling = model_name in ["Logistic Regression", "K-Nearest Neighbors", "SVM"]
        Xtr = X_train_scaled if needs_scaling else X_train
        Xte = X_test_scaled  if needs_scaling else X_test

        # Train the model
        model.fit(Xtr, y_train)

        # Predict on test set
        y_pred       = model.predict(Xte)
        y_pred_proba = model.predict_proba(Xte)  # Probability scores for ROC-AUC

        # ─── Metric Calculations ──────────────────────────────────────────────
        accuracy  = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
        recall    = recall_score(y_test, y_pred, average="weighted", zero_division=0)
        f1        = f1_score(y_test, y_pred, average="weighted", zero_division=0)

        # ROC-AUC for multi-class (One-vs-Rest strategy)
        roc_auc = roc_auc_score(y_test, y_pred_proba, multi_class="ovr", average="weighted")

        # Cross-Validation Score (5-fold) — proves model generalizes beyond test set
        cv_scores = cross_val_score(model, Xtr, y_train, cv=5, scoring="f1_weighted")

        # Confusion Matrix
        cm = confusion_matrix(y_test, y_pred).tolist()

        logger.info(f"    {model_name}: Accuracy={accuracy:.3f}, F1={f1:.3f}, ROC-AUC={roc_auc:.3f}")

        # ─── Store Results
        all_results[model_name] = {
            "accuracy":    round(float(accuracy), 4),
            "precision":   round(float(precision), 4),
            "recall":      round(float(recall), 4),
            "f1_score":    round(float(f1), 4),
            "roc_auc":     round(float(roc_auc), 4),
            "cv_mean_f1":  round(float(cv_scores.mean()), 4),
            "cv_std_f1":   round(float(cv_scores.std()), 4),
            "confusion_matrix": cm,
        }

        # ─── ROC Curve Data (per class for charting)
        y_test_bin = label_binarize(y_test, classes=[0, 1, 2])
        roc_curves = {}
        for i, class_name in enumerate(class_names):
            fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_pred_proba[:, i])
            class_auc   = auc(fpr, tpr)
            roc_curves[class_name] = {
                "fpr":       fpr.tolist(),
                "tpr":       tpr.tolist(),
                "auc":       round(float(class_auc), 4)
            }
        roc_data[model_name] = roc_curves

        # Save each trained model
        safe_name = model_name.lower().replace(" ", "_")
        joblib.dump(model, f"ml_models/benchmark_{safe_name}.pkl")

    # ─── Identify Best Model ──────────────────────────────────────────────────
    best_model = max(all_results, key=lambda m: all_results[m]["roc_auc"])

    # ─── Final Report
    report = {
        "summary": {
            "total_samples":    5000,
            "train_samples":    len(X_train),
            "test_samples":     len(X_test),
            "feature_names":    feature_names,
            "class_labels":     class_names,
            "best_model":       best_model,
            "best_roc_auc":     all_results[best_model]["roc_auc"],
        },
        "models":   all_results,
        "roc_data": roc_data,
    }

    # Save the benchmark results
    os.makedirs("ml_models", exist_ok=True)
    with open(save_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info(f"=== Benchmark Complete. Best Model: {best_model} (AUC={report['summary']['best_roc_auc']}) ===")
    logger.info(f"Results saved to {save_path}")

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results = run_benchmark()
    print("\n=== BENCHMARK RESULTS TABLE ===")
    print(f"{'Model':<25} {'Accuracy':>10} {'Precision':>10} {'Recall':>10} {'F1':>10} {'ROC-AUC':>10}")
    print("-" * 75)
    for name, metrics in results["models"].items():
        print(f"{name:<25} {metrics['accuracy']:>10.4f} {metrics['precision']:>10.4f} "
              f"{metrics['recall']:>10.4f} {metrics['f1_score']:>10.4f} {metrics['roc_auc']:>10.4f}")
    print(f"\n🏆 Best Model: {results['summary']['best_model']} "
          f"(ROC-AUC={results['summary']['best_roc_auc']})")
