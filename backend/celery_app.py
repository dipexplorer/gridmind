"""
Celery Application Instance

Celery is our background task queue.
When the API receives a CSV upload, instead of processing it RIGHT NOW (which would
block the response for 30+ seconds), it hands the work off to Celery:

  API → puts a "task" message into Redis → returns 202 immediately
  Celery Worker → picks up the task from Redis → does the heavy work

This file creates the Celery app object. All task files import from this.

QUEUES:
  We use 3 separate queues with different priorities:
    - etl:     CSV parsing and database insertion (fast, user-facing)
    - scoring: ML model inference (moderate speed)
    - ml:      Model retraining (slow, runs weekly in background)
"""
from celery import Celery
from celery.schedules import crontab

from core.config import settings

# ─── Create the Celery App ────────────────────────────────────────────────────
celery_app = Celery(
    "gridmind",
    broker=settings.REDIS_URL,          # Where tasks are sent (Redis)
    backend=settings.REDIS_URL,         # Where results are stored (Redis)
    include=[                           # Python modules containing tasks
        "tasks.etl",
        "tasks.scoring",
        "tasks.ml",
    ],
)

# ─── Celery Configuration ─────────────────────────────────────────────────────
celery_app.conf.update(
    # Serialization — use JSON so task arguments are human-readable
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    
    # Run tasks synchronously (Eager mode) to bypass Redis requirement for testing
    task_always_eager=True,

    # Reliability — only acknowledge a task as "done" after successful completion
    # (If a worker crashes mid-task, the task is re-queued)
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Result expiry — store task results for 24 hours (for status polling)
    result_expires=86400,

    # Queue routing — each task type goes to its own queue
    task_routes={
        "tasks.etl.*":     {"queue": "etl"},
        "tasks.scoring.*": {"queue": "scoring"},
        "tasks.ml.*":      {"queue": "ml"},
    },

    # Scheduled tasks (Celery Beat = cron-like scheduler)
    beat_schedule={
        # Every night at midnight IST (18:30 UTC), re-score all transformers
        "nightly-full-rescore": {
            "task": "tasks.scoring.score_all_transformers",
            "schedule": crontab(hour=18, minute=30),  # 00:00 IST = 18:30 UTC
        },
        # Every Sunday at 02:00 IST (20:30 UTC Saturday), retrain survival model
        "weekly-survival-retrain": {
            "task": "tasks.ml.retrain_survival_model",
            "schedule": crontab(hour=20, minute=30, day_of_week="saturday"),
        },
        # 30 minutes later: retrain anomaly model
        "weekly-anomaly-retrain": {
            "task": "tasks.ml.retrain_anomaly_model",
            "schedule": crontab(hour=21, minute=0, day_of_week="saturday"),
        },
    },
)
