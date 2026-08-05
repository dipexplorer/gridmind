# GridMind — AI-Powered Transformer Health Monitoring System
## Summer Internship Project Report

**Organization:** Assam Power Distribution Company Limited (APDCL)  
**Project:** GridMind — Predictive Maintenance Intelligence Platform  
**Technology Stack:** Python · FastAPI · PostgreSQL/PostGIS · Next.js · Scikit-Learn · XGBoost · Lifelines · PyTorch  
**Period:** Summer 2026

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)  
2. [Problem Statement & Motivation](#2-problem-statement--motivation)  
3. [System Architecture](#3-system-architecture)  
4. [Technology Stack](#4-technology-stack)  
5. [Database Design](#5-database-design)  
6. [AI & Machine Learning Pipeline](#6-ai--machine-learning-pipeline)  
7. [Backend API Implementation](#7-backend-api-implementation)  
8. [Frontend Implementation](#8-frontend-implementation)  
9. [Data Pipeline & Synthetic Dataset Generation](#9-data-pipeline--synthetic-dataset-generation)  
10. [Model Benchmarking & Evaluation](#10-model-benchmarking--evaluation)  
11. [Deep Learning — LSTM Forecasting](#11-deep-learning--lstm-forecasting)  
12. [Deployment Architecture](#12-deployment-architecture)  
13. [Known Limitations & Honest Assessment](#13-known-limitations--honest-assessment)  
14. [Learnings & Outcomes](#14-learnings--outcomes)  
15. [Conclusion](#15-conclusion)

---

## 1. Executive Summary

GridMind is a full-stack web platform I built during my internship at APDCL to demonstrate how AI and machine learning can be applied to transformer predictive maintenance. The system ingests synthetic telemetry data (modelled on real APDCL transformer parameters), runs a multi-model ML inference pipeline, and surfaces results to operations engineers through an interactive dashboard.

The core idea is simple: instead of waiting for a transformer to fail and reacting, can we predict *which transformers are at risk* and *how much time they have left* — and show that to field engineers in a way they can actually act on?

The system does four things:
- **Monitors** a fleet of transformers using 24-hour rolling telemetry windows
- **Scores** each transformer using four ML models fused into a single health score
- **Explains** the AI's decision using SHAP feature importance values
- **Alerts** engineers through a maintenance ticket system when a transformer needs attention

> **Data honesty note:** All telemetry in this project is synthetically generated using physics-based formulas derived from real APDCL transformer parameters (voltage, KVA ratings, temperature limits). No real SCADA sensor data from APDCL was available for this prototype. The models are trained on this synthetic dataset.

---

## 2. Problem Statement & Motivation

APDCL operates thousands of distribution transformers across Assam. When a transformer fails unexpectedly, it causes:
- Unplanned power outages affecting entire localities
- Emergency maintenance that costs more and takes longer than scheduled maintenance
- Difficulty prioritizing which transformers to inspect given limited field crew capacity

Traditional maintenance is either **reactive** (repair after failure) or **time-based** (inspect on a fixed schedule regardless of actual condition). Neither is efficient.

The objective of this project was to prototype a system that would:
1. Continuously evaluate transformer health using sensor data
2. Flag transformers that are deteriorating before they fail
3. Provide AI-generated explanations (not just a number) so engineers understand *why* a transformer is flagged
4. Estimate how many days of remaining useful life a transformer has

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     USER (Browser)                      │
│         Next.js Frontend — Vercel / localhost:3000      │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS / REST API
            ┌──────────────┼──────────────────┐
            │              │                  │
            ▼              ▼                  ▼
    POST /api/v1    GET /api/v1       Supabase JS SDK
    transformers    transformers      (direct DB read
    risk-score      risk-score         via anon key)
            │
┌───────────▼─────────────────────────────────────────────┐
│              FastAPI Backend — Render.com / localhost    │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  API Routers │  │ InferService │  │  AI Service   │ │
│  │  (FastAPI)   │→ │  (fusion)    │→ │ (4-model ML)  │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
│                                            │            │
│  ┌─────────────────────────────────────────▼──────────┐ │
│  │     ml_models/  (PKL files on disk)                │ │
│  │   isolation_forest.pkl   survival_model.pkl        │ │
│  │   benchmark_random_forest.pkl  benchmark_xgboost.pkl│ │
│  │   lstm_forecaster.pt                               │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │   Data Cache (in-memory Pandas DataFrames)      │    │
│  │   telemetry_history.csv → _telemetry_df         │    │
│  │   health_trend_history.csv → _trend_df          │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│      PostgreSQL + PostGIS (Supabase-hosted)             │
│                                                         │
│  substations ←── feeders ←── transformers               │
│  users    maintenance_logs    failure_events            │
│  notifications   score_runs   transformer_scores        │
│  transformer_shap_explanations                          │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

**Dual data path (Supabase SDK + FastAPI):** The dashboard list page reads directly from Supabase using the JS client for speed (no backend round-trip for bulk reads). Individual transformer detail pages call the FastAPI backend for live ML inference and SHAP explanations.

**In-memory telemetry cache:** On startup, the backend loads `telemetry_history.csv` (24 hourly readings per transformer) into a global Pandas DataFrame. This avoids per-request disk I/O and allows the batch ML pipeline to process all transformers quickly.

**Scheduled batch scoring:** Instead of running ML inference on every page load, the system uses a daily batch job (`predict_daily_batch.py`) that scores all transformers overnight, writing results back to the `transformers` table. The dashboard shows these pre-computed results. Live inference is available on the detail page via the `/risk-score` endpoint.

---

## 4. Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Web Framework | FastAPI | 0.110.0 |
| ASGI Server | Uvicorn | 0.29.0 |
| ORM | SQLAlchemy 2.0 | 2.0.29 |
| Database Migrations | Alembic | 1.13.1 |
| DB Driver | psycopg2-binary | 2.9.9 |
| Spatial Extensions | GeoAlchemy2 | 0.14.6 |
| Config Management | Pydantic Settings | 2.2.1 |
| Anomaly Detection | scikit-learn (IsolationForest) | 1.4.2 |
| Survival Analysis | lifelines (CoxPHFitter) | 0.27.8 |
| Gradient Boosting | XGBoost | 2.0.3 |
| SHAP Explanations | SHAP | 0.45.0 |
| Deep Learning | PyTorch | (in requirements) |
| Task Queue | Celery + Redis | 5.3.6 + 5.0.3 |
| Auth | python-jose + Supabase JWT | 3.3.0 |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js 16 | ^16.2.10 |
| Language | TypeScript | ^5.4.5 |
| Styling | Tailwind CSS | ^3.4.19 |
| Charts | Recharts | ^2.15.4 |
| Map | Leaflet + React-Leaflet | 1.9.4 / 5.0.0 |
| Data Fetching | Axios | ^1.6.8 |
| State Management | Zustand | ^4.5.2 |
| Backend Client | Supabase JS | ^2.109.0 |
| Icons | Lucide React | ^1.23.0 |

---

## 5. Database Design

The database is hosted on Supabase (managed PostgreSQL with PostGIS extension). The schema has 9 tables organized around 3 domains:

### Asset Domain

**`substations`** — 33 kV grid connection points  
- `id` (UUID PK), `name`, `code`, `voltage_kv`, `district`, `location` (PostGIS GEOGRAPHY POINT)

**`feeders`** — 11 kV distribution feeders hanging off substations  
- `id`, `name`, `code`, `substation_id` (FK), `voltage_kv`, `feeder_type` (OVERHEAD/UNDERGROUND)

**`transformers`** — The core asset table. One transformer serves N consumers off a feeder.  
Fields include:
- Static specs: `transformer_code`, `rated_kva`, `voltage_hv_kv`, `voltage_lv_v`, `cooling_type`, `manufacturer`, `installation_date`, `age_years`
- Geographic: `location` (PostGIS GEOGRAPHY POINT, SRID 4326), `address_text`, `district`, `is_flood_prone`, `is_high_lightning`
- AI output columns (written by batch job): `current_health_score`, `current_failure_risk`, `current_status`, `current_load_pct`, `current_oil_temp_c`, `expected_lifetime_days`, `last_updated`

### Intelligence Domain

**`score_runs`** — Audit log of each batch ML run (timestamp, transformers scored, status)  
**`transformer_scores`** — Per-transformer per-run scores (anomaly_score, health_score, risk_category, expected_lifetime_days)  
**`transformer_shap_explanations`** — Per-feature SHAP values linked to a score record

### Event Domain

**`maintenance_logs`** — Engineer-recorded maintenance actions (oil filtration, replacement, inspection)  
**`failure_events`** — Historical failure records used for Cox PH survival training  
**`users`** — Engineer accounts (Supabase Auth integration)  
**`notifications`** — System-generated alerts for critical transformers

### PostGIS Usage

Transformer locations are stored as `Geography(POINT, 4326)` WKT elements. The frontend parses these into Leaflet marker coordinates. The backend extracts lat/lon using `geoalchemy2.shape.to_shape()` for weather API lookups.

---

## 6. AI & Machine Learning Pipeline

This is the technical core of the project. The AI pipeline is implemented in [`backend/services/ai_service.py`](/home/dipuser/DIP/INTERNSHIP/APDCL/backend/services/ai_service.py).

### 6.1 Feature Set

All models use the same 13 features:

| Feature | Description | How derived |
|---------|-------------|-------------|
| `temperature_c` | Oil winding temperature (°C) | Raw sensor reading |
| `load_percentage` | Load factor as % of rated KVA | Raw sensor reading |
| `voltage_lv` | LV side terminal voltage (V) | Raw sensor reading |
| `current_a` | Load current (A) | Raw sensor reading |
| `ambient_temperature` | Outdoor air temperature (°C) | Open-Meteo API |
| `age_years` | Transformer age | Installation date → DB |
| `rated_kva` | Nameplate capacity (kVA) | Asset register → DB |
| `power_factor` | Load power factor | Physics formula: `0.82 + (load/150)*0.16` |
| `load_ratio` | `load_percentage / 100` | Engineered |
| `current_ratio` | `current_a / rated_current` | Engineered (rated current from KVA) |
| `voltage_deviation` | `(415 - voltage_lv) / 415` | Engineered |
| `temperature_rise` | `temperature_c - ambient_temperature` | Engineered |
| `stress_index` | `current_ratio × temperature_rise × (1 + 0.05 × age_years)` | Engineered |

The last 5 are "physics-aware engineered features" — they encode domain knowledge about how transformers degrade. For example, stress_index captures the combined effect of overcurrent, heat, and aging that causes insulation deterioration.

### 6.2 Four-Model Pipeline

```
Telemetry (24h × 4 raw readings)
         │
         ▼
   Feature Engineering (13 features)
         │
    ┌────┼────┬──────────┐
    ▼    ▼    ▼          ▼
   IF   XGB  RF       Cox PH
    │    │    │          │
    ▼    ▼    ▼          ▼
anomaly  class class  survival
score  label  label   prob @ 365d
    │    │    │          │
    └────┼────┘          │
         ▼               │
    "winner model"       │
    (min health of      │
     XGB vs RF)          │
         │               │
         └───────┬────────┘
                 │
         Decision Fusion Engine
         0.50×Cox + 0.35×Winner + 0.15×IF
                 │
                 ▼
          Ensemble Health Score (0–100)
          Failure Probability (Sigmoid)
          Risk Category (HEALTHY/WARNING/CRITICAL)
          Expected Lifetime Days
```

#### Model 1 — Isolation Forest (Production Anomaly Detector)

The primary anomaly detection model. It's unsupervised — trained on the full feature set without labels.

- **Algorithm:** Isolation Forest with 150 estimators, contamination=0.12
- **Why this contamination?** The training dataset has ~12% WARNING+CRITICAL samples by physics-based simulation
- **Score transformation:** The raw `decision_function()` output (negative = more anomalous) is mapped to a 0–100 anomaly score using a sigmoid: `1 / (1 + exp(-3.0 × raw_score))` × 100
- **Role in fusion:** Provides the 15% weight in the Decision Fusion Engine

```python
# From ai_service.py
iforest_score = 100.0 / (1.0 + np.exp(-3.0 * raw_score))  # Invert + normalize
health_if = 100.0 - iforest_score
```

#### Model 2 — XGBoost Classifier (Supervised)

A 3-class gradient boosting classifier (SAFE/WARNING/CRITICAL).

- **Architecture:** 100 estimators, eval_metric=mlogloss, n_jobs=2
- **Training:** Supervised on the synthetic labeled dataset (`risk_label` column derived from physics-based health score)
- **Score output:** Class probabilities are mapped to a health score: `100 × (P_SAFE + 0.5 × P_WARNING)`
- **Benchmark result (on 2,000 test samples):** Accuracy 99.5%, F1 0.9950, ROC-AUC 1.0000

#### Model 3 — Random Forest Classifier (Supervised)

Same 3-class classification task as XGBoost but with a different algorithm.

- **Architecture:** 100 estimators, random_state=42
- **Score output:** Same probability-to-health-score mapping as XGBoost
- **Benchmark result (on 2,000 test samples):** Accuracy 99.65%, F1 0.9965, ROC-AUC 0.9999
- **Winner logic:** The Decision Fusion Engine uses `min(health_xgb, health_rf)` — the more conservative of the two classifiers — as the "winner" score

#### Model 4 — Cox Proportional Hazards (Survival Analysis)

This model provides **Remaining Useful Life (RUL)** estimation.

- **Library:** `lifelines.CoxPHFitter`
- **What it models:** Time-to-failure events given current operating conditions
- **Training process:** Failure durations are synthesized from risk labels: CRITICAL → 1–15 days, WARNING → 15–90 days, HEALTHY → 90–3,650 days
- **Score output:** Survival probability at t=365 days from `predict_survival_function()`. `P(survival @ 365d) × 100` = Cox health score
- **RUL output:** Median survival time from `predict_median()` in days
- **Role in fusion:** 50% weight — the most important model because it combines all risk factors into a long-term prognosis

#### 6.3 Decision Fusion Engine

The four models are combined using a weighted average:

```
Health Score = 0.50 × Cox_health + 0.35 × Winner_health + 0.15 × IF_health
```

Where:
- `Cox_health = P(survival@365d) × 100`
- `Winner_health = min(XGBoost_health, RandomForest_health)`  
- `IF_health = 100 - iforest_score`

**Dynamic re-weighting:** If any model fails to load (e.g. PKL file missing), the weights automatically shift to the remaining models proportionally. This makes the system fault-tolerant.

**Risk categorization threshold:**
```
Health Score ≥ 75  →  HEALTHY
Health Score ≥ 45  →  WARNING
Health Score < 45  →  CRITICAL
```

**Failure Probability (Sigmoid mapping):**
```python
failure_prob = 100.0 / (1.0 + exp(0.08 × (health_score - 45.0)))
```
This produces a smooth probability curve — a transformer at the WARNING/CRITICAL boundary (score=45) has a 50% failure probability.

### 6.4 SHAP Explainability

Both unsupervised (Isolation Forest) and supervised (XGBoost/Random Forest) models produce SHAP values.

- **Isolation Forest SHAP:** Uses `shap.TreeExplainer`. Values are **inverted** (multiplied by -1) so that positive SHAP = "increases risk"
- **Supervised SHAP:** Uses `shap.TreeExplainer` on the predicted class. Sign-multiplier is applied: `-1.0 if predicted HEALTHY else +1.0` to ensure positive = increases risk across all models
- **Frontend display:** A horizontal bar chart shows top features sorted by SHAP value. The user can toggle between Isolation Forest SHAP and XGBoost SHAP

### 6.5 Weather Integration

```python
# Calls Open-Meteo free API (no key needed)
url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
```

- The backend fetches live ambient temperature for each transformer's GPS coordinates
- Result is cached by (lat, lon) pair for 30 minutes using a simple dict cache to avoid API rate limits
- The ambient temperature feeds directly into the `temperature_rise` and `stress_index` features
- The frontend also independently calls Open-Meteo for the weather badge on the detail page

---

## 7. Backend API Implementation

The FastAPI backend is organized as follows:

```
backend/
├── main.py              # App entry point, startup events, CORS
├── core/
│   ├── config.py        # All settings via Pydantic BaseSettings
│   ├── database.py      # SQLAlchemy engine + session factory
│   └── security.py      # Supabase JWT verification
├── api/
│   ├── api.py           # Router aggregation
│   └── endpoints/
│       ├── asset.py     # CRUD for substations, feeders, transformers
│       ├── detail.py    # Transformer detail, timeseries, maintenance
│       ├── intelligence.py  # AI runs, risk scores, SHAP
│       ├── ml_analytics.py  # Benchmark + deep learning results
│       ├── operations.py    # Live inference, weather, all-models
│       ├── event.py         # Failure events, maintenance logs
│       ├── notification.py  # Alerts
│       └── user.py          # User management
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── crud/                # Database CRUD helpers
├── services/
│   ├── ai_service.py    # Core ML inference (4 models + fusion)
│   ├── inference_service.py  # Single-transformer scoring coordinator
│   ├── data_cache.py    # In-memory telemetry cache
│   ├── ml_benchmark.py  # RF + XGBoost benchmark suite
│   └── deep_learning.py # PyTorch LSTM training + inference
├── tasks/
│   └── scoring.py       # Background batch scoring task
├── scripts/
│   ├── generate_datasets.py   # Synthetic data generation
│   ├── train_production_models.py  # Model training pipeline
│   ├── predict_daily_batch.py # Batch scoring runner
│   └── seed_db.py             # DB population from CSV
└── data/               # Generated CSV/NPZ files (not committed)
└── ml_models/          # Trained PKL/PT model files (not committed)
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/transformers/` | All transformers (flat list) |
| GET | `/transformers/{id}/detail` | Full specs + feeder/substation names |
| GET | `/transformers/{id}/timeseries` | 24h telemetry readings (CSV cache + fallback) |
| GET | `/transformers/{id}/risk-score` | Latest AI risk score from DB |
| GET | `/transformers/{id}/shap-explanations` | SHAP feature importance values |
| GET | `/transformers/{id}/score-history` | 7-day health trend |
| GET | `/transformers/{id}/maintenance` | Maintenance log entries |
| POST | `/transformers/{id}/maintenance` | Log a new maintenance action |
| POST | `/ai-runs/trigger` | Trigger background ML scoring run |
| GET | `/ai-runs/latest` | Latest batch run metadata |
| GET | `/ml/benchmark` | RF vs XGBoost benchmark metrics |
| GET | `/ml/deep-learning` | LSTM training results |
| POST | `/ml/run-benchmark` | Trigger benchmark training |
| POST | `/ml/run-deep-learning` | Trigger LSTM training |
| GET | `/operations/live-score/{id}` | Live ML inference (not cached) |

### Startup Events

When the FastAPI app starts (`main.py`), it:
1. Calls `load_data_caches()` — loads `telemetry_history.csv` and `health_trend_history.csv` into memory
2. Calls `ai_service.load_models_if_needed()` — loads PKL model files from `ml_models/`
3. Registers APScheduler for any scheduled tasks (batch job scheduling, if configured)

### Configuration

All settings live in `core/config.py` via Pydantic BaseSettings and read from environment variables or `.env`:

- `POSTGRES_*` — DB credentials
- `SUPABASE_JWT_SECRET` — for JWT verification
- `ANOMALY_CONTAMINATION` — Isolation Forest contamination rate (default: 0.12)
- `HEALTH_WEIGHT_*` — Legacy weight config (actual fusion uses hardcoded 0.50/0.35/0.15)
- `NOMINAL_VOLTAGE`, `TEMPERATURE_LIMIT_*`, `LOAD_LIMIT_*` — Physics thresholds
- `TEMP_MIN/MAX_VALID`, `VOLTAGE_MIN/MAX_VALID` — Telemetry validation bounds

---

## 8. Frontend Implementation

The frontend is a Next.js 16 app using the App Router, TypeScript, and Tailwind CSS.

### Pages

#### `/` — Landing / Gateway Page
A simple login gateway. Shows "GridMind AI — Predictive Intelligence Core" with a security warning banner and an "Enter Dashboard" button. No actual authentication is enforced (auth was bypassed for the demo).

#### `/dashboard` — Main Operations Dashboard
The primary view for fleet-wide monitoring. Contains:

**1. KPI Header Cards (4 cards)**
- Network Health %: `(healthy_count / total_count) × 100`
- Active Alerts: count of CRITICAL + WARNING transformers
- Total Transformers: count from Supabase query
- Operations Panel: Refresh + Export CSV buttons

**2. Filters Bar**
- Search by transformer code
- Filter by substation, risk level, capacity range, operational status
- All filters applied client-side against the fetched dataset

**3. Bento Grid Layout**
- **Map (3×2 cells):** Leaflet map with colored markers (green/amber/red by risk category), clustering for dense areas, popup on click with transformer details
- **Risk Distribution (1×2 cells):** Donut/pie chart showing HEALTHY/WARNING/CRITICAL count breakdown (Recharts)
- **Asset Directory Table (3×2 cells):** Filterable list of top-10 matching transformers with anomaly scores and "Details" links
- **Critical Attention (1×2 cells):** Sorted list of highest-risk transformers
- **Tickets Widget (4×2 cells):** Maintenance tickets table with status/priority

**Data source:** Supabase JS client reads directly from `transformers_flat` database view (a PostGIS-aware view that exposes `latitude`/`longitude` as plain floats).

#### `/dashboard/transformers/[id]` — Transformer Detail Page
The most information-dense page. Loads data from 5 parallel API calls:
1. `/transformers/{id}/detail` — Static specs
2. `/transformers/{id}/timeseries` — 24h telemetry
3. `/transformers/{id}/maintenance` — Maintenance history
4. `/transformers/{id}/risk-score` — Latest AI score (from DB, pre-computed by batch job)
5. `/transformers/{id}/score-history` — 7-day health trend

Plus a direct call to Open-Meteo for ambient temperature.

**Sections:**
- **Hero Status Band:** Large health score gauge, HEALTHY/WARNING/CRITICAL badge, anomaly score, expected lifetime countdown
- **Model Selector:** Tabs for Ensemble Fused (default), Isolation Forest, XGBoost, Random Forest — switches the displayed anomaly score and category
- **Live Telemetry Charts:** Interactive area chart showing 24 hours of load %, voltage, temperature, or current (switchable with tab buttons)
- **AI SHAP Explanation Panel:** Horizontal bar chart showing which features are driving the AI's risk assessment. User can toggle between Isolation Forest SHAP and XGBoost SHAP
- **7-Day Health Trend:** Line chart showing how health score has evolved over the past week
- **Technical Specs Card:** Rated KVA, cooling type, voltage ratio, manufacturer, district, flood/lightning risk flags
- **Maintenance History:** Chronological list of past maintenance actions
- **Log Maintenance Form:** Form for engineers to record new maintenance actions (oil filtration, replacement, etc.)

#### `/map` — Full-Screen Network Map
A dedicated full-screen Leaflet map with filter buttons (ALL/CRITICAL/WARNING/HEALTHY/UNKNOWN). Loads from the FastAPI backend (not Supabase). Useful for geographic analysis — seeing which areas have clusters of at-risk transformers.

#### `/ml-analytics` — AI Analytics & Academic Suite
Two-tab page:

**Tab 1 — Model Benchmarks:** Shows the benchmark results from `benchmark_results.json`:
- Summary cards: Best model, highest ROC-AUC, test sample count
- Metrics table: Accuracy, F1-Score, ROC-AUC per model
- ROC Curve chart: FPR vs TPR curves for each classifier (Recharts LineChart)
- "Train Pipelines" dropdown button to trigger retraining in background

**Tab 2 — Deep Learning (LSTM Forecast):** Shows LSTM training results:
- Architecture card: Validation MSE loss, epochs trained
- Sample forecasting chart: Hardcoded reference chart showing conceptual actual vs predicted 24h load/temperature

### Frontend State Management

State is managed at the page level using React `useState` and `useCallback`. There is no global state (Zustand is installed but not actively used for primary state). Data is fetched fresh on each page mount.

### API Client

`/src/lib/api.ts` defines an Axios instance pointing to `NEXT_PUBLIC_API_URL` (default: `http://127.0.0.1:8000/api/v1`). An interceptor attaches the Supabase JWT token to every request. Another interceptor handles 401 responses by signing out.

---

## 9. Data Pipeline & Synthetic Dataset Generation

Since no real-time SCADA feed was available, I built a physics-based synthetic data generator (`scripts/generate_datasets.py`). The generation logic is transparent and documented.

### Dataset 1: `telemetry_history.csv`

24 hourly readings per transformer, representing the past 24 hours. Generated for:
- 5% of transformers: marked CRITICAL status → elevated load (110–140%), elevated temperature
- 10% of transformers: marked WARNING status → moderate stress (80–105% load)
- 85% of transformers: HEALTHY → normal load (30–80%), normal temperature

Temperature is calculated from ambient temperature + I²R heating component + aging factor:
```python
temp = ambient_temp + (current / rated_current)² × 45.0 + age_years × 0.4 + noise
```

Current is derived from KVA × load_factor ÷ (√3 × voltage). Voltage has a physics-based drop based on load current and transformer impedance (4.5% typical).

**Seeds are deterministic:** using `random.Random(f"{transformer_id}_{hour_string}")` ensures the same transformer always gets the same telemetry for the same hour — important for reproducibility during testing.

### Dataset 2: `ml_training_dataset.csv`

10,000 labeled samples for supervised model training. Each sample is an independently generated operating point, not a time series. The physics formulas mirror those in the telemetry generator:

```
health = 100 - temp_penalty - load_penalty - voltage_penalty - current_penalty - age_penalty
```

Where:
- `temp_penalty = ((max(0, temp - 70) / 15)² × 12`
- `load_penalty = ((max(0, load - 80) / 20)² × 10`
- `age_penalty = (age / 25)^1.8 × 12`

Labels:
- `health ≥ 75` → SAFE (label=0)
- `45 ≤ health < 75` → WARNING (label=1)
- `health < 45` → CRITICAL (label=2)

Distribution from a representative run: ~87% SAFE, ~7% WARNING, ~6% CRITICAL.

### Dataset 3: `health_trend_history.csv`

7-day health history per transformer, used for the trend chart on the detail page. Generated by working backwards from current `failure_risk` with bounded random daily variance.

### Dataset 4: `lstm_training_data.npz`

2,000 synthetic 48-hour sequences for LSTM training. Each sequence has `[temp, load, voltage, current]` for 48 hours. Input: first 24h. Target: next 24h `[load, temp]`.

### Batch Scoring Script (`predict_daily_batch.py`)

This script ties everything together:

1. Loads telemetry cache from CSV
2. Queries all transformers from DB using `yield_per(100)` (memory-efficient)
3. For each transformer, calls `ai_service.predict_daily_health()` with validated telemetry readings
4. Validates readings against bounds (`TEMP_MIN_VALID`, `VOLTAGE_MIN_VALID`, etc.) — physically impossible values are rejected
5. Writes back to DB: `current_health_score`, `current_failure_risk`, `current_status`, `current_load_pct`, `current_oil_temp_c`
6. Commits every 100 transformers to prevent memory buildup

The script is designed to run via cron or Celery scheduler. Currently it's triggered manually or via the `/ai-runs/trigger` API endpoint.

---

## 10. Model Benchmarking & Evaluation

The `services/ml_benchmark.py` module implements a rigorous benchmark of the two supervised classifiers.

### Setup

- **Dataset:** 10,000 samples from `ml_training_dataset.csv`
- **Train/Test split:** 80% train / 20% test (stratified by class)
- **Features:** All 13 (same as production models)
- **Models compared:** Random Forest (200 trees, class_weight=balanced) vs XGBoost (200 boosting rounds, learning_rate=0.05)

### Results (from `ml_models/benchmark_results.json`)

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
|-------|----------|-----------|--------|----------|---------|
| Random Forest | 99.65% | 0.9966 | 0.9965 | 0.9965 | 0.9999 |
| XGBoost | 99.50% | 0.9950 | 0.9950 | 0.9950 | 1.0000 |

**Best model by ROC-AUC:** XGBoost (1.0000)

### Confusion Matrix — Random Forest

```
              Predicted SAFE  Predicted WARNING  Predicted CRITICAL
Actual SAFE       1754              3                  0
Actual WARNING       2             67                  0
Actual CRITICAL      0              2                172
```

### Cross-Validation (5-fold, on training set)

- **Random Forest:** Mean F1 = 0.9929 ± 0.0012
- **XGBoost:** Mean F1 = 0.9959 ± 0.0006

### Important Caveat

These near-perfect scores reflect the fact that both the training data and the test data were generated by the same physics formula. The model has essentially learned to reconstruct the physics equation. Real-world performance would be lower because:
- Real sensor data has noise, drift, and measurement errors
- CRITICAL failure events are extremely rare in practice
- The training distribution may not match real-world failure modes

This is honestly stated — the benchmark exists to demonstrate ML methodology for academic assessment, not to claim real-world accuracy.

---

## 11. Deep Learning — LSTM Forecasting

Implemented in `services/deep_learning.py` using PyTorch.

### Architecture

```
Input: [batch, 24, 4]   ← 24 hours of [temp, load, voltage, current]
  │
  └→ LSTM Layer 1: hidden_size=128, dropout=0.2
       │
  └→ LSTM Layer 2: hidden_size=128, dropout=0.2  (stacked)
       │
  Last hidden state: [batch, 128]
       │
  FC(128 → 64) → ReLU → Dropout(0.2)
       │
  FC(64 → 24×2)
       │
  Reshape → [batch, 24, 2]

Output: [batch, 24, 2]  ← Next 24 hours of [load, temp]
```

### Training Details

- **Optimizer:** Adam (lr=0.001)
- **Loss:** MSE (regression — forecasting actual values)
- **Epochs:** 50
- **Batch size:** 64
- **Regularization:** Gradient clipping (max_norm=1.0) + dropout
- **Scheduler:** ReduceLROnPlateau with patience=5, factor=0.5
- **Train/Val split:** 80/20

### Model Persistence

After training, the model state dict is saved to `ml_models/lstm_forecaster.pt` and normalization parameters (X_mean, X_std, y_mean, y_std) to `ml_models/lstm_normalization.pkl`. If the model files exist at startup, they're loaded for inference.

The LSTM can be invoked via `predict_lstm_forecast(past_24h_sequence)` for any transformer given its last 24 hours of data.

---

## 12. Deployment Architecture

### Production Deployment

The system is configured for deployment on:

**Backend:** Render.com (Python web service)
- `render.yaml` specifies: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Region: Singapore (closest to Assam/India)
- Build command: `pip install -r requirements.txt`
- Health check path: `/health`
- Environment variables managed through Render secrets

**Frontend:** Vercel
- Auto-deploys from Git on push
- `NEXT_PUBLIC_API_URL` points to Render backend URL
- `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` for direct DB access

**Database:** Supabase
- Managed PostgreSQL + PostGIS in Supabase cloud
- The `transformers_flat` view is a SQL view that projects PostGIS geometry to plain float lat/lon for the frontend
- A Supabase anon key is used for read-only dashboard access; write operations go through the FastAPI backend

### Local Development

```bash
# Backend
cd backend
PYTHONPATH=. ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev -- --port 3000
```

### Database Initialization Sequence

```bash
# 1. Generate synthetic datasets
python scripts/generate_datasets.py

# 2. Train production models
python scripts/train_production_models.py

# 3. Seed database with transformer records
python scripts/seed_db.py

# 4. Run initial batch scoring to populate health columns
python scripts/predict_daily_batch.py
```

---

## 13. Known Limitations & Honest Assessment

**1. Synthetic data only**  
All telemetry is synthetically generated. The system has not been connected to real APDCL SCADA sensors. The benchmark accuracy numbers (99%+) reflect the synthetic nature of the data, not real-world performance.

**2. Models trained on simulation, not historical failures**  
The Cox PH survival model's "failure durations" are generated from risk labels, not from actual transformer failure records. In a production system, you would train this on 10–20 years of historical failure event data.

**3. No real-time streaming**  
There's no message queue (Kafka, MQTT) connecting sensors to the backend. The "24-hour telemetry" is loaded from a static CSV on startup. Real IoT integration would require a streaming pipeline.

**4. Batch scoring delay**  
Dashboard health scores reflect the last batch run, not live conditions. A transformer that suddenly spikes in temperature won't be flagged until the next batch job runs. The `/operations/live-score` endpoint allows real-time scoring but requires an explicit API call.

**5. Authentication bypassed**  
The API router comment reads: `# DEV OVERRIDE: Bypassed authentication as requested.` The Supabase JWT verification is implemented but disabled. Any user can access all API endpoints without a token.

**6. LSTM forecast visualization is illustrative**  
The LSTM training is real (50 epochs on 2,000 sequences, saved to `.pt` file). But the forecast chart on the ML Analytics page uses hardcoded representative values, not live LSTM inference output, because building a full real-time forecasting UI was beyond the internship scope.

**7. Ticket system partially implemented**  
The `TicketsWidget` on the dashboard reads from a Supabase table but ticket creation from the dashboard isn't implemented (only from the detail page's maintenance form).

---

## 14. Learnings & Outcomes

### Technical Learnings

**Isolation Forest for anomaly detection:** I learned why unsupervised anomaly detection is genuinely valuable here — you don't need labeled failure data. The model learns what "normal" looks like and flags deviations. The challenge is that it can't tell you *why* something is anomalous without SHAP.

**Survival analysis is the right framing:** The Cox PH model taught me that transformer health is fundamentally a survival analysis problem, not a classification problem. The question isn't "is this transformer bad?" but "how long until this transformer fails?" The expected_lifetime_days output is more actionable for maintenance scheduling.

**Feature engineering matters more than model selection:** The 5 engineered features (load_ratio, current_ratio, voltage_deviation, temperature_rise, stress_index) gave much better model performance than the 4 raw sensor readings alone. Embedding domain physics into features is powerful.

**PostGIS for spatial data:** Working with geographic coordinates in PostgreSQL using GeoAlchemy2 was new for me. Storing locations as WGS84 POINT geography and extracting lat/lon for weather API lookups was an interesting challenge.

**Fusion > individual models:** Any single model can be fooled or fail. The decision fusion approach (50% Cox + 35% classifier + 15% IF) is more robust and gives more interpretable results than relying on any single model.

### System Design Learnings

- **In-memory caching** of static telemetry CSV dramatically simplifies the batch inference pipeline compared to hitting the DB for every transformer
- **Deterministic random seeds** using transformer ID + timestamp strings are essential for reproducible synthetic telemetry
- **Pydantic BaseSettings** makes configuration management clean and secure — no hardcoded secrets
- **FastAPI's BackgroundTasks** is sufficient for triggering ML training jobs without a full Celery setup for simple demos

### What I Would Do Differently

1. Use actual APDCL historical maintenance and failure records instead of synthetic generation
2. Add a proper message queue (MQTT broker) to receive sensor readings in real-time
3. Implement proper user authentication before letting this anywhere near production
4. Build a proper A/B testing framework to compare model versions as they're retrained
5. Add model drift monitoring — the Isolation Forest score distribution should be tracked over time

---

## 15. Conclusion

GridMind demonstrates that a comprehensive AI-powered transformer monitoring system can be built from first principles using modern open-source tools. The multi-model architecture — combining unsupervised anomaly detection, supervised classification, and survival analysis — provides a more complete picture of transformer health than any single model could.

The SHAP integration is particularly important: showing field engineers *which* parameters triggered an alert (oil temperature is high, or load factor has been consistently over 90%) is more useful than just showing them a red badge. Explainability converts the AI from a black box into a decision-support tool.

The system architecture is designed to be extended. Adding real IoT sensor integration would primarily require replacing the static CSV cache with a streaming pipeline — the rest of the inference and dashboard code is already in place.

For APDCL's use case, the most immediate value would come from deploying a version of this system with even a partial subset of real historical failure data, which would dramatically improve the Cox PH model's RUL estimates and give the Isolation Forest a better calibration of what "normal" actually looks like in Assam's climate.

---

*Report prepared by internship student as part of the APDCL Summer Internship Program, 2026.*  
*GridMind source code: [github.com/dipuser/APDCL/gridmind]*  
*Backend: FastAPI + PostgreSQL | Frontend: Next.js 16 | ML: Scikit-Learn + XGBoost + Lifelines + PyTorch*
