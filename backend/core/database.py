"""
Database Connection Setup — SQLAlchemy

This file creates two things:
  1. `engine`     — the connection to PostgreSQL
  2. `SessionLocal` — a factory that creates DB sessions

HOW IT WORKS:
  - SQLAlchemy uses a "connection pool" — it keeps N connections open
    and reuses them. pool_pre_ping=True tests connections before use
    (prevents "stale connection" bugs).

  - A "session" is like a unit of work. You open a session, do queries,
    commit, and close. All changes in a session are atomic (all or nothing).

HOW TO USE IN API ENDPOINTS:
  Use the `get_db` dependency function with FastAPI's dependency injection:

  ```python
  from core.database import get_db
  from sqlalchemy.orm import Session
  from fastapi import Depends

  @router.get("/transformers")
  def list_transformers(db: Session = Depends(get_db)):
      return db.query(Transformer).all()
      # Session is automatically closed after the request finishes
  ```
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import settings

# ─── Create the Engine ────────────────────────────────────────────────────────
# The "engine" is the core SQLAlchemy object that manages the connection pool
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,     # Test connection before each use; reconnect if dead
    pool_recycle=3600,      # Recycle connections every 1 hour (prevents stale connections)
    pool_size=10,           # Keep 10 connections open in the pool
    max_overflow=20,        # Allow up to 20 extra connections during spikes
    echo=settings.API_DEBUG, # Log all SQL statements when DEBUG=true (very useful!)
)

# ─── Session Factory ──────────────────────────────────────────────────────────
# SessionLocal is a class. Calling SessionLocal() creates a new session.
SessionLocal = sessionmaker(
    autocommit=False,   # Don't auto-commit — we commit manually after successful operations
    autoflush=False,    # Don't auto-flush — we flush manually
    bind=engine,
)

# ─── Base Class for Models ────────────────────────────────────────────────────
# All SQLAlchemy ORM models (tables) must inherit from this Base class.
# It tracks all model definitions and is used by Alembic for migrations.
Base = declarative_base()


# ─── Dependency: get_db ───────────────────────────────────────────────────────
# This is a FastAPI dependency that:
#   1. Opens a DB session before the request
#   2. Yields it to the endpoint function
#   3. Closes it after the request (even if an exception occurred)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
