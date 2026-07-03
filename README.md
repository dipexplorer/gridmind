# GridMind 🔌

**Adaptive Reliability Intelligence Platform for APDCL**

> Transformer predictive maintenance — from reactive break-fix to data-driven, explainable risk prioritization.

[![CI](https://github.com/dipexplorer/gridmind/actions/workflows/ci.yml/badge.svg)](https://github.com/dipexplorer/gridmind/actions)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## What is GridMind?

APDCL manages thousands of distribution transformers across Assam. Today, these are serviced only after they fail — causing unplanned outages for hundreds of consumers, emergency repair costs, and crew inefficiency.

**GridMind** solves this by:

1. **Unifying** transformer asset data, maintenance logs, complaints, and load history in one place
2. **Scoring** each transformer using **survival analysis** (Cox Proportional Hazards) + **anomaly detection** (Isolation Forest) — statistically grounded, not arbitrary weighted formulas
3. **Prioritizing** by combining failure probability with consumer impact — a transformer serving a hospital zone is ranked higher than one in a field, even at equal risk
4. **Explaining** every risk score via SHAP factors — so engineers understand *why*, not just *what*
5. **Displaying** all this on a WebGL-accelerated GIS map and dashboard

---

## ⚡ Quick Start (5 minutes)

**Prerequisites:** [Docker](https://docs.docker.com/get-docker/) 24.0+ and [Docker Compose](https://docs.docker.com/compose/) 2.20+

```bash
# 1. Clone
git clone https://github.com/your-org/gridmind.git
cd gridmind

# 2. Configure environment
cp .env.example .env
# Edit .env — change passwords and JWT secret (see docs/development/SETUP_GUIDE.md)

# 3. Start all services
docker compose up -d

# 4. Initialize database
docker compose exec backend alembic upgrade head

# 5. Load synthetic demo data + train ML models
docker compose exec backend python scripts/generate_synthetic_data.py --n-transformers 500
docker compose exec backend python scripts/train_models.py
docker compose exec backend python scripts/create_admin.py

# 6. Open the app
#    Dashboard:   http://localhost:3000
#    API docs:    http://localhost:8000/api/docs
#    Task monitor: http://localhost:5555
```

Default admin credentials (change immediately):
```
username: admin
password: GridMind@2026
```

---

## 🏗️ Architecture Overview

```
User Browser
     │
     ▼
  Nginx (port 80/443)
  ├── /        → Next.js 14 (TypeScript) — Dashboard, GIS Map, Admin
  └── /api     → FastAPI (Python 3.11)   — REST API + WebSocket
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
     PostgreSQL    Redis 7    Celery Workers
     + PostGIS     (cache +   (async scoring,
     + TimescaleDB  broker)    ETL, ML retrain)
          │
          ▼
   Intelligence Engine
   ├── Cox PH Survival Analysis (lifelines)
   ├── Isolation Forest Anomaly Detection (scikit-learn)
   ├── Impact-Weighted Priority Score
   └── SHAP Explainability (shap)
```

**Key design decisions:**
- Survival analysis (not binary classification) — handles right-censored transformer data correctly
- Unsupervised anomaly detection — useful from Day 1 without labeled failure data
- Celery + Redis — async intelligence pipeline, API is never blocked
- Deck.gl WebGL GIS — renders 10,000+ transformer markers at 60fps

See [`docs/architecture/SYSTEM_DESIGN.md`](docs/architecture/SYSTEM_DESIGN.md) for the full design.

---

## 📁 Project Structure

```
gridmind/
├── backend/                    # FastAPI + Celery + ML Intelligence Engine
│   ├── api/                   # REST API routers (transformers, risk, auth…)
│   ├── models/                # SQLAlchemy ORM models
│   ├── schemas/               # Pydantic request/response schemas
│   ├── services/              # Intelligence engine (survival, anomaly, SHAP)
│   ├── tasks/                 # Celery async tasks (ETL, scoring, ML retrain)
│   ├── scripts/               # Utility scripts (synthetic data, training)
│   ├── tests/                 # pytest unit + integration tests
│   └── alembic/               # Database migrations
│
├── frontend/                   # Next.js 14 TypeScript dashboard
│   └── src/
│       ├── app/               # Pages: dashboard, map, transformers, admin
│       ├── components/        # Deck.gl map, Recharts charts, UI components
│       ├── lib/               # API client, utilities
│       └── store/             # Zustand UI state
│
├── docs/                       # All project documentation (20 files)
│   ├── architecture/          # System design, API spec, DB schema, event flows
│   ├── product/               # Feature roadmap, user stories, KPIs
│   ├── engineering/           # ML design, health score spec, data pipeline
│   ├── data/                  # Data dictionary, synthetic data plan
│   ├── development/           # Setup guide, testing, security, contributing
│   └── handover/              # Deployment guide, user manual, handover checklist
│
├── nginx/                      # Nginx reverse proxy configuration
├── docker-compose.yml          # Docker service definitions
├── docker-compose.prod.yml     # Production overrides
├── .env.example                # Environment variable template
└── .github/workflows/ci.yml   # GitHub Actions CI pipeline
```

---

## 📚 Documentation Index

| Category | Document | Description |
|----------|----------|-------------|
| **Architecture** | [SYSTEM_DESIGN.md](docs/architecture/SYSTEM_DESIGN.md) | Full system architecture, components, data flows |
| **Architecture** | [API_SPEC.md](docs/architecture/API_SPEC.md) | REST API + WebSocket endpoint reference |
| **Architecture** | [DATABASE_SCHEMA.md](docs/architecture/DATABASE_SCHEMA.md) | PostgreSQL schema with PostGIS + TimescaleDB |
| **Architecture** | [EVENT_FLOW.md](docs/architecture/EVENT_FLOW.md) | Async Celery pipeline design |
| **Architecture** | [ARCHITECTURE_DECISIONS.md](docs/architecture/ARCHITECTURE_DECISIONS.md) | Why each technology was chosen (ADR format) |
| **Product** | [FEATURE_ROADMAP.md](docs/product/FEATURE_ROADMAP.md) | 4-week sprint plan with test criteria |
| **Product** | [USER_STORIES.md](docs/product/USER_STORIES.md) | User stories with acceptance criteria |
| **Product** | [KPI_DEFINITIONS.md](docs/product/KPI_DEFINITIONS.md) | System and business KPIs |
| **Product** | [PRODUCT_BRIEF.md](docs/product/PRODUCT_BRIEF.md) | Executive 1-pager for non-technical stakeholders |
| **Engineering** | [HEALTH_SCORE_SPEC.md](docs/engineering/HEALTH_SCORE_SPEC.md) | Survival analysis + anomaly detection spec |
| **Engineering** | [ML_DESIGN.md](docs/engineering/ML_DESIGN.md) | ML model training, validation, versioning |
| **Engineering** | [DATA_PIPELINE.md](docs/engineering/DATA_PIPELINE.md) | ETL pipeline for CSV ingestion |
| **Engineering** | [SCORING_VALIDATION_REPORT.md](docs/engineering/SCORING_VALIDATION_REPORT.md) | Model validation results on synthetic data |
| **Engineering** | [ERROR_HANDLING_SPEC.md](docs/engineering/ERROR_HANDLING_SPEC.md) | Resilience and error handling design |
| **Engineering** | [ALERT_DESIGN.md](docs/engineering/ALERT_DESIGN.md) | In-app notification and alert design |
| **Data** | [DATA_DICTIONARY.md](docs/data/DATA_DICTIONARY.md) | Field definitions, types, constraints |
| **Data** | [SYNTHETIC_DATA_PLAN.md](docs/data/SYNTHETIC_DATA_PLAN.md) | Synthetic data generation strategy |
| **Data** | [INTEGRATION_GUIDE.md](docs/data/INTEGRATION_GUIDE.md) | CSV import format guide |
| **Development** | [SETUP_GUIDE.md](docs/development/SETUP_GUIDE.md) | Local development setup |
| **Development** | [TESTING_STRATEGY.md](docs/development/TESTING_STRATEGY.md) | Unit, integration, and ML test strategy |
| **Development** | [SECURITY.md](docs/development/SECURITY.md) | Auth, data protection, security practices |
| **Development** | [CONTRIBUTING.md](docs/development/CONTRIBUTING.md) | Contribution guidelines |
| **Handover** | [DEPLOYMENT_GUIDE.md](docs/handover/DEPLOYMENT_GUIDE.md) | Production deployment to APDCL server |
| **Handover** | [USER_MANUAL.md](docs/handover/USER_MANUAL.md) | End-user guide for admins and engineers |
| **Handover** | [HANDOVER_CHECKLIST.md](docs/handover/HANDOVER_CHECKLIST.md) | Project handover checklist |

---

## 🧑‍💻 Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | Python 3.11 + FastAPI | ML ecosystem, async API, auto-generated Swagger docs |
| **ML / Intelligence** | lifelines (Cox PH) + scikit-learn (IForest) + shap | Survival analysis for censored data; unsupervised anomaly detection |
| **Database** | PostgreSQL 16 + PostGIS + TimescaleDB | Geo-queries + time-series + ACID compliance |
| **Cache / Queue** | Redis 7 | Dual role: Celery broker + score cache |
| **Async Tasks** | Celery 5 + Celery Beat | Async ML pipeline; nightly scoring schedule |
| **Frontend** | Next.js 14 (TypeScript) | SSR, production-grade React framework |
| **GIS Map** | Deck.gl (WebGL) | 10,000+ transformer markers at 60fps |
| **Charts** | Recharts | React-native chart library |
| **State** | TanStack Query + Zustand | Server state + UI state |
| **DevOps** | Docker Compose + GitHub Actions + Nginx | Multi-service orchestration + CI/CD |

---

## 🤝 Contributing

See [`docs/development/CONTRIBUTING.md`](docs/development/CONTRIBUTING.md) for:
- Branch naming conventions
- Commit message format
- PR review process
- Code style (ruff for Python, ESLint + Prettier for TypeScript)

---

## 📋 Development Roadmap

| Week | Focus | Key Milestone |
|------|-------|---------------|
| **Week 1** (Jul 3–9) | Foundation: Docker, DB schema, ETL | Admin can upload CSV → data in DB |
| **Week 2** (Jul 10–16) | Intelligence engine: Cox PH + IForest + SHAP | Risk scores visible via API |
| **Week 3** (Jul 17–23) | Full REST API + Next.js dashboard MVP | Demo-able to stakeholders |
| **Week 4** (Jul 24–31) | GIS map + CI/CD + documentation | Production deployment ready |

See [`docs/product/FEATURE_ROADMAP.md`](docs/product/FEATURE_ROADMAP.md) for the detailed sprint plan.

---

## 📄 License

MIT License — see [LICENSE](LICENSE).

---

*Built during APDCL Internship, July 2026 | Guwahati, Assam, India*
