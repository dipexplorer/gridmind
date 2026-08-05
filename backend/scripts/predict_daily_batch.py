"""
GridMind 24-Hour Batch Prediction Script
=========================================
Runs a daily evaluation cycle for all transformers:
1. Loads cached telemetry (SCADA readings from CSV cache).
2. Validates each reading — rejects physically impossible sensor values.
3. Runs batch ML inference: Isolation Forest + XGBoost + Random Forest + Cox PH.
4. Updates `transformers` table with daily aggregated health, status, failure risk.

Run manually or via Celery/cron scheduler to keep dashboard status current.

NOTE: Score and SHAP persistence to a scores table is not yet implemented.
      If needed, add an SQLAlchemy write inside the per-transformer loop.
"""

import os
import sys
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import settings
from core.database import SessionLocal
from models.asset import Transformer
from models.ticket import MaintenanceTicket  # noqa: F401 — needed for Base metadata
from services.ai_service import ai_service
from services.data_cache import load_data_caches, get_telemetry_history
from crud.crud_ticket import create_ticket, open_ticket_exists
from schemas.ticket import TicketCreate

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DailyBatchPredictor")


@dataclass
class TelemetryReading:
    """Single SCADA sensor snapshot for one time-step."""
    temperature_c: float
    load_percentage: float
    voltage_lv: float
    current_a: float


def _validate_reading(r: TelemetryReading, transformer_code: str) -> bool:
    """
    Rejects physically impossible sensor readings.
    Returns True if reading is valid, False if it should be discarded.
    """
    if not (settings.TEMP_MIN_VALID <= r.temperature_c <= settings.TEMP_MAX_VALID):
        logger.warning(
            f"[{transformer_code}] Invalid temperature {r.temperature_c}°C — skipping reading."
        )
        return False
    if not (settings.VOLTAGE_MIN_VALID <= r.voltage_lv <= settings.VOLTAGE_MAX_VALID):
        logger.warning(
            f"[{transformer_code}] Invalid voltage {r.voltage_lv}V — skipping reading."
        )
        return False
    if not (settings.CURRENT_MIN_VALID <= r.current_a <= settings.CURRENT_MAX_VALID):
        logger.warning(
            f"[{transformer_code}] Invalid current {r.current_a}A — skipping reading."
        )
        return False
    if not (settings.LOAD_MIN_VALID <= r.load_percentage <= settings.LOAD_MAX_VALID):
        logger.warning(
            f"[{transformer_code}] Invalid load {r.load_percentage}% — skipping reading."
        )
        return False
    return True


def _parse_telemetry(history_df, transformer_code: str) -> Optional[List[TelemetryReading]]:
    """
    Converts raw telemetry DataFrame rows into validated TelemetryReading objects.

    Returns:
        List of valid readings, or None if no telemetry available at all.
        Never invents synthetic sensor data.
    """
    if history_df.empty:
        return None

    readings = []
    for _, row in history_df.iterrows():
        r = TelemetryReading(
            temperature_c=float(row["temperature_c"]),
            load_percentage=float(row["load_percentage"]),
            voltage_lv=float(row["voltage_lv"]),
            current_a=float(row["current_a"]),
        )
        if _validate_reading(r, transformer_code):
            readings.append(r)

    if not readings:
        logger.warning(
            f"[{transformer_code}] All telemetry readings failed validation. "
            "Skipping prediction."
        )
        return None

    return readings


