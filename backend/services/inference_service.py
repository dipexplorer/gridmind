"""
GridMind Inference Service
===========================
Single responsibility: coordinate ML scoring for one transformer.

Architecture:
    API Endpoint
        └── crud_intelligence (thin delegation)
                └── InferenceService  ← THIS FILE
                        ├── fetch transformer metadata (DB)
                        ├── fetch live telemetry (data_cache or DB snapshot)
                        ├── call ai_service.predict_anomaly()  (4-model fusion)
                        └── return unified TransformerScoreResult dict

Design decisions:
- No synthetic random sensor generation. If no telemetry is available,
  we fall back to the DB snapshot values (current_oil_temp_c, current_load_pct)
  stored in the transformer row by the daily batch job.
- AI model output is NEVER overwritten with DB values after inference.
  The fusion engine result is the authoritative source.
- Cox PH expected_lifetime_days is used directly — no hardcoded 7/90/365.
- SHAP values are embedded in the score response (real, from predict_anomaly).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _map_status_to_category(status: Optional[str], anomaly_pct: float) -> str:
    """Map raw DB status string to canonical CRITICAL/WARNING/HEALTHY category."""
    s = (status or "").lower()
    if s == "critical":
        return "CRITICAL"
    if s == "warning":
        return "WARNING"
    if s == "healthy":
        return "HEALTHY"
    # Fallback: derive from anomaly score
    if anomaly_pct >= 70:
        return "CRITICAL"
    if anomaly_pct >= 40:
        return "WARNING"
    return "HEALTHY"


class InferenceService:
    """
    Coordinates transformer risk scoring across all ML models.
    Singleton — import via `inference_service` at bottom of this file.
    """

    def score_transformer(self, transformer_id: str, db) -> Optional[dict]:
        """
        Run full 4-model fusion scoring for a single transformer.

        Returns a dict matching TransformerScoreResponse schema, or None
        if the transformer is not found in the database.
        """
        from models.asset import Transformer
        from services.ai_service import ai_service
        from services.data_cache import get_latest_telemetry
        from core.config import settings

        transformer = db.query(Transformer).filter(
            Transformer.id == transformer_id
        ).first()

        if not transformer:
            return None

        # ── 1. Resolve telemetry ─────────────────────────────────────────────
        # Priority: live cache → DB snapshot values
        latest_read = get_latest_telemetry(transformer_id)
        data_source = "live_cache"

        temp_c = None
        load_pct = None
        voltage_lv = None
        current_a = None

        if not latest_read:
            # Fall back to DB snapshot (written by predict_daily_batch.py)
            if (
                transformer.current_oil_temp_c is not None
                and transformer.current_load_pct is not None
            ):
                logger.debug(
                    f"Transformer {transformer_id}: No live telemetry, using DB snapshot."
                )
                data_source = "db_snapshot"
                temp_c = float(transformer.current_oil_temp_c)
                load_pct = float(transformer.current_load_pct)
            else:
                logger.warning(
                    f"Transformer {transformer_id}: No telemetry at all. "
                    "Returning unavailable response."
                )
                return self._no_telemetry_response(transformer_id, transformer)
        else:
            temp_c = float(latest_read["temperature_c"]) if latest_read.get("temperature_c") is not None else None
            load_pct = float(latest_read["load_percentage"]) if latest_read.get("load_percentage") is not None else None
            voltage_lv = float(latest_read["voltage_lv"]) if latest_read.get("voltage_lv") is not None else None
            current_a = float(latest_read["current_a"]) if latest_read.get("current_a") is not None else None

        # Resolve asset specs
        age_years = int(transformer.age_years) if transformer.age_years is not None else 10
        rated_kva = float(transformer.rated_kva) if transformer.rated_kva is not None else 500.0

        # Coordinates
        lat, lon = None, None
        try:
            from geoalchemy2.shape import to_shape
            if transformer.location:
                point = to_shape(transformer.location)
                lat = float(point.y)
                lon = float(point.x)
        except Exception:
            pass

        # ── 2. Run full fusion inference ─────────────────────────────────────
        try:
            pred = ai_service.predict_anomaly(
                transformer_id,
                temp_c=temp_c,
                load_pct=load_pct,
                voltage_lv=voltage_lv,
                current_a=current_a,
                age_years=age_years,
                rated_kva=rated_kva,
                lat=lat,
                lon=lon
            )
        except Exception as e:
            logger.error(
                f"predict_anomaly failed for {transformer_id}: {e}", exc_info=True
            )
            return None

        # ── 3. Build unified response ────────────────────────────────────────
        return {
            # Stable ID keyed to transformer (no random UUID per request)
            "id": f"score_{transformer_id}",
            "transformer_id": transformer_id,
            "run_id": "00000000-0000-0000-0000-000000000000",

            # Primary scoring outputs
            "anomaly_score": pred["anomaly_score"],
            "health_score": pred["health_score"],
            "failure_probability": pred["failure_probability"],
            "risk_category": pred["risk_category"],

            # Cox PH lifetime — real model output, not hardcoded
            "expected_lifetime_days": pred["expected_lifetime_days"],
            "confidence_interval_lower": pred["confidence_interval_lower"],
            "confidence_interval_upper": pred["confidence_interval_upper"],

            "calculated_at": transformer.last_updated or datetime.now(timezone.utc),

            # All 4 model predictions returned independently
            "model_predictions": pred.get("model_predictions", {}),

            # Real SHAP values from Isolation Forest
            "shap_values": pred.get("shap_values", []),

            # Real supervised SHAP from XGBoost/RF
            "xgb_shap_values": pred.get("xgb_shap_values", []),

            # Metadata
            "data_source": data_source,
        }

    def _no_telemetry_response(self, transformer_id: str, transformer) -> dict:
        """
        Returns a structured response when no telemetry is available.
        Does NOT fabricate sensor readings — returns explicit data_available=False.
        """
        return {
            "id": f"score_{transformer_id}",
            "transformer_id": transformer_id,
            "run_id": "00000000-0000-0000-0000-000000000000",
            "anomaly_score": None,
            "health_score": None,
            "failure_probability": None,
            "risk_category": "UNKNOWN",
            "expected_lifetime_days": None,
            "confidence_interval_lower": None,
            "confidence_interval_upper": None,
            "calculated_at": datetime.now(timezone.utc),
            "model_predictions": {},
            "shap_values": [],
            "xgb_shap_values": [],
            "data_source": "unavailable",
        }


# Singleton
inference_service = InferenceService()
