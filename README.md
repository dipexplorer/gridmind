# GridMind 🔌

**AI-Powered Transformer Health Monitoring & Predictive Maintenance Platform**

> Developed under **Assam Power Distribution Company Limited (APDCL)** — Internship Project, July–August 2026

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is GridMind?

APDCL manages approx 1.2 lakhs of distribution transformers across Assam. Traditional maintenance is reactive — transformers are serviced only after they fail, causing unplanned outages and emergency costs.

**GridMind** solves this with a 4-model AI fusion engine:

1. **Anomaly Detection** — Isolation Forest learns healthy transformer behaviour and flags deviations in real time
2. **Risk Classification** — XGBoost + Random Forest directly classify each transformer as SAFE / WARNING / CRITICAL
3. **Remaining Useful Life** — Cox Proportional Hazards Survival Analysis estimates how many days until probable failure
4. **Decision Fusion** — A weighted ensemble (Cox 50% + Classifiers 35% + IF 15%) produces a single Health Score (0–100)
5. **Explainability** — SHAP values reveal exactly _which sensor readings_ are driving the risk prediction
6. **Dashboard** — Real-time monitoring across all transformers with GIS map, 24-hour telemetry, and maintenance alerts

---

## 🐳 Quick Start with Docker (Recommended)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) 24.0+ and [Docker Compose](https://docs.docker.com/compose/) 2.20+

```bash
# 1. Clone the repository
git clone https://github.com/dipexplorer/gridmind.git
cd gridmind

# 2. Copy and configure environment (edit passwords if needed)
cp .env.example .env

# 3. Start all services (PostgreSQL + FastAPI backend + Next.js frontend)
docker compose up -d

# 4. First-time setup — run once to initialize DB, seed data, and train models
chmod +x docker-setup.sh
./docker-setup.sh
```

That's it! Open:

| Service | URL |
| --- | --- |
| **Dashboard** | http://localhost:3000 |
| **API Swagger** | http://localhost:8000/api/docs |
| **API ReDoc** | http://localhost:8000/api/redoc |

**Default login:**

```
Email:    admin@gridmind.com
Password: GridMind@2026
```

### Docker Commands Reference

```bash
docker compose up -d          # Start all services in background
docker compose down           # Stop all services
docker compose down -v        # Stop + delete database volume (full reset)
docker compose logs -f        # Watch live logs from all services
docker compose logs backend   # Watch backend logs only
docker compose ps             # Check container status

# Re-train models inside the running backend container
docker compose exec backend python scripts/train_production_models.py

# Run database migrations
docker compose exec backend alembic upgrade head

# Open a shell inside the backend container
docker compose exec backend bash
```

---

## ⚡ Manual Setup (Without Docker)

**Prerequisites:** Python 3.11, Node.js 20+, PostgreSQL 16

```bash
# 1. Clone
git clone https://github.com/dipexplorer/gridmind.git
cd gridmind

# 2. Backend setup
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set POSTGRES_* credentials and JWT_SECRET_KEY

# 4. Database migrations
alembic upgrade head

# 5. Generate training data + seed database
python scripts/generate_datasets.py          # creates data/ml_training_dataset.csv
python scripts/seed_db.py                    # populates transformer records

# 6. Train all ML models
python scripts/train_production_models.py    # trains IF, Cox PH, RF, XGBoost
python -c "from services.ml_benchmark import run_benchmark; run_benchmark()"

# 7. Start backend API
uvicorn main:app --reload --port 8000

# 8. Frontend setup (new terminal)
cd ../frontend
npm install
npm run dev                                  # http://localhost:3000
```

```

---

## 🏗️ Architecture

```
Browser (Next.js 14)
        │
        ▼
FastAPI 0.110  (port 8000)
├── REST API        → /api/v1/...
├── WebSocket       → /api/v1/ws/...
└── ML Analytics    → /api/v1/ml/...
        │
        ├── PostgreSQL 16 + PostGIS   ← Asset data, telemetry, events
        ├── SQLite (dev fallback)     ← gridmind.db for local development
        │
        └── ML Intelligence Engine
            ├── Isolation Forest       ← Anomaly score (0–100%)
            ├── XGBoost Classifier     ← SAFE / WARNING / CRITICAL
            ├── Random Forest          ← Cross-check classifier
            ├── Cox PH Survival        ← Remaining days to failure
            └── SHAP Explainer         ← Feature importance per prediction
