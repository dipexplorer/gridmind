"""
GridMind Backend — FastAPI Application Entry Point

This file creates the FastAPI app instance, registers all routers,
adds middleware, and sets up global exception handlers.

Think of this as the "main.py" of the whole backend.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings

# ─── Create the FastAPI Application ───────────────────────────────────────────
app = FastAPI(
    title="GridMind API",
    description="Transformer Predictive Maintenance Intelligence Platform",
    version="1.0.0",
    docs_url="/api/docs",       # Swagger UI will be at http://localhost:8000/api/docs
    redoc_url="/api/redoc",     # ReDoc alternative at http://localhost:8000/api/redoc
)

# ─── CORS Middleware ───────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# This allows the Next.js frontend (localhost:3000) to call the API (localhost:8000)
# Without this, browsers block cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",")] if isinstance(settings.CORS_ORIGINS, str) else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],                    # GET, POST, PUT, PATCH, DELETE
    allow_headers=["*"],
)

# ─── Health Check ─────────────────────────────────────────────────────────────
# This is the simplest possible endpoint.
# A monitoring system (or Docker health check) hits this to verify the app is alive.
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


def schedule_daily_batch():
    """
    Background thread to execute daily ML predictions batch run automatically.
    First execution starts 24 hours after server startup to avoid startup CPU/RAM spikes and Render timeouts.
    """
    import time
    import logging
    logger = logging.getLogger("startup_scheduler")
    logger.info("Daily batch prediction scheduler initialized. First run scheduled in 24 hours.")
    # Sleep for 24 hours before the first run
    time.sleep(86400)
    from scripts.predict_daily_batch import run_batch_prediction
    while True:
        try:
            logger.info("Automatically executing daily batch prediction run...")
            run_batch_prediction()
            logger.info("Automatic daily batch prediction completed successfully.")
        except Exception as e:
            logger.error(f"Automatic daily batch prediction run failed: {e}")
        # Sleep for 24 hours
        time.sleep(86400)

@app.on_event("startup")
async def startup_event():
    import asyncio
    from services.websocket import manager
    manager.loop = asyncio.get_running_loop()
    
    # Load telemetry and health trend caches
    from services.data_cache import load_data_caches
    load_data_caches()
    
    # Pre-load PyTorch LSTM inference engine
    from services.deep_learning import get_lstm_inference_engine
    get_lstm_inference_engine()
    
    import threading
    threading.Thread(target=schedule_daily_batch, daemon=True).start()

# ─── Root Redirect ────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    return {"message": "GridMind API. Visit /api/docs for documentation."}


# ─── TODO: Register API routers here as we build them ─────────────────────────
from api.api import api_router
from api.endpoints import websockets

app.include_router(websockets.router, prefix="/api/v1/ws", tags=["WebSockets"])
app.include_router(api_router, prefix="/api/v1")

# ─── ML Analytics Suite (Public — No Auth required for academic demo) ──────────
from api.api import ml_public_router
app.include_router(ml_public_router, prefix="/api/v1")

