#!/bin/bash
# ─── GridMind Docker Setup Script ────────────────────────────────────────────
# Run this ONCE after `docker compose up -d` to initialize the database,
# seed transformer data, and train ML models inside the backend container.
#
# Usage:
#   chmod +x docker-setup.sh
#   ./docker-setup.sh

set -e

BACKEND="gridmind-backend"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║          GridMind — Docker Setup Script             ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# 1. Wait for backend to be healthy
echo "[1/5] Waiting for backend container to be ready..."
until docker compose exec backend python -c "import sys; sys.exit(0)" 2>/dev/null; do
  echo "  ... waiting"
  sleep 3
done
echo "  ✅ Backend container is running"

# 2. Run database migrations
echo ""
echo "[2/5] Running Alembic database migrations..."
docker compose exec backend alembic upgrade head
echo "  ✅ Database schema is up to date"

# 3. Seed transformer data
echo ""
echo "[3/5] Seeding transformer records..."
docker compose exec backend python scripts/seed_db.py
echo "  ✅ Transformer data seeded"

# 4. Generate training dataset
echo ""
echo "[4/5] Generating ML training dataset (10,000 samples)..."
docker compose exec backend python scripts/generate_datasets.py
echo "  ✅ Training dataset generated"

# 5. Train ML models
echo ""
echo "[5/5] Training all ML models (IF, Cox PH, XGBoost, RF)..."
docker compose exec backend python scripts/train_production_models.py
docker compose exec backend python -c "from services.ml_benchmark import run_benchmark; run_benchmark()"
echo "  ✅ All models trained and saved"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║               Setup Complete! 🎉                    ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║  Dashboard  →  http://localhost:3000                ║"
echo "║  API Docs   →  http://localhost:8000/api/docs       ║"
echo "║                                                      ║"
echo "║  Login: admin@gridmind.com / GridMind@2026           ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
