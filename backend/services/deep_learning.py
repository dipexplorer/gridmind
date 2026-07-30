"""
GridMind Deep Learning Module
================================
This module implements two PyTorch-based deep learning models:

1. LSTM (Long Short-Term Memory) — Time-Series Load Forecasting
   - Predicts the next 24 hours of transformer load and temperature
   - Uses sequential past-24-hour windows as input
   - Category: Deep Learning / Recurrent Neural Network

2. 1D-CNN (1-Dimensional Convolutional Neural Network) — Fault Classification
   - Scans the telemetry waveform for transient fault patterns
   - Classifies faults into: Normal, Thermal Surge, Voltage Dip, Overload
   - Category: Deep Learning / Convolutional Network

Why PyTorch over TensorFlow?
-------------------------------
PyTorch uses dynamic computation graphs, meaning the network architecture can
change at every forward pass. This makes debugging intuitive (standard Python
debugger works) and is the standard in modern research and production AI systems.
"""

import os
import logging
import numpy as np
import json

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import joblib

logger = logging.getLogger(__name__)

# ─── GPU or CPU auto-detection ────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
logger.info(f"Deep Learning Device: {DEVICE}")


# ═══════════════════════════════════════════════════════════════════════════════
# MODEL 1: LSTM — 24-Hour Load & Temperature Forecasting
# ═══════════════════════════════════════════════════════════════════════════════

