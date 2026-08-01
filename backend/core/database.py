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

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    **({} if is_sqlite else {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    }),
    connect_args=connect_args,
    echo=settings.API_DEBUG,
)

# ─── Session Factory ──────────────────────────────────────────────────────────
# SessionLocal is a class. Calling SessionLocal() creates a new session.
SessionLocal = sessionmaker(
    autocommit=False,   # Don't auto-commit — we commit manually after successful operations
    autoflush=False,    # Don't auto-flush — we flush manually
    bind=engine,
)

# Note: Base is defined in models/base.py to avoid circular imports.


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
