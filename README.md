# GridMind 🔌

**AI-Powered Transformer Health Monitoring & Predictive Maintenance Platform**

> Developed under **Assam Power Distribution Company Limited (APDCL)** — Internship Project, July–August 2026

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is GridMind?

APDCL manages approx 1.2 lakh distribution transformers across Assam. Traditional maintenance is reactive — transformers are serviced only after they fail, causing unplanned outages and emergency costs.

**GridMind** solves this with a 4-model AI fusion engine:

1. **Anomaly Detection** — Isolation Forest learns healthy transformer behaviour and flags deviations in real time
2. **Risk Classification** — XGBoost + Random Forest classify each transformer as SAFE / WARNING / CRITICAL
3. **Remaining Useful Life** — Cox Proportional Hazards Survival Analysis estimates days until probable failure
4. **Decision Fusion** — Weighted ensemble (Cox 50% + Classifiers 35% + IF 15%) produces a single Health Score (0–100)
5. **Explainability** — SHAP values reveal which sensor readings are driving each risk prediction
6. **Dashboard** — Real-time monitoring with GIS map, 24-hour telemetry, and maintenance alerts

---

## 🐳 Quick Start — Docker (Recommended)

**Prerequisites:** [Docker 24.0+](https://docs.docker.com/get-docker/) and [Docker Compose 2.20+](https://docs.docker.com/compose/)

```bash
# 1. Clone
git clone https://github.com/dipexplorer/gridmind.git
cd gridmind

# 2. Configure environment
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. First-time setup (run once: DB migrate + seed data + train models)
chmod +x docker-setup.sh
./docker-setup.sh
```

Once done, open:

| Service | URL |
|---|---|
| **Dashboard** | http://localhost:3000 |
| **API Docs (Swagger)** | http://localhost:8000/api/docs |
| **API Docs (ReDoc)** | http://localhost:8000/api/redoc |

**Default login:**

```
Email:    admin@gridmind.com
Password: GridMind@2026
```

### Docker Commands Reference

```bash
docker compose up -d                  # Start all services
docker compose down                   # Stop all services
docker compose down -v                # Stop + wipe database (full reset)
docker compose logs -f                # Watch live logs (all services)
docker compose logs -f backend        # Backend logs only
docker compose ps                     # Check running status

# Run commands inside the backend container
docker compose exec backend alembic upgrade head
docker compose exec backend python scripts/train_production_models.py
docker compose exec backend bash      # Open a shell
```

---

## ⚡ Manual Setup (Without Docker)

**Prerequisites:** Python 3.11, Node.js 20+, PostgreSQL 16

```bash
# 1. Clone
git clone https://github.com/dipexplorer/gridmind.git
cd gridmind

# 2. Backend — create virtualenv and install dependencies
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env             # Edit POSTGRES_* and JWT_SECRET_KEY

# 4. Database migrations
alembic upgrade head

# 5. Generate training data and seed database
python scripts/generate_datasets.py   # → data/ml_training_dataset.csv (10,000 rows)
python scripts/seed_db.py             # → transformer records in DB

# 6. Train ML models
python scripts/train_production_models.py
python -c "from services.ml_benchmark import run_benchmark; run_benchmark()"

# 7. Start backend
uvicorn main:app --reload --port 8000

# 8. Frontend (new terminal)
cd ../frontend
npm install
npm run dev                           # → http://localhost:3000
```

---

## 🏗️ Architecture

```
Browser (Next.js 14)
        │
        ▼
FastAPI 0.110  (port 8000)
├── REST API      →  /api/v1/...
├── WebSocket     →  /api/v1/ws/...
└── ML Analytics  →  /api/v1/ml/...
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
Health Score = 0.50 × Cox_health       (1-year survival probability × 100)
             + 0.35 × min(XGB, RF)     (conservative: worst of the two)
             + 0.15 × IF_health        (100 − anomaly_score)

Status:  ≥ 75  →  HEALTHY   🟢
         ≥ 45  →  WARNING   🟡
          < 45  →  CRITICAL  🔴
```

---

## 📁 Project Structure

```
gridmind/
├── backend/
│   ├── Dockerfile                      # Multi-stage Python 3.11 build
│   ├── .dockerignore
│   ├── main.py                         # FastAPI app entry point
│   ├── requirements.txt
│   ├── api/endpoints/
│   │   ├── asset.py                    # GET /transformers
│   │   ├── detail.py                   # GET /transformers/{id}
│   │   ├── intelligence.py             # GET /intelligence
│   │   ├── ml_analytics.py             # GET /ml/benchmark, POST /ml/run-*
│   │   ├── event.py                    # Maintenance events
│   │   ├── notification.py             # In-app alerts
│   │   ├── timeseries.py               # 24h telemetry
│   │   ├── user.py                     # Auth: login, refresh
│   │   ├── operations.py               # Maintenance tickets
│   │   └── websockets.py               # Real-time WebSocket
│   ├── services/
│   │   ├── ai_service.py               # Core: IF + XGB + RF + Cox + SHAP fusion
│   │   ├── ml_benchmark.py             # RF vs XGBoost benchmark + confusion matrix
│   │   ├── deep_learning.py            # PyTorch LSTM 24h forecasting
│   │   ├── inference_service.py        # Batch inference orchestrator
│   │   └── data_cache.py               # In-memory telemetry cache
│   ├── scripts/
│   │   ├── generate_datasets.py        # Synthetic SCADA dataset (10,000 rows)
│   │   ├── train_production_models.py  # Train IF, Cox PH, XGBoost, RF
│   │   ├── predict_daily_batch.py      # Daily batch prediction runner
│   │   ├── seed_db.py                  # Seed transformer records
│   │   └── sync_db_scores.py           # Sync ML scores to DB
│   ├── models/                         # SQLAlchemy ORM models
│   ├── schemas/                        # Pydantic schemas
│   ├── core/
│   │   ├── config.py                   # All settings via Pydantic BaseSettings
│   │   └── database.py                 # SQLAlchemy engine + session
│   ├── alembic/                        # DB migrations
│   ├── ml_models/
│   │   ├── isolation_forest.pkl        # IF (SAFE-only, contamination=auto)
│   │   ├── survival_model.pkl          # Cox PH for RUL
│   │   ├── benchmark_random_forest.pkl
│   │   ├── benchmark_xgboost.pkl
│   │   ├── benchmark_results.json      # Confusion matrices, class reports, ROC
│   │   ├── lstm_forecaster.pt          # PyTorch LSTM weights
│   │   └── deep_learning_results.json
│   └── data/
│       └── ml_training_dataset.csv     # 10,000 labeled SCADA samples
│
├── frontend/
│   ├── Dockerfile                      # Multi-stage Node 20 alpine build
│   ├── .dockerignore
│   ├── next.config.js                  # output: standalone (Docker support)
│   └── src/
│       ├── app/
│       │   ├── login/                  # JWT login page
│       │   ├── dashboard/              # Fleet overview + health status cards
│       │   ├── map/                    # GIS map (transformer locations)
│       │   └── ml-analytics/           # Confusion matrix, ROC, classification report
│       ├── components/                 # Charts, UI cards, sidebar
│       └── lib/api.ts                  # Axios API client
│
├── docker-compose.yml                  # Starts PostgreSQL + backend + frontend
├── docker-setup.sh                     # First-time: migrate + seed + train
├── .env.example                        # Environment variable template
├── render.yaml                         # Render.com deployment config
└── GridMind_Project_Report.md          # Full APDCL internship project report
```

---

## 🧠 ML Models

| Model | Type | Output | Weight in Health Score |
|---|---|---|---|
| **Isolation Forest** | Unsupervised anomaly detection | Anomaly Score 0–100% | 15% |
| **XGBoost** | Supervised classifier | SAFE / WARNING / CRITICAL | 35% (with RF) |
| **Random Forest** | Supervised classifier | SAFE / WARNING / CRITICAL | 35% (with XGB) |
| **Cox PH Survival** | Survival analysis | Days to failure + 1-year survival probability | 50% |
| **LSTM (PyTorch)** | Time-series forecasting | Next 24h load & temperature forecast | Academic demo |

All models share the same **13 input features**:

| Feature | Source | Description |
|---|---|---|
| `temperature_c` | Sensor | Oil temperature (°C) |
| `load_percentage` | Sensor | Load as % of rated capacity |
| `voltage_lv` | Sensor | LV side voltage (V) |
| `current_a` | Sensor | Primary current (A) |
| `ambient_temperature` | Open-Meteo API | Live outdoor temperature |
| `age_years` | Database | Transformer age in years |
| `rated_kva` | Database | Rated capacity (kVA) |
| `power_factor` | Computed | Load-derived power factor |
| `load_ratio` | Computed | `load_pct / 100` |
| `current_ratio` | Computed | `current / rated_current` |
| `voltage_deviation` | Computed | `(415 − V_lv) / 415` |
| `temperature_rise` | Computed | `temp_c − ambient_temp` |
| `stress_index` | Computed | `current_ratio × temp_rise × (1 + 0.05 × age)` |

---

## 📊 Model Performance

**Supervised Classifiers** — 10,000 samples, 80/20 split, 3-class (SAFE / WARNING / CRITICAL):

| Model | Accuracy | F1-Score | ROC-AUC |
|---|---|---|---|
| **Random Forest** (200 trees) | 99.65% | 0.9965 | 0.9999 |
| **XGBoost** (200 rounds) | 99.50% | 0.9950 | 1.0000 |

**Isolation Forest** — SAFE-only training, evaluated on unseen data:

| Metric | Value | Notes |
|---|---|---|
| Accuracy | 87.7% | On 2,971 unseen samples |
| Anomaly Recall | **100%** | All WARNING + CRITICAL flagged |
| SAFE False-Positive Rate | ~20.7% | Improvement target |
| Training contamination | `auto` | No label leakage |

> High supervised accuracy is expected on synthetic data. Real-world results would require actual failure-labeled APDCL records.

---

## 🖥️ Frontend Pages

| Page | URL | Description |
|---|---|---|
| **Login** | `/login` | JWT authentication |
| **Dashboard** | `/dashboard` | Fleet overview: health cards, anomaly counts, high-risk list |
| **Transformer Detail** | `/dashboard/[id]` | 24h telemetry, Health Score, SHAP drivers, RUL, model breakdown |
| **GIS Map** | `/map` | Transformer locations colour-coded by health status |
| **ML Analytics** | `/ml-analytics` | Confusion matrices, classification reports, ROC curves, LSTM forecast |

---

## 🔌 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | JWT login |
| `GET` | `/api/v1/transformers` | List all transformers with current health |
| `GET` | `/api/v1/transformers/{id}` | Full detail: telemetry, SHAP, health history |
| `GET` | `/api/v1/transformers/{id}/predict` | Run live ML inference |
| `GET` | `/api/v1/intelligence` | Batch health scores for all transformers |
| `GET` | `/api/v1/ml/benchmark` | Benchmark results (confusion matrix, class report, ROC) |
| `POST` | `/api/v1/ml/run-benchmark` | Trigger benchmark re-training (background) |
| `GET` | `/api/v1/ml/deep-learning` | LSTM training results |
| `WS` | `/api/v1/ws/telemetry` | Real-time telemetry WebSocket |

Full interactive docs: `http://localhost:8000/api/docs`

---

## 🧑‍💻 Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Backend** | FastAPI | 0.110.0 |
| **Language** | Python | 3.11 |
| **ML — Anomaly** | scikit-learn IsolationForest | 1.4.2 |
| **ML — Classification** | XGBoost + scikit-learn RandomForest | 2.0.3 / 1.4.2 |
| **ML — Survival** | lifelines CoxPHFitter | 0.27.8 |
| **ML — Explainability** | SHAP TreeExplainer | 0.45.0 |
| **ML — Deep Learning** | PyTorch LSTM (2-layer stacked) | — |
| **Database** | PostgreSQL 16 + PostGIS | — |
| **ORM** | SQLAlchemy | 2.0.29 |
| **Migrations** | Alembic | 1.13.1 |
| **Frontend** | Next.js 14 (TypeScript) | 14.x |
| **Charts** | Recharts | 2.x |
| **Auth** | JWT (python-jose) | 3.3.0 |
| **Async Tasks** | Celery + Redis | 5.3.6 |
| **Deployment** | Docker Compose / Render.com | — |

---

## 📂 Data Generation

The training dataset is **physics-based synthetic SCADA data** — real APDCL sensor data was not available during the internship.

```bash
python backend/scripts/generate_datasets.py
# Output: backend/data/ml_training_dataset.csv
# 10,000 rows — 8,787 SAFE | 344 WARNING | 869 CRITICAL
```

Each row simulates one 24-hour snapshot with physics-derived sensor readings, engineered features, and a ground-truth risk label.

---

## 🔁 Daily Batch Prediction

On every server startup, a background thread auto-runs batch prediction 30 seconds after boot:

```python
# backend/main.py
threading.Thread(target=schedule_daily_batch, daemon=True).start()
```

This calls `predict_daily_batch.py` which loads all transformers, fetches their latest 24h telemetry, runs `ai_service.predict_daily_health()`, and writes updated health scores and RUL back to the database.

---

## 🔐 Environment Variables

Copy `.env.example` to `.env` and set these key values:

```env
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gridmind
POSTGRES_USER=gridmind_user
POSTGRES_PASSWORD=your_secure_password

# JWT — generate with: openssl rand -hex 32
JWT_SECRET_KEY=your_256_bit_secret

# Frontend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 📄 Project Report

The complete APDCL internship project report is at **[GridMind_Project_Report.md](GridMind_Project_Report.md)**.

Covers: Problem Statement, System Architecture, ML Methodology, Benchmark Results, Limitations, and Future Work.

---

## 📜 License

MIT License — see [LICENSE](LICENSE).

---

_Built during APDCL Internship | July–August 2026 | Guwahati, Assam, India_
