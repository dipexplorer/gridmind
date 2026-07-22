"""
GridMind ML Analytics API Endpoints
======================================
Serves results from the Academic ML Suite:
  - GET /ml/benchmark      → 5-model comparison table + ROC-AUC data
  - GET /ml/deep-learning  → LSTM + 1D-CNN training results
  - GET /ml/rl-agent       → RL Agent policy and results
  - POST /ml/run-benchmark → Trigger a fresh benchmark run (background task)
"""

import os
import json
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ML Analytics Suite"])

ML_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ml_models")


def _load_json(filename: str) -> Dict[str, Any]:
    """Helper to load a JSON result file from ml_models directory."""
    path = os.path.join(ML_MODELS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail=f"Results not found. Please run the training pipeline first. "
                   f"Missing: {filename}"
        )
    with open(path, "r") as f:
        return json.load(f)


# ─── GET /ml/benchmark ────────────────────────────────────────────────────────
@router.get("/benchmark", summary="Get 5-Model ML Benchmark Results")
async def get_benchmark_results():
    """
    Returns the comparison table of all 5 supervised ML models including:
    - Accuracy, Precision, Recall, F1-Score, ROC-AUC
    - Per-class ROC curve data for charting
    - Best performing model summary
    """
    return _load_json("benchmark_results.json")


# ─── GET /ml/deep-learning ────────────────────────────────────────────────────
@router.get("/deep-learning", summary="Get LSTM + 1D-CNN Training Results")
async def get_deep_learning_results():
    """
    Returns training results for PyTorch LSTM and 1D-CNN models:
    - Architecture details
    - Training loss history
    - Final validation accuracy/loss
    """
    return _load_json("deep_learning_results.json")


# ─── GET /ml/rl-agent ─────────────────────────────────────────────────────────
@router.get("/rl-agent", summary="Get Reinforcement Learning Agent Results")
async def get_rl_results():
    """
    Returns Q-Learning agent training results:
    - Success rate (% of critical scenarios resolved)
    - Average cumulative reward
    - Hyperparameters (alpha, gamma, epsilon)
    """
    return _load_json("rl_results.json")


# ─── GET /ml/summary ──────────────────────────────────────────────────────────
@router.get("/summary", summary="Get Complete ML Suite Summary")
async def get_ml_summary():
    """
    Returns a combined summary of all ML models in the GridMind system:
    - Current production models (Isolation Forest + Cox PH)
    - Academic benchmark suite (RF, XGBoost, KNN, LR, SVM)
    - Deep Learning models (LSTM + 1D-CNN)
    - RL Agent
    """
    summary = {
        "production_models": {
            "isolation_forest": {
                "status":    "ACTIVE",
                "type":      "Unsupervised Anomaly Detection",
                "purpose":   "Real-time transformer anomaly scoring",
                "input":     ["temperature_c", "load_percentage", "voltage_lv", "current_a"],
                "output":    "Anomaly Score (0-100%)",
                "pkl_saved": os.path.exists(os.path.join(ML_MODELS_DIR, "isolation_forest.pkl"))
            },
            "cox_ph": {
                "status":    "ACTIVE",
                "type":      "Survival Analysis",
                "purpose":   "Remaining Useful Life (RUL) estimation",
                "input":     ["temperature_c", "load_percentage"],
                "output":    "Expected lifetime in days",
                "pkl_saved": os.path.exists(os.path.join(ML_MODELS_DIR, "survival_model.pkl"))
            }
        },
        "benchmark_suite": {
            "status": "TRAINED" if os.path.exists(
                os.path.join(ML_MODELS_DIR, "benchmark_results.json")) else "NOT_TRAINED",
            "models": ["Random Forest", "XGBoost", "KNN", "Logistic Regression", "SVM"],
            "metrics": ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"],
        },
        "deep_learning": {
            "lstm_trained":  os.path.exists(os.path.join(ML_MODELS_DIR, "lstm_forecaster.pt")),
            "cnn1d_trained": os.path.exists(os.path.join(ML_MODELS_DIR, "cnn1d_fault_classifier.pt")),
        },
        "rl_agent": {
            "status": "TRAINED" if os.path.exists(
                os.path.join(ML_MODELS_DIR, "rl_agent.pkl")) else "NOT_TRAINED",
            "algorithm": "Q-Learning (Tabular)",
            "purpose": "Prescriptive load balancing"
        }
    }
    return summary


# ─── POST /ml/run-benchmark ───────────────────────────────────────────────────
@router.post("/run-benchmark", summary="Trigger ML Benchmark Training (Background)")
async def trigger_benchmark(background_tasks: BackgroundTasks):
    """
    Triggers a full benchmark training run in the background.
    Returns immediately with a task status message.
    """
    def run_all():
        try:
            logger.info("Background ML benchmark triggered via API")
            from services.ml_benchmark import run_benchmark
            run_benchmark()
            logger.info("ML benchmark completed successfully")
        except Exception as e:
            logger.error(f"ML benchmark failed: {e}")

    background_tasks.add_task(run_all)
    return {
        "status": "STARTED",
        "message": "ML benchmark training started in background. "
                   "Check GET /ml/benchmark in ~30 seconds for results."
    }


# ─── POST /ml/run-deep-learning ───────────────────────────────────────────────
@router.post("/run-deep-learning", summary="Trigger Deep Learning Training (Background)")
async def trigger_deep_learning(background_tasks: BackgroundTasks):
    """Triggers LSTM + 1D-CNN training in background."""
    def run_dl():
        try:
            logger.info("Background deep learning training triggered via API")
            from services.deep_learning import train_all_deep_learning_models
            train_all_deep_learning_models()
            logger.info("Deep learning training completed successfully")
        except Exception as e:
            logger.error(f"Deep learning training failed: {e}")

    background_tasks.add_task(run_dl)
    return {
        "status": "STARTED",
        "message": "LSTM + 1D-CNN training started in background. "
                   "Check GET /ml/deep-learning in ~2-5 minutes for results."
    }


# ─── POST /ml/run-rl-agent ────────────────────────────────────────────────────
@router.post("/run-rl-agent", summary="Trigger RL Agent Training (Background)")
async def trigger_rl_agent(background_tasks: BackgroundTasks):
    """Triggers Q-Learning RL agent training in background."""
    def run_rl():
        try:
            logger.info("Background RL agent training triggered via API")
            from services.rl_agent import train_rl_agent
            train_rl_agent()
            logger.info("RL agent training completed successfully")
        except Exception as e:
            logger.error(f"RL agent training failed: {e}")

    background_tasks.add_task(run_rl)
    return {
        "status": "STARTED",
        "message": "RL agent training started. "
                   "Check GET /ml/rl-agent in ~30 seconds for results."
    }
