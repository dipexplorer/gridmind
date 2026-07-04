"""
Alembic Environment Configuration

Alembic is the database migration tool for SQLAlchemy.
"Migration" = a versioned script that changes the DB schema (add table, add column, etc.)

This file tells Alembic:
  1. How to connect to the database
  2. Which SQLAlchemy models to use as the "target" schema

HOW MIGRATIONS WORK:
  1. You modify a SQLAlchemy model (e.g., add a column to Transformer)
  2. Run: alembic revision --autogenerate -m "add firmware column"
     → Alembic compares current DB schema vs your models → generates a migration script
  3. Run: alembic upgrade head
     → Alembic runs the migration script against the DB → DB is updated

The migration scripts live in: backend/alembic/versions/
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# This imports our app's configuration (reads .env file)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.config import settings
from models.base import Base

# ─── Import ALL models here so Alembic can "see" them ─────────────────────────
import models


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the database URL from our settings (instead of alembic.ini)
# We must replace '%' with '%%' because Alembic uses ConfigParser which interprets '%' for interpolation.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# target_metadata tells Alembic what the DB SHOULD look like (our models)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def include_name(name, type_, parent_names):
    if type_ == "table":
        return name not in ["spatial_ref_sys"]
    return True

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_name=include_name
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