```

**Health Score Fusion Formula:**

```
Health Score = 0.50 × Cox_health        (survival probability × 100)
             + 0.35 × min(XGB, RF)      (conservative — worst of the two)
             + 0.15 × IF_health         (100 − anomaly_score)

Status:  ≥ 75  →  HEALTHY 🟢
         ≥ 45  →  WARNING 🟡
         < 45  →  CRITICAL 🔴
```

---

## 📁 Project Structure

```
gridmind/
├── backend/
│   ├── Dockerfile                 # Multi-stage Docker build for FastAPI
│   ├── .dockerignore
│   ├── api/
│   │   └── endpoints/
│   │       ├── asset.py           # GET /transformers — list and filter transformers
│   │       ├── detail.py          # GET /transformers/{id} — telemetry, SHAP, health history
│   │       ├── intelligence.py    # GET /intelligence — batch health scores
│   │       ├── ml_analytics.py    # GET /ml/benchmark, /ml/deep-learning, POST /ml/run-*
│   │       ├── event.py           # Maintenance events and alerts
│   │       ├── notification.py    # In-app notifications
│   │       ├── timeseries.py      # 24-hour telemetry readings
│   │       ├── user.py            # Auth: login, token refresh
│   │       ├── operations.py      # Maintenance tickets
│   │       └── websockets.py      # Real-time WebSocket updates
│   │
│   ├── services/
│   │   ├── ai_service.py          # Core inference: IF + XGB + RF + Cox + SHAP fusion
│   │   ├── ml_benchmark.py        # Academic benchmark: RF vs XGBoost metrics + confusion matrix
│   │   ├── deep_learning.py       # PyTorch LSTM 24h load & temperature forecasting
│   │   ├── inference_service.py   # Batch inference orchestrator
│   │   └── data_cache.py          # In-memory telemetry and health trend cache
│   │
│   ├── scripts/
│   │   ├── generate_datasets.py   # Physics-based synthetic SCADA dataset (10,000 rows)
│   │   ├── train_production_models.py  # Trains IF (SAFE-only), Cox PH, benchmark RF+XGB
│   │   ├── predict_daily_batch.py # Daily scheduled batch prediction runner
│   │   ├── seed_db.py             # Populates DB with transformer records
│   │   └── sync_db_scores.py      # Syncs ML scores back to DB
│   │
│   ├── models/                    # SQLAlchemy ORM models (Transformer, TelemetryReading, etc.)
│   ├── schemas/                   # Pydantic request/response schemas
│   ├── core/
│   │   ├── config.py              # All settings via Pydantic BaseSettings / .env
│   │   └── database.py            # SQLAlchemy engine + session factory
│   ├── alembic/                   # Database migration scripts
│   ├── ml_models/                 # Trained model files (joblib + PyTorch)
│   │   ├── isolation_forest.pkl       # IF trained on SAFE-only data (contamination=auto)
│   │   ├── survival_model.pkl         # Cox PH model for RUL estimation
│   │   ├── benchmark_random_forest.pkl
│   │   ├── benchmark_xgboost.pkl
│   │   ├── benchmark_results.json     # Confusion matrices, class reports, ROC-AUC
│   │   ├── lstm_forecaster.pt         # PyTorch LSTM weights
│   │   └── deep_learning_results.json
│   └── data/
│       └── ml_training_dataset.csv    # 10,000 labeled SCADA telemetry samples
│
├── frontend/
│   ├── Dockerfile                 # Multi-stage Docker build for Next.js
│   ├── .dockerignore
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # Root → redirects to /dashboard
│       │   ├── layout.tsx         # Global layout + navigation sidebar
│       │   ├── login/             # JWT login page
│       │   ├── dashboard/         # Main fleet overview + health status cards
│       │   ├── map/               # GIS map with transformer markers
│       │   └── ml-analytics/      # ML benchmark dashboard (Confusion Matrix, ROC, Classification Report)
│       ├── components/            # Recharts charts, UI cards, sidebar
│       └── lib/
│           └── api.ts             # Axios API client (JWT auth, base URL from env)
│
├── docker-compose.yml             # Docker Compose — starts db + backend + frontend
├── docker-setup.sh                # First-time init: migrate DB, seed data, train models
├── data-pipeline/                 # Standalone ETL pipeline (separate venv)
├── docs/                          # Architecture, engineering, product documentation
├── .env.example                   # Environment variable template
├── render.yaml                    # Render.com deployment config
└── GridMind_Project_Report.md     # Full internship project report
```

---

## 🧠 ML Models — What Each One Does

| Model                | Type                           | Input                   | Output                                    | Role in Dashboard                 |
| -------------------- | ------------------------------ | ----------------------- | ----------------------------------------- | --------------------------------- |
| **Isolation Forest** | Unsupervised anomaly detection | 13 SCADA features       | Anomaly Score 0–100%                      | 15% weight in Health Score        |
| **XGBoost**          | Supervised classifier          | 13 SCADA features       | SAFE / WARNING / CRITICAL + probabilities | 35% weight (with RF)              |
| **Random Forest**    | Supervised classifier          | 13 SCADA features       | SAFE / WARNING / CRITICAL + probabilities | 35% weight (with XGB)             |
| **Cox PH Survival**  | Survival analysis              | 13 SCADA features       | Days to failure + survival probability    | 50% weight in Health Score        |
| **LSTM (PyTorch)**   | Time-series forecasting        | 24h telemetry sequences | Next 24h load & temperature forecast      | Academic demo (ML Analytics page) |

**The 13 Input Features:**

| Feature               | Source         | Description                                    |
| --------------------- | -------------- | ---------------------------------------------- |
| `temperature_c`       | Sensor         | Oil temperature (°C)                           |
| `load_percentage`     | Sensor         | Load as % of rated capacity                    |
| `voltage_lv`          | Sensor         | LV side voltage (V)                            |
| `current_a`           | Sensor         | Primary current (A)                            |
| `ambient_temperature` | Open-Meteo API | Live outdoor temperature                       |
| `age_years`           | Database       | Transformer age in years                       |
| `rated_kva`           | Database       | Rated capacity (kVA)                           |
| `power_factor`        | Computed       | Load-derived power factor                      |
| `load_ratio`          | Computed       | `load_pct / 100`                               |
| `current_ratio`       | Computed       | `current / rated_current`                      |
| `voltage_deviation`   | Computed       | `(415 − V_lv) / 415`                           |
| `temperature_rise`    | Computed       | `temp_c − ambient_temp`                        |
| `stress_index`        | Computed       | `current_ratio × temp_rise × (1 + 0.05 × age)` |

---

## 📊 Model Performance (Benchmark Results)

**Supervised Classifiers** (10,000 samples, 80/20 split, 3-class: SAFE/WARNING/CRITICAL):

| Model                         | Accuracy | F1-Score | ROC-AUC |
| ----------------------------- | -------- | -------- | ------- |
| **Random Forest** (200 trees) | 99.65%   | 0.9965   | 0.9999  |
| **XGBoost** (200 rounds)      | 99.50%   | 0.9950   | 1.0000  |

**Isolation Forest** (SAFE-only training, evaluated on unseen data):

| Metric                 | Value    | Notes                          |
| ---------------------- | -------- | ------------------------------ |
| Accuracy               | 87.7%    | On 2,971 unseen samples        |
| Anomaly Recall         | **100%** | All WARNING + CRITICAL flagged |
| SAFE False-Positive    | ~20.7%   | Improvement target             |
| Training contamination | `auto`   | No label leakage               |

> High supervised accuracy is expected on synthetic physics-based data. Real-world accuracy would require actual failure-labeled APDCL data.

---

## 🖥️ Frontend Pages

| Page                   | URL               | Description                                                           |
| ---------------------- | ----------------- | --------------------------------------------------------------------- |
| **Login**              | `/login`          | JWT authentication                                                    |
| **Dashboard**          | `/dashboard`      | Fleet overview: health cards, anomaly counts, high-risk list          |
| **Transformer Detail** | `/dashboard/[id]` | 24h telemetry, Health Score, SHAP risk drivers, RUL, model breakdown  |
| **GIS Map**            | `/map`            | Transformer locations colour-coded by health status                   |
| **ML Analytics**       | `/ml-analytics`   | Confusion matrices, classification reports, ROC curves, LSTM forecast |

---

## 🔌 Key API Endpoints

| Method | Endpoint                            | Description                                                  |
| ------ | ----------------------------------- | ------------------------------------------------------------ |
| `POST` | `/api/v1/auth/login`                | JWT login                                                    |
| `GET`  | `/api/v1/transformers`              | List all transformers with current health                    |
| `GET`  | `/api/v1/transformers/{id}`         | Full detail: telemetry, SHAP, health history                 |
| `GET`  | `/api/v1/transformers/{id}/predict` | Run live ML inference                                        |
| `GET`  | `/api/v1/intelligence`              | Batch health scores for all transformers                     |
| `GET`  | `/api/v1/ml/benchmark`              | Benchmark results JSON (confusion matrix, class report, ROC) |
| `POST` | `/api/v1/ml/run-benchmark`          | Trigger benchmark re-training (background)                   |
| `GET`  | `/api/v1/ml/deep-learning`          | LSTM training results                                        |
| `WS`   | `/api/v1/ws/telemetry`              | Real-time telemetry WebSocket                                |

Full Swagger UI: `http://localhost:8000/api/docs`

