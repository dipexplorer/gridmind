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
# MODEL 2: 1D-CNN — Fault Waveform Classification
# ═══════════════════════════════════════════════════════════════════════════════

class CNN1DFaultClassifier(nn.Module):
    """
    PyTorch 1D-CNN model for fault pattern classification on time-series data.

    Architecture:
    ─────────────────────────────────────────────────────
    Input  [batch, input_size=4, seq_len=24]  ← Note: channels first for Conv1d
        → Conv1d(4 → 32, kernel=3, padding=1)
        → BatchNorm + ReLU + MaxPool
        → Conv1d(32 → 64, kernel=3, padding=1)
        → BatchNorm + ReLU + MaxPool
        → Conv1d(64 → 128, kernel=3, padding=1)
        → BatchNorm + ReLU + AdaptiveAvgPool (reduces to length 1)
        → Flatten → [batch, 128]
        → Dropout → FC(128 → 64) → ReLU → FC(64 → num_classes=4)
    Output [batch, 4]  ← Logits for 4 fault classes (use Softmax for proba)
    ─────────────────────────────────────────────────────

    Why kernel_size=3?
      - A kernel of 3 looks at 3 consecutive time steps.
      - Small kernels capture local temporal patterns (e.g., sudden spikes).
      - Multiple stacked Conv layers capture increasingly complex patterns.

    Why BatchNorm after each Conv?
      - Normalizes the activations of each layer to prevent internal covariate shift.
      - Allows higher learning rates and makes training much more stable.
    """

    def __init__(self, input_channels: int = 4, seq_len: int = 24, num_classes: int = 4):
        super(CNN1DFaultClassifier, self).__init__()

        self.num_classes = num_classes

        # Convolutional feature extractor
        self.conv_block = nn.Sequential(
            # Block 1: Local pattern extraction
            nn.Conv1d(input_channels, 32, kernel_size=3, padding=1),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),    # Halves temporal resolution

            # Block 2: Higher-level pattern
            nn.Conv1d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),

            # Block 3: Abstract temporal features
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),        # Squeeze temporal dim to 1
        )

        # Classification head
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x: [batch, channels, seq_len] e.g. [32, 4, 24]
        Returns: logits [batch, num_classes]
        """
        features = self.conv_block(x)  # [batch, 128, 1]
        return self.classifier(features)


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


def generate_cnn_fault_sequences(n_sequences: int = 3000, seq_len: int = 24,
                                  random_state: int = 42) -> tuple:
    """
    Generates labeled fault classification sequences for 1D-CNN training.

    Classes:
      0 = NORMAL       — Standard operation
      1 = THERMAL_SURGE — Sudden temperature spike mid-sequence
      2 = VOLTAGE_DIP  — Voltage drop event
      3 = OVERLOAD     — Load exceeds 110% for sustained period
    """
    np.random.seed(random_state)

    class_names = ["NORMAL", "THERMAL_SURGE", "VOLTAGE_DIP", "OVERLOAD"]
    X_seqs, y_labels = [], []

    for i in range(n_sequences):
        fault_class = i % 4  # Balanced classes: 25% each

        # Base telemetry
        temp    = np.random.uniform(40, 70, seq_len)
        load    = np.random.uniform(30, 75, seq_len)
        voltage = np.random.uniform(400, 420, seq_len)
        current = np.random.uniform(50, 150, seq_len)

        # Inject fault signatures
        fault_start = np.random.randint(8, 16)  # Fault happens mid-sequence

        if fault_class == 1:  # THERMAL_SURGE
            temp[fault_start:] += np.random.uniform(25, 45)
        elif fault_class == 2:  # VOLTAGE_DIP
            voltage[fault_start:] -= np.random.uniform(30, 60)
            current[fault_start:] += np.random.uniform(50, 120)
        elif fault_class == 3:  # OVERLOAD
            load[fault_start:] = np.random.uniform(112, 140)
            current[fault_start:] += np.random.uniform(80, 180)

        # Add noise to all classes
        temp    += np.random.normal(0, 1.5, seq_len)
        load    += np.random.normal(0, 2.0, seq_len)
        voltage += np.random.normal(0, 1.5, seq_len)
        current += np.random.normal(0, 5.0, seq_len)

        # Shape: [channels=4, seq_len=24] for Conv1d
        seq = np.row_stack([temp, load, voltage, current]).astype(np.float32)

        X_seqs.append(seq)
        y_labels.append(fault_class)

    return np.array(X_seqs), np.array(y_labels), class_names


# ═══════════════════════════════════════════════════════════════════════════════
# TRAINING FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

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

    X, y = generate_lstm_sequences(n_samples := 2000)

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


def train_cnn1d(save_path: str = "ml_models/cnn1d_fault_classifier.pt",
                epochs: int = 40, batch_size: int = 64,
                learning_rate: float = 0.001) -> dict:
    """
    Trains the 1D-CNN fault classifier.

    Optimizer: Adam
    Loss: CrossEntropyLoss (standard for multi-class classification)
    """
    logger.info("=== Training 1D-CNN Fault Classifier ===")

    X, y, class_names = generate_cnn_fault_sequences(n_sequences=3000)

    split   = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    train_ds = TensorDataset(torch.tensor(X_train), torch.tensor(y_train, dtype=torch.long))
    val_ds   = TensorDataset(torch.tensor(X_val),   torch.tensor(y_val,   dtype=torch.long))
    train_dl = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_dl   = DataLoader(val_ds,   batch_size=batch_size)

    model     = CNN1DFaultClassifier(num_classes=len(class_names)).to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()

    best_val_acc = 0.0
    history      = {"train_loss": [], "val_accuracy": []}

    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_dl:
            X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
            optimizer.zero_grad()
            logits = model(X_batch)
            loss   = criterion(logits, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # Validation
        model.eval()
        correct, total = 0, 0
        with torch.no_grad():
            for X_batch, y_batch in val_dl:
                X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
                logits  = model(X_batch)
                preds   = logits.argmax(dim=1)
                correct += (preds == y_batch).sum().item()
                total   += len(y_batch)

        val_acc = correct / total
        avg_loss = train_loss / len(train_dl)
        history["train_loss"].append(round(avg_loss, 6))
        history["val_accuracy"].append(round(val_acc, 4))

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), save_path)  # Save best model

        if (epoch + 1) % 10 == 0:
            logger.info(f"  Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f} | Val Acc: {val_acc:.4f}")

    logger.info(f"=== 1D-CNN Training Complete. Best Val Accuracy: {best_val_acc:.4f} ===")
    logger.info(f"Model saved to {save_path}")

    return {
        "model": "1D-CNN Fault Classifier",
        "architecture": "3x Conv1d blocks + FC Classifier",
        "input": "24-hour waveform [4 channels x 24 time steps]",
        "output": "Fault Class: NORMAL, THERMAL_SURGE, VOLTAGE_DIP, OVERLOAD",
        "classes": class_names,
        "optimizer": "Adam",
        "learning_rate": learning_rate,
        "loss_function": "CrossEntropyLoss",
        "epochs_trained": epochs,
        "best_val_accuracy": round(best_val_acc, 4),
        "history": history
    }


# ─── Run both training pipelines ──────────────────────────────────────────────
def train_all_deep_learning_models() -> dict:
    """
    Entry point: Trains both LSTM and 1D-CNN and saves results summary.
    """
    results = {}
    results["lstm"] = train_lstm()
    results["cnn1d"] = train_cnn1d()

    os.makedirs("ml_models", exist_ok=True)
    with open("ml_models/deep_learning_results.json", "w") as f:
        # Remove non-serializable history for the JSON file
        serializable = {k: {sk: sv for sk, sv in v.items() if sk != "history"}
                        for k, v in results.items()}
        json.dump(serializable, f, indent=2)

    logger.info("=== All Deep Learning Models Trained and Saved ===")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    train_all_deep_learning_models()