class LSTMForecaster(nn.Module):
    """
    PyTorch LSTM model for multi-step time-series forecasting.

    Architecture:
    ─────────────────────────────────────────────────────
    Input  [batch, seq_len=24, input_size=4]
        → LSTM Layer 1 (hidden_size=128, num_layers=2, dropout=0.2)
        → Last hidden state [batch, 128]
        → Fully Connected Layer (128 → 64)
        → ReLU Activation
        → Fully Connected Layer (64 → horizon*output_size)
        → Reshape to [batch, horizon=24, output_size=2]
    Output [batch, 24, 2]  ← (load_pct, temperature_c) for next 24 hours
    ─────────────────────────────────────────────────────

    Why 2 LSTM Layers (Stacked LSTM)?
      - Layer 1 captures short-term patterns (hourly fluctuations).
      - Layer 2 captures long-term temporal dependencies (daily cycles).

    Why Dropout?
      - Randomly "turns off" 20% neurons during training to prevent overfitting.
    """

    def __init__(self, input_size: int = 4, hidden_size: int = 128,
                 num_layers: int = 2, dropout: float = 0.2,
                 forecast_horizon: int = 24, output_size: int = 2):
        super(LSTMForecaster, self).__init__()

        self.input_size       = input_size
        self.hidden_size      = hidden_size
        self.num_layers       = num_layers
        self.forecast_horizon = forecast_horizon
        self.output_size      = output_size

        # LSTM core: processes time-sequential input
        self.lstm = nn.LSTM(
            input_size  = input_size,
            hidden_size = hidden_size,
            num_layers  = num_layers,
            dropout     = dropout,
            batch_first = True    # Input shape: [batch, seq, features]
        )

        # Fully connected decoder head
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, forecast_horizon * output_size)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass: x shape [batch, seq_len, input_size]
        Returns: predictions [batch, forecast_horizon, output_size]
        """
        # LSTM returns: output [batch, seq, hidden], (h_n, c_n)
        _, (h_n, _) = self.lstm(x)

        # Take only the LAST LSTM layer's hidden state
        # h_n shape: [num_layers, batch, hidden_size]
        last_hidden = h_n[-1]  # [batch, hidden_size]

        # Decode to forecast
        out = self.fc(last_hidden)  # [batch, horizon * output_size]

        # Reshape to [batch, horizon, output_size]
        return out.view(-1, self.forecast_horizon, self.output_size)





# ═══════════════════════════════════════════════════════════════════════════════
# DATA GENERATION FOR DEEP LEARNING TRAINING
# ═══════════════════════════════════════════════════════════════════════════════

def generate_lstm_sequences(n_sequences: int = 2000, seq_len: int = 24,
                             random_state: int = 42) -> tuple:
    """
    Generates synthetic 24-hour SCADA sequences for LSTM training.

    Each sequence = 24 hourly readings of [temp, load, voltage, current].
    The LSTM target = the next 24 hours of [load, temp] values.

    Physics-based generation:
    - Evening peak hours (18:00-22:00) have 1.15x load multiplier.
    - Anomalous transformers have elevated base temperature/load.
    """
    np.random.seed(random_state)

    X_seqs, y_seqs = [], []

    for _ in range(n_sequences):
        is_anomalous = np.random.random() < 0.2  # 20% anomalous transformers

        # Base values for this transformer
        if is_anomalous:
            base_temp = np.random.uniform(80, 100)
            base_load = np.random.uniform(90, 130)
        else:
            base_temp = np.random.uniform(35, 65)
            base_load = np.random.uniform(25, 75)

        base_volt  = np.random.uniform(395, 425)
        base_curr  = np.random.uniform(40, 200)

        # Generate 48-hour window (24 input + 24 target)
        hours = np.arange(48)
        peak_factor = np.where((hours % 24 >= 18) & (hours % 24 <= 22), 1.15, 1.0)

        temp    = base_temp + np.random.normal(0, 2, 48) + (3.0 * (((hours%24)>=12) & ((hours%24)<=16)))
        load    = np.clip(base_load * peak_factor + np.random.normal(0, 3, 48), 0, 150)
        voltage = base_volt + np.random.normal(0, 3, 48)
        current = base_curr * peak_factor + np.random.normal(0, 8, 48)

        # Input: first 24 hours [temp, load, voltage, current]
        seq_in  = np.column_stack([temp[:24], load[:24], voltage[:24], current[:24]])
        # Target: next 24 hours [load, temp]
        seq_out = np.column_stack([load[24:], temp[24:]])

        X_seqs.append(seq_in)
        y_seqs.append(seq_out)

    return np.array(X_seqs, dtype=np.float32), np.array(y_seqs, dtype=np.float32)




# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

_lstm_model_cache = None
_lstm_norm_cache = None

def get_lstm_inference_engine():
    global _lstm_model_cache, _lstm_norm_cache
    if _lstm_model_cache is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "ml_models", "lstm_forecaster.pt")
        norm_path = os.path.join(base_dir, "ml_models", "lstm_normalization.pkl")
        
        if os.path.exists(model_path) and os.path.exists(norm_path):
            try:
                model = LSTMForecaster().to(DEVICE)
                model.load_state_dict(torch.load(model_path, map_location=DEVICE))
                model.eval()
                _lstm_model_cache = model
                _lstm_norm_cache = joblib.load(norm_path)
                logger.info("Loaded PyTorch LSTM Forecaster model weights and normalization parameters.")
            except Exception as e:
                logger.error(f"Error loading LSTM model weights: {e}", exc_info=True)
        else:
            logger.warning(f"LSTM model or normalization pickle missing at {model_path}. Forecasts will use mathematical fallbacks.")
    return _lstm_model_cache, _lstm_norm_cache

def predict_lstm_forecast(past_sequence_24h: np.ndarray) -> np.ndarray:
    """
    Takes a sequence of shape (24, 4) representing [temp, load, voltage, current] of past 24 hours.
    Returns forecasted next 24 hours sequence of shape (24, 2) representing [load_pct, temp_c].
    """
    model, norm = get_lstm_inference_engine()
    if model is None or norm is None:
        # Fallback cyclic forecast if weights aren't trained
        forecast = []
        base_load = past_sequence_24h[-1, 1]
        base_temp = past_sequence_24h[-1, 0]
        for h in range(1, 25):
            peak = 1.15 if 18 <= ((h + 12) % 24) <= 22 else 1.0
            forecast.append([base_load * peak, base_temp + (h * 0.1)])
        return np.array(forecast)
    
    try:
        # 1. Normalize the input sequence using stored mean and std
        X_mean = norm["X_mean"]
        X_std = norm["X_std"]
        y_mean = norm["y_mean"]
        y_std = norm["y_std"]
        
        seq_norm = (past_sequence_24h - X_mean) / (X_std + 1e-8)
        
        # 2. Add batch dimension: shape (1, 24, 4)
        seq_tensor = torch.tensor(seq_norm, dtype=torch.float32).unsqueeze(0).to(DEVICE)
        
        # 3. Model forward pass
        with torch.no_grad():
            pred_norm = model(seq_tensor) # output shape: [1, 24, 2]
            pred_norm = pred_norm.squeeze(0).cpu().numpy() # shape: [24, 2]
            
        # 4. Denormalize the output
        predictions = (pred_norm * (y_std + 1e-8)) + y_mean
        return predictions
    except Exception as e:
        logger.error(f"LSTM prediction run failed: {e}", exc_info=True)
        forecast = []
        base_load = past_sequence_24h[-1, 1]
        base_temp = past_sequence_24h[-1, 0]
        for h in range(1, 25):
            peak = 1.15 if 18 <= ((h + 12) % 24) <= 22 else 1.0
            forecast.append([base_load * peak, base_temp + (h * 0.1)])
        return np.array(forecast)

def train_lstm(save_path: str = "ml_models/lstm_forecaster.pt",
               epochs: int = 50, batch_size: int = 64,
               learning_rate: float = 0.001) -> dict:
    """
    Trains the LSTM forecaster and saves model weights.

    Optimizer: Adam (Adaptive Moment Estimation)
      - Combines momentum and RMSProp for adaptive per-parameter learning rates.
      - Standard for sequence models; learning_rate=0.001 is default best.

    Loss: MSE (Mean Squared Error)
      - Best for regression/forecasting tasks.
      - Penalizes large prediction errors quadratically.
    """
    logger.info("=== Training LSTM Forecaster ===")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    npz_path = os.path.join(base_dir, "data", "lstm_training_data.npz")
    if not os.path.exists(npz_path):
        raise FileNotFoundError(f"LSTM training data not found at {npz_path}. Run generate_datasets.py first.")
    
    data = np.load(npz_path)
    X = data["X"]
    y = data["y"]
    logger.info(f"Loaded {len(X)} sequential samples from {npz_path}")

    # Normalize features (important for LSTM convergence)
    X_mean, X_std = X.mean(axis=(0, 1)), X.std(axis=(0, 1))
    y_mean, y_std = y.mean(axis=(0, 1)), y.std(axis=(0, 1))
    X_norm = (X - X_mean) / (X_std + 1e-8)
    y_norm = (y - y_mean) / (y_std + 1e-8)

    # Split
    split = int(len(X_norm) * 0.8)
    X_train, X_val = X_norm[:split], X_norm[split:]
    y_train, y_val = y_norm[:split], y_norm[split:]

    # Convert to tensors
    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train))
    val_ds   = TensorDataset(torch.tensor(X_val),   torch.tensor(y_val))
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size)

    # Initialize model
    model     = LSTMForecaster().to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    history = {"train_loss": [], "val_loss": []}

    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_dl:
            X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
            optimizer.zero_grad()
            pred = model(X_batch)
            loss = criterion(pred, y_batch)
            loss.backward()
            # Gradient clipping: prevents exploding gradients in LSTM
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item()

        # Validation phase
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_dl:
                X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
                pred     = model(X_batch)
                val_loss += criterion(pred, y_batch).item()

        avg_train = train_loss / len(train_dl)
        avg_val   = val_loss   / len(val_dl)
        scheduler.step(avg_val)

        history["train_loss"].append(round(avg_train, 6))
        history["val_loss"].append(round(avg_val, 6))

        if (epoch + 1) % 10 == 0:
            logger.info(f"  Epoch {epoch+1}/{epochs} | Train Loss: {avg_train:.4f} | Val Loss: {avg_val:.4f}")

    # Save model weights and normalization stats
    os.makedirs("ml_models", exist_ok=True)
    torch.save(model.state_dict(), save_path)
    joblib.dump({"X_mean": X_mean, "X_std": X_std, "y_mean": y_mean, "y_std": y_std},
                "ml_models/lstm_normalization.pkl")

    final_val_loss = history["val_loss"][-1]
    logger.info(f"=== LSTM Training Complete. Final Val Loss: {final_val_loss:.4f} ===")
    logger.info(f"Model saved to {save_path}")

    return {
        "model": "LSTM Forecaster",
        "architecture": "2-layer Stacked LSTM + FC Decoder",
        "input": "24-hour sequence [temp, load, voltage, current]",
        "output": "Next 24-hour [load, temperature] forecast",
        "optimizer": "Adam",
        "learning_rate": learning_rate,
        "loss_function": "MSE (Mean Squared Error)",
        "epochs_trained": epochs,
        "final_val_loss": final_val_loss,
        "history": history
    }


# ─── Run LSTM training pipeline ──────────────────────────────────────────────
def train_all_deep_learning_models() -> dict:
    """
    Entry point: Trains LSTM and saves results summary.
    """
    results = {}
    results["lstm"] = train_lstm()

    os.makedirs("ml_models", exist_ok=True)
    with open("ml_models/deep_learning_results.json", "w") as f:
        # Remove non-serializable history for the JSON file
        serializable = {k: {sk: sv for sk, sv in v.items() if sk != "history"}
                        for k, v in results.items()}
        json.dump(serializable, f, indent=2)

    logger.info("=== LSTM Deep Learning Model Trained and Saved ===")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    train_all_deep_learning_models()