---

## 🧑‍💻 Tech Stack

| Layer                   | Technology                         | Version              |
| ----------------------- | ---------------------------------- | -------------------- |
| **Backend**             | FastAPI                            | 0.110.0              |
| **Language**            | Python                             | 3.12                 |
| **ML — Anomaly**        | scikit-learn IsolationForest       | 1.4.2                |
| **ML — Classification** | XGBoost, scikit-learn RandomForest | 2.0.3 / 1.4.2        |
| **ML — Survival**       | lifelines CoxPHFitter              | 0.27.8               |
| **ML — Explainability** | SHAP TreeExplainer                 | 0.45.0               |
| **ML — Deep Learning**  | PyTorch LSTM (stacked 2-layer)     | via deep_learning.py |
| **Database**            | PostgreSQL 16 + PostGIS            | —                    |
| **ORM**                 | SQLAlchemy                         | 2.0.29               |
| **Migrations**          | Alembic                            | 1.13.1               |
| **Frontend**            | Next.js 14 (TypeScript)            | 14.x                 |
| **Charts**              | Recharts                           | latest               |
| **HTTP Client**         | Axios                              | via apiClient        |
| **Auth**                | JWT (python-jose)                  | 3.3.0                |
| **Async Tasks**         | Celery + Redis                     | 5.3.6                |
| **Deployment**          | Render.com (render.yaml)           | —                    |