def run_batch_prediction():
    db = SessionLocal()
    try:
        logger.info("Loading telemetry cache from telemetry_history.csv...")
        load_data_caches()

        logger.info("Initializing Daily Batch ML Prediction Run...")

        # Load all transformers into memory (completely safe for current fleet size)
        transformer_query = db.query(Transformer).all()

        anomalies_detected = 0
        updated_count = 0
        skipped_count = 0
        tickets_created = 0

        for idx, t in enumerate(transformer_query):
            try:
                # ── 1. Load and validate telemetry ──────────────────────────
                history_df = get_telemetry_history(str(t.id))
                readings = _parse_telemetry(history_df, t.transformer_code or str(t.id))

                if readings is None:
                    # No valid telemetry → no prediction.
                    # DB values from a previous batch run are left unchanged.
                    logger.info(
                        f"[{t.transformer_code}] Skipping — no valid telemetry available."
                    )
                    skipped_count += 1
                    continue

                # ── 2. Run batch ML inference (all 4 models) ─────────────────
                # predict_daily_health() runs:
                #   - Isolation Forest (anomaly score)
                #   - XGBoost (risk category + probability)
                #   - Random Forest (risk category)
                #   - Cox PH (remaining useful life)
                #   - Decision Fusion Engine (health score)
                pred = ai_service.predict_daily_health(
                    str(t.id),
                    readings,
                    calculate_shap=False,
                    age_years=int(t.age_years) if t.age_years is not None
                              else settings.DEFAULT_AGE_YEARS,
                    rated_kva=float(t.rated_kva) if t.rated_kva is not None
                              else settings.DEFAULT_RATED_KVA,
                )

                # ── 3. Extract and validate required fields ─────────────────
                health_score = pred.get("health_score")
                failure_prob = pred.get("failure_probability")
                risk_category = pred.get("risk_category")

                if health_score is None or failure_prob is None or risk_category is None:
                    logger.error(
                        f"[{t.transformer_code}] AI service returned incomplete prediction. "
                        f"Pred keys: {list(pred.keys())}. Skipping DB update."
                    )
                    skipped_count += 1
                    continue

                # ── 4. Write to DB ───────────────────────────────────────────
                # failure_probability comes from the Sigmoid mapping (0-100),
                # stored as fraction (0.0-1.0) in the DB column.
                t.current_failure_risk = float(failure_prob) / 100.0
                t.current_health_score = int(health_score)
                t.current_status = risk_category.lower()
                t.current_load_pct = pred.get("avg_load_pct", t.current_load_pct)
                t.current_oil_temp_c = pred.get("avg_temp_c", t.current_oil_temp_c)
                t.last_updated = datetime.now(timezone.utc)

                if risk_category in ("WARNING", "CRITICAL"):
                    anomalies_detected += 1

                # ── 5. Auto-create maintenance ticket if needed ──────────────
                # One open ticket per transformer per priority level.
                # dedup_key prevents duplicates across batch runs.
                if risk_category == "CRITICAL":
                    priority = "CRITICAL"
                    dedup_key = f"AUTO:CRITICAL:{t.id}"
                    desc = (
                        f"Transformer {t.transformer_code} is in CRITICAL condition "
                        f"(Health Score: {int(health_score)}/100, "
                        f"Failure Risk: {round(float(failure_prob), 1)}%). "
                        "Immediate inspection and intervention required."
                    )
                elif risk_category == "WARNING":
                    priority = "HIGH"
                    dedup_key = f"AUTO:HIGH:{t.id}"
                    desc = (
                        f"Transformer {t.transformer_code} has entered WARNING status "
                        f"(Health Score: {int(health_score)}/100). "
                        "Schedule a maintenance check."
                    )
                else:
                    priority = None
                    dedup_key = None
                    desc = None

                if priority and dedup_key and not open_ticket_exists(db, dedup_key):
                    ticket = create_ticket(db, TicketCreate(
                        transformer_id=str(t.id),
                        priority=priority,
                        description=desc,
                        trigger_type="AUTO",
                        health_score=float(health_score),
                        dedup_key=dedup_key,
                    ))
                    if ticket:
                        tickets_created += 1
                        logger.info(
                            f"[{t.transformer_code}] Auto-ticket created "
                            f"(priority={priority}, score={int(health_score)})"
                        )

                updated_count += 1

                # ── 5. Periodic commit ───────────────────────────────────────
                # commit() inside the loop means each batch is independently
                # durable. A later failure won't roll back already-saved rows.
                if (idx + 1) % settings.BATCH_COMMIT_EVERY == 0:
                    db.commit()
                    logger.info(
                        f"Processed {idx + 1} transformers — "
                        f"{updated_count} updated, {skipped_count} skipped so far..."
                    )

            except Exception as tr_err:
                logger.error(
                    f"[{t.transformer_code}] Failed to process transformer: {tr_err}",
                    exc_info=True
                )
                # Note: rollback only affects uncommitted rows since the last commit().
                db.rollback()

        # Final commit for remaining rows
        db.commit()

        logger.info(
            f"Daily batch run complete. "
            f"Updated: {updated_count} | Skipped: {skipped_count} | "
            f"Anomalies: {anomalies_detected} | Tickets created: {tickets_created}"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Fatal error during batch prediction: {e}", exc_info=True)
    finally:
        db.close()


if __name__ == "__main__":
    run_batch_prediction()
