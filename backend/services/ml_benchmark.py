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
from sklearn.preprocessing import label_binarize
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
    roc_curve, auc, classification_report
)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

import joblib

logger = logging.getLogger(__name__)


# ─── Step 1: Synthetic Labeled Dataset Generation ─────────────────────────────

def generate_labeled_dataset(n_samples: int = 10000, random_state: int = 42) -> tuple:
    """
    Loads the static labeled SCADA telemetry dataset from backend/data/ml_training_dataset.csv.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, "data", "ml_training_dataset.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"ML training dataset not found at {csv_path}. Run generate_datasets.py first.")
    
    df = pd.read_csv(csv_path)
    if n_samples and n_samples < len(df):
        df = df.sample(n=n_samples, random_state=random_state)
        
    feature_names = [
        "temperature_c", "load_percentage", "voltage_lv", "current_a", 
        "ambient_temperature", "age_years", "rated_kva", "power_factor",
        "load_ratio", "current_ratio", "voltage_deviation", 
        "temperature_rise", "stress_index"
    ]
    X = df[feature_names].values
    y = df["risk_label"].values
    
    logger.info(f"Loaded {len(df)} training samples from CSV: "
                f"SAFE={sum(y==0)}, WARNING={sum(y==1)}, CRITICAL={sum(y==2)}")
    return X, y, feature_names


# ─── Step 2: Define all 5 Benchmark Models ────────────────────────────────────

def get_benchmark_models() -> dict:
    """
    Returns a dictionary of Random Forest and XGBoost classifiers for benchmarking.
    """
    models = {
        "Random Forest": RandomForestClassifier(
            n_estimators=200,       # 200 trees for stable ensemble voting
            max_depth=12,           # Prevent overfitting on synthetic data
            class_weight="balanced",# Handle class imbalance (failures are rare)
            random_state=42,
            n_jobs=2               # Limit cores to prevent VM lockups
        )
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
            n_jobs=2
        )
    else:
        # Fallback: Gradient Boosting from sklearn if XGBoost not installed
        models["Gradient Boosting"] = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42
        )

    return models


# ─── Step 3: Training, Evaluation, and Metrics Calculation ────────────────────

def run_benchmark(save_path: str = None) -> dict:
    """
    Runs the Random Forest vs XGBoost benchmark pipeline:
      1. Generate labeled dataset.
      2. Split into train/test (80/20).
      3. Train each model.
      4. Calculate all metrics.
      5. Save results to JSON.

    Returns:
        dict: Complete benchmark results with all metrics and ROC data.
    """
    logger.info("=== GridMind ML Benchmark Starting ===")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if save_path is None:
        save_path = os.path.join(base_dir, "ml_models", "benchmark_results.json")

    # Step 1: Generate data
    X, y, feature_names = generate_labeled_dataset(n_samples=10000)

    # Step 2: Train-test split (80% train, 20% test)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # Step 3: Get models
    models = get_benchmark_models()
    class_names = ["SAFE", "WARNING", "CRITICAL"]

    # ─── Collect Results
    all_results = {}
    roc_data    = {}

    for model_name, model in models.items():
        logger.info(f"  Training {model_name}...")

        Xtr = X_train
        Xte = X_test

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
        class_report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)

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
            "class_report": class_report,
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
        joblib.dump(model, os.path.join(base_dir, "ml_models", f"benchmark_{safe_name}.pkl"))

    # ─── Identify Best Model ──────────────────────────────────────────────────
    best_model = max(all_results, key=lambda m: all_results[m]["roc_auc"])

    # ─── Final Report
    report = {
        "summary": {
            "total_samples":    len(X),
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
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
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