---

## 📂 Data Generation

The training dataset is **physics-based synthetic SCADA data** — not real APDCL sensor data (which was not available during the internship).

```bash
python backend/scripts/generate_datasets.py
# → backend/data/ml_training_dataset.csv
# → 10,000 rows: 8,787 SAFE | 344 WARNING | 869 CRITICAL
```

Each row simulates one 24-hour snapshot of a transformer with:

- Physics-derived sensor readings (temperature, load, voltage, current)
- Engineered features (stress index, load ratio, temperature rise)
- Ground-truth risk label (0=SAFE, 1=WARNING, 2=CRITICAL)

---

## 🏃 Running the ML Benchmark

```bash
# From backend/ with venv activated:

# Option 1: Direct Python (fastest)
python -c "from services.ml_benchmark import run_benchmark; run_benchmark()"

# Option 2: Via API (when server is running)
curl -X POST http://localhost:8000/api/v1/ml/run-benchmark

# Results saved to: backend/ml_models/benchmark_results.json
# Includes: confusion_matrix, class_report, roc_data per model
```

---

## 🔁 Daily Batch Prediction

On every server startup, a background thread auto-runs the batch prediction 30 seconds after boot:

```python
# backend/main.py — startup_event()
threading.Thread(target=schedule_daily_batch, daemon=True).start()
```

This calls `scripts/predict_daily_batch.py` which:

1. Loads all transformers from DB
2. Fetches their latest 24h telemetry readings
3. Runs `ai_service.predict_daily_health()` on each
4. Writes updated health scores, risk category, and RUL back to DB

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gridmind
POSTGRES_USER=gridmind_user
POSTGRES_PASSWORD=your_secure_password

# JWT (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your_256_bit_secret

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# ML
ANOMALY_CONTAMINATION=0.05   # Legacy — IF now uses contamination=auto
```

---

## 📄 Project Report

The complete APDCL internship project report is available at:
**[`GridMind_Project_Report.md`](GridMind_Project_Report.md)**

Covers: Problem Statement, Architecture, ML Methodology, Results, Limitations, Future Work.

---

## 📜 License

MIT License — see [LICENSE](LICENSE).

---

_Built during APDCL Internship | July–August 2026 | Guwahati, Assam, India_
