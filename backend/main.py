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
    allow_origins=settings.CORS_ORIGINS,   # List of allowed origins from .env
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


import asyncio
from services.websocket import manager

@app.on_event("startup")
async def startup_event():
    manager.loop = asyncio.get_running_loop()

# ─── Root Redirect ────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    return {"message": "GridMind API. Visit /api/docs for documentation."}


# ─── TODO: Register API routers here as we build them ─────────────────────────
from api.api import api_router
from api.endpoints import websockets

app.include_router(websockets.router, prefix="/api/v1/ws", tags=["WebSockets"])
app.include_router(api_router, prefix="/api/v1")
