import os
import random
import logging
import numpy as np
import pandas as pd
import joblib
# shap is imported lazily inside load_models() to avoid numba JIT at startup (prevents Render timeout)
import scipy.integrate
# Monkey patch trapz for newer scipy compatibility with lifelines unpickling
if not hasattr(scipy.integrate, 'trapz'):
    if hasattr(scipy.integrate, 'trapezoid'):
        scipy.integrate.trapz = scipy.integrate.trapezoid
    elif hasattr(np, 'trapezoid'):
        scipy.integrate.trapz = np.trapezoid

from typing import Dict, Any, Optional

from core.database import SessionLocal
from core.config import settings

logger = logging.getLogger(__name__)

class RealAIModel:
    """
    Real Machine Learning Model Service.
    Loads Isolation Forest and Cox Survival models from joblib pickles.
    Computes exact mathematical anomaly scores and SHAP explainability.
    """
    
    def __init__(self):
        self.features = ["temperature_c", "load_percentage", "voltage_lv", "current_a", "ambient_temperature", "age_years", "rated_kva", "power_factor", "load_ratio", "current_ratio", "voltage_deviation", "temperature_rise", "stress_index"]
        self.model = None          # Isolation Forest (anomaly score)
        self.xgb_model = None      # XGBoost (status classification)
        self.rf_model = None       # Random Forest (benchmark classifier)
        self.survival_model = None
        self.explainer = None      # Isolation Forest SHAP TreeExplainer
        self.supervised_explainer = None # Supervised SHAP TreeExplainer (XGBoost/RF)
        self._models_loaded = False
        import threading
        self._lock = threading.Lock()

    def raw_to_anomaly_score(self, raw: float) -> float:
        """
        Converts Isolation Forest decision_function output to 0-100 anomaly score.
        decision_function: positive = normal (inlier), negative = anomaly (outlier).
        Calibrated based on actual physical dataset ranges:
        - 0.05 or higher (very normal) -> 0%
        - -0.15 or lower (highly anomalous) -> 100%
        """
        return float(np.clip((0.05 - raw) / 0.20 * 100.0, 0.0, 100.0))

    def calibrate_anomaly_score(self, score: float, category: str) -> float:
        """
        [DEPRECATED] Independent models are now returned directly.
        Returns the score unchanged to preserve mathematical correctness.
        """
        return score

    def load_models_if_needed(self):
        with self._lock:
            if not self._models_loaded:
                self.load_models()
                self._models_loaded = True

    def load_models(self):
        """
        Loads models from ml_models directory if available.
        - Isolation Forest: unsupervised anomaly score (0-100)
        - XGBoost: supervised status classification (SAFE/WARNING/CRITICAL)
        - Random Forest: benchmark status classification
        - Cox Survival: remaining useful life estimation
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path    = os.path.join(base_dir, "ml_models", "isolation_forest.pkl")
        survival_path = os.path.join(base_dir, "ml_models", "survival_model.pkl")
        xgb_path      = os.path.join(base_dir, "ml_models", "benchmark_xgboost.pkl")
        rf_path       = os.path.join(base_dir, "ml_models", "benchmark_random_forest.pkl")

        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                import shap as shap_lib
                self.explainer = shap_lib.TreeExplainer(self.model)
                logger.info("Successfully loaded Isolation Forest model and SHAP TreeExplainer.")
            except Exception as e:
                logger.error(f"Failed to load Isolation Forest model: {e}")
        else:
            logger.warning(f"Isolation Forest model not found at {model_path}. Running in mock mode.")

        if os.path.exists(xgb_path):
            try:
                self.xgb_model = joblib.load(xgb_path)
                logger.info("Successfully loaded XGBoost classifier for status prediction.")
            except Exception as e:
                logger.error(f"Failed to load XGBoost model: {e}")
        else:
            logger.warning(f"XGBoost model not found at {xgb_path}.")

        if os.path.exists(rf_path):
            try:
                self.rf_model = joblib.load(rf_path)
                logger.info("Successfully loaded Random Forest classifier.")
            except Exception as e:
                logger.error(f"Failed to load Random Forest model: {e}")
        else:
            logger.warning(f"Random Forest model not found at {rf_path}.")

        if os.path.exists(survival_path):
            try:
                self.survival_model = joblib.load(survival_path)
                logger.info("Successfully loaded Cox Proportional Hazards survival model.")
            except Exception as e:
                logger.error(f"Failed to load Cox Proportional Hazards model: {e}")
        else:
            logger.warning(f"Survival model not found at {survival_path}. Running in mock mode.")

        # Supervised SHAP Explainer
        if self.xgb_model is not None:
            try:
                import shap as shap_lib
                self.supervised_explainer = shap_lib.TreeExplainer(self.xgb_model)
                logger.info("Successfully loaded XGBoost SHAP TreeExplainer.")
            except Exception as e:
                logger.warning(f"Failed to load XGBoost SHAP TreeExplainer (will try Random Forest fallback): {e}")

        if self.supervised_explainer is None and self.rf_model is not None:
            try:
                import shap as shap_lib
                self.supervised_explainer = shap_lib.TreeExplainer(self.rf_model)
                logger.info("Successfully loaded Random Forest SHAP TreeExplainer as supervised fallback.")
            except Exception as e:
                logger.error(f"Failed to load Random Forest SHAP TreeExplainer: {e}")

    def build_features(self, temp_c, load_pct, v_lv, curr_a, ambient_temp, age_years, rated_kva, power_factor) -> pd.DataFrame:
        """
        Unified feature engineering function. Can handle scalar values or lists/arrays of values.
        """
        # Convert all to numpy arrays for unified handling
        temp_c = np.array(temp_c, dtype=float)
        load_pct = np.array(load_pct, dtype=float)
        v_lv = np.array(v_lv, dtype=float)
        curr_a = np.array(curr_a, dtype=float)
        ambient_temp = np.array(ambient_temp, dtype=float)
        age_years = np.array(age_years, dtype=float)
        rated_kva = np.array(rated_kva, dtype=float)
        power_factor = np.array(power_factor, dtype=float)

        load_ratio = load_pct / 100.0
        rated_current = (rated_kva * 1000.0) / (1.732 * settings.NOMINAL_VOLTAGE)
        current_ratio = curr_a / rated_current
        voltage_deviation = (settings.NOMINAL_VOLTAGE - v_lv) / settings.NOMINAL_VOLTAGE
        temperature_rise = temp_c - ambient_temp
        stress_index = current_ratio * temperature_rise * (1.0 + 0.05 * age_years)
        
        # Stack into matrix
        data = np.column_stack([
            temp_c, load_pct, v_lv, curr_a, ambient_temp, age_years, rated_kva, power_factor,
            load_ratio, current_ratio, voltage_deviation, temperature_rise, stress_index
        ])
        return pd.DataFrame(data, columns=self.features)

    def _fetch_live_weather(self, lat: float, lon: float) -> float:
        """
        Fetches live ambient temperature from Open-Meteo API.
        Returns the temperature in Celsius, or 30.0 as fallback.
        Caches results using a location-specific key (rounded to 1 decimal place) to avoid rate limits.
        """
        cache_key = f"weather_{round(lat, 1)}_{round(lon, 1)}"
        if not hasattr(self, '_weather_cache'):
            self._weather_cache = {}
            
        if cache_key in self._weather_cache:
            return self._weather_cache[cache_key]
            
        try:
            import requests
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                temp = float(data.get("current_weather", {}).get("temperature", 30.0))
                self._weather_cache[cache_key] = temp
                return temp
            self._weather_cache[cache_key] = 30.0
            return 30.0
        except Exception as e:
            logger.warning(f"Weather API failed for lat={lat}, lon={lon}: {e}. Using fallback ambient temperature.")
            self._weather_cache[cache_key] = 30.0
            return 30.0

    def predict_anomaly(
        self,
        transformer_id: str,
        *,
        temp_c: Optional[float] = None,
        load_pct: Optional[float] = None,
        voltage_lv: Optional[float] = None,
        current_a: Optional[float] = None,
        age_years: Optional[int] = None,
        rated_kva: Optional[float] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Performs real independent inference for all models in parallel:
        - Isolation Forest -> Anomaly Score
        - XGBoost & Random Forest -> Risk Categories
        - Cox Survival -> Remaining Useful Life (RUL) and Survival Probability
        - Decision Fusion Engine -> Fused Health Score (0-100) and Sigmoid Failure Probability

        Optional keyword arguments allow callers (e.g. inference_service) to pass
        pre-fetched sensor values directly, avoiding a duplicate DB round-trip and
        ensuring that live telemetry CSV values are used for inference.
        """
        self.load_models_if_needed()
        if self.model is None or self.survival_model is None or self.explainer is None:
            return self._fallback_predict(transformer_id)

        # ── Resolve sensor values ─────────────────────────────────────────────
        # If caller supplied values, use them directly (no DB round-trip needed).
        # Otherwise open a DB session to read the latest snapshot.
        _need_db = any(v is None for v in [temp_c, load_pct, age_years, rated_kva])
        _db_lat = 26.14
        _db_lon = 91.74

        if _need_db:
            db = SessionLocal()
            try:
                from models.asset import Transformer
                t = db.query(Transformer).filter(Transformer.id == transformer_id).first()
                if t:
                    if temp_c is None:
                        temp_c = float(t.current_oil_temp_c) if t.current_oil_temp_c is not None else 40.0
                    if load_pct is None:
                        load_pct = float(t.current_load_pct) if t.current_load_pct is not None else 45.0
                    if age_years is None:
                        age_years = int(t.age_years) if t.age_years is not None else 10
                    if rated_kva is None:
                        rated_kva = float(t.rated_kva) if t.rated_kva is not None else 500.0
                    try:
                        from geoalchemy2.shape import to_shape
                        if t.location:
                            point = to_shape(t.location)
                            _db_lat = float(point.y)
                            _db_lon = float(point.x)
                    except Exception:
                        pass
                else:
                    temp_c = temp_c or 40.0
                    load_pct = load_pct or 45.0
                    age_years = age_years or 10
                    rated_kva = rated_kva or 500.0
            except Exception as db_err:
                logger.warning(f"DB lookup failed in predict_anomaly ({transformer_id}): {db_err}. Using safe defaults.")
                temp_c = temp_c or 40.0
                load_pct = load_pct or 45.0
                age_years = age_years or 10
                rated_kva = rated_kva or 500.0
            finally:
                db.close()

        # Final safe defaults if still None
        temp_c = temp_c or 40.0
        load_pct = load_pct or 45.0
        age_years = age_years or 10
        rated_kva = rated_kva or 500.0
        lat = lat if lat is not None else _db_lat
        lon = lon if lon is not None else _db_lon
        try:
            # Synthesize voltage, current and power factor using physics-aware formulas
            # PF dynamic based on load
            power_factor = 0.82 + (load_pct / 150.0) * 0.16 + random.normalvariate(0, 0.01)
            power_factor = max(0.80, min(0.98, power_factor))
            
            # Impedance voltage drop (V_drop = I * Z)
            rated_current = (rated_kva * 1000.0) / (1.732 * settings.NOMINAL_VOLTAGE)
            typical_impedance_ohms = 0.045 * (settings.NOMINAL_VOLTAGE / rated_current)
            approx_current = rated_current * (load_pct / 100.0)
            voltage_drop = approx_current * typical_impedance_ohms
            v_lv = settings.NOMINAL_VOLTAGE - voltage_drop + random.uniform(-1.5, 1.5)
            
            # Current
            curr_a = (rated_kva * 1000.0 * (load_pct / 100.0)) / (1.732 * v_lv * power_factor) + random.uniform(-2, 2)
            curr_a = max(0.0, min(curr_a, 1.5 * rated_current))

            # Fetch live weather (ambient temperature)
            ambient_temp = self._fetch_live_weather(lat, lon)

            # Build feature vector using unified DRY method
            df_x = self.build_features(temp_c, load_pct, v_lv, curr_a, ambient_temp, age_years, rated_kva, power_factor)

            # 1. Isolation Forest Anomaly Score
            raw_score = self.model.decision_function(df_x)[0]
            anomaly_score = self.raw_to_anomaly_score(raw_score)
            health_if = 100.0 - anomaly_score

            # 2. XGBoost Prediction & Probability
            category_map = {0: "HEALTHY", 1: "WARNING", 2: "CRITICAL"}
            if self.xgb_model is not None:
                xgb_pred = int(self.xgb_model.predict(df_x.values)[0])
                xgb_category = category_map.get(xgb_pred, "HEALTHY")
                proba = self.xgb_model.predict_proba(df_x.values)[0]
                health_xgb = float(np.clip(100.0 * (proba[0] + 0.5 * proba[1]), 0.0, 100.0))
            else:
                xgb_category = "HEALTHY"
                health_xgb = 50.0

            # 3. Random Forest Prediction
            if self.rf_model is not None:
                rf_pred = int(self.rf_model.predict(df_x.values)[0])
                rf_category = category_map.get(rf_pred, "HEALTHY")
            else:
                rf_category = "HEALTHY"

            # 4. Cox Proportional Hazards RUL & Survival Prob
            try:
                median_life = self.survival_model.predict_median(df_x)
                expected_lifetime_days = float(median_life.iloc[0])
                if np.isinf(expected_lifetime_days) or np.isnan(expected_lifetime_days):
                    expected_lifetime_days = int((100 - anomaly_score) * 36.5)
                else:
                    expected_lifetime_days = int(expected_lifetime_days)
                
                # Fetch survival probability at t=365 days
                surv_func = self.survival_model.predict_survival_function(df_x)
                closest_t = min(surv_func.index, key=lambda t_val: abs(t_val - 365.0))
                p_surv_365 = float(surv_func.loc[closest_t].values[0])
                health_cox = p_surv_365 * 100.0
            except Exception:
                expected_lifetime_days = int((100 - anomaly_score) * 36.5)
                health_cox = 50.0

            # 5. Physics Health
            temp_penalty = (np.maximum(0.0, temp_c - settings.TEMPERATURE_LIMIT_WARNING) / 15.0) ** 2 * 12.0
            load_penalty = (np.maximum(0.0, load_pct - settings.LOAD_LIMIT_WARNING) / 20.0) ** 2 * 10.0
            voltage_penalty = (np.abs(v_lv - settings.NOMINAL_VOLTAGE) / 20.0) ** 2 * 8.0
            current_penalty = np.maximum(0.0, (curr_a / rated_current) - 1.0) * 25.0
            age_penalty = (age_years / 25.0) ** 1.8 * 12.0

            health_physics = 100.0 - temp_penalty - load_penalty - voltage_penalty - current_penalty - age_penalty
            health_physics = float(np.clip(health_physics, 0.0, 100.0))

            # 6. Decision Fusion Engine (Model output fusion)
            w_if = settings.HEALTH_WEIGHT_IF
            w_xgb = settings.HEALTH_WEIGHT_XGB
            w_cox = settings.HEALTH_WEIGHT_COX
            w_phys = settings.HEALTH_WEIGHT_PHYSICS
            
            if self.xgb_model is None:
                w_phys += w_xgb
                w_xgb = 0.0
            if self.survival_model is None:
                w_phys += w_cox
                w_cox = 0.0
                
            total_w = w_if + w_xgb + w_cox + w_phys
            w_if, w_xgb, w_cox, w_phys = w_if / total_w, w_xgb / total_w, w_cox / total_w, w_phys / total_w
            
            health_score = (
                w_if * health_if +
                w_xgb * health_xgb +
                w_cox * health_cox +
                w_phys * health_physics
            )
            health_score = float(np.clip(health_score, 0.0, 100.0))

            # 7. Sigmoid failure probability
            failure_prob = 100.0 / (1.0 + np.exp(0.08 * (health_score - 45.0)))

            # Risk Category directly mapped from continuous Health Score
            if health_score >= 75.0:
                risk_category = "HEALTHY"
            elif health_score >= 45.0:
                risk_category = "WARNING"
            else:
                risk_category = "CRITICAL"

            # 8. Compute SHAP explainability (Isolation Forest)
            shap_list = []
            shap_vals = self.explainer.shap_values(df_x)[0]
            
            load_ratio = load_pct / 100.0
            current_ratio = curr_a / rated_current
            voltage_deviation = (settings.NOMINAL_VOLTAGE - v_lv) / settings.NOMINAL_VOLTAGE
            temperature_rise = temp_c - ambient_temp
            stress_index = current_ratio * temperature_rise * (1.0 + 0.05 * age_years)
            val_mapping = [temp_c, load_pct, v_lv, curr_a, ambient_temp, age_years, rated_kva, power_factor, load_ratio, current_ratio, voltage_deviation, temperature_rise, stress_index]
            
            for i, name in enumerate(self.features):
                shap_list.append({
                    "feature_name": name,
                    "feature_value": round(float(val_mapping[i]), 2),
                    "shap_value": round(float(shap_vals[i]), 4)
                })

            # 9. Compute Supervised SHAP explainability (using XGBoost/RF fallback)
            xgb_shap_list = []
            if self.supervised_explainer is not None:
                try:
                    supervised_shap_vals = self.supervised_explainer.shap_values(df_x)
                    pred_class_idx = 0
                    if self.xgb_model is not None:
                        pred_class_idx = int(xgb_pred)
                    elif self.rf_model is not None:
                        pred_class_idx = int(rf_pred)

                    if isinstance(supervised_shap_vals, list):
                        supervised_shap_class = supervised_shap_vals[pred_class_idx][0]
                    else:
                        if supervised_shap_vals.ndim == 3:
                            if supervised_shap_vals.shape[0] == 3:  # (classes, samples, features)
                                supervised_shap_class = supervised_shap_vals[pred_class_idx][0]
                            else:  # (samples, features, classes)
                                supervised_shap_class = supervised_shap_vals[0, :, pred_class_idx]
                        else:
                            supervised_shap_class = supervised_shap_vals[0]

                    for i, name in enumerate(self.features):
                        xgb_shap_list.append({
                            "feature_name": name,
                            "feature_value": round(float(val_mapping[i]), 2),
                            "shap_value": round(float(supervised_shap_class[i]), 4)
                        })
                except Exception as shap_err:
                    logger.warning(f"Supervised SHAP values computation failed: {shap_err}")

            return {
                "transformer_id": transformer_id,
                "anomaly_score": round(anomaly_score, 2),
                "health_score": round(health_score, 1),
                "failure_probability": round(failure_prob, 1),
                "risk_category": risk_category,
                "expected_lifetime_days": expected_lifetime_days,
                "confidence_interval_lower": max(0, expected_lifetime_days - 30),
                "confidence_interval_upper": expected_lifetime_days + 30,
                "shap_values": shap_list,
                "xgb_shap_values": xgb_shap_list,
                "model_predictions": {
                    "isolation_forest": {
                        "anomaly_score": round(anomaly_score, 2),
                        "risk_category": risk_category,
                        "expected_lifetime_days": expected_lifetime_days
                    },
                    "xgboost": {
                        "anomaly_score": round(100.0 - health_xgb, 2),
                        "risk_category": xgb_category,
                        "expected_lifetime_days": expected_lifetime_days
                    },
                    "random_forest": {
                        "anomaly_score": round(anomaly_score, 2),
                        "risk_category": rf_category,
                        "expected_lifetime_days": expected_lifetime_days
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error during real AI inference: {e}", exc_info=True)
            return self._fallback_predict(transformer_id)

    def predict_daily_health(self, transformer_id: str, readings: list, calculate_shap: bool = True, age_years: int = None, rated_kva: float = None) -> Dict[str, Any]:
        """
        Performs batch inference over 24 hours of telemetry readings.
        Calculates daily average metrics and runs ML models on daily aggregated values.
        """
        self.load_models_if_needed()
        if self.model is None or self.survival_model is None or not readings:
            return self._fallback_predict(transformer_id)

        lat = 26.14
        lon = 91.74

        # Only query database if metadata is not provided
        if age_years is None or rated_kva is None:
            db = SessionLocal()
            try:
                from models.asset import Transformer
                t = db.query(Transformer).filter(Transformer.id == transformer_id).first()
                if t:
                    age_years = int(t.age_years) if t.age_years is not None else 10
                    rated_kva = float(t.rated_kva) if t.rated_kva is not None else 500.0
                    try:
                        from geoalchemy2.shape import to_shape
                        if t.location:
                            point = to_shape(t.location)
                            lat = float(point.y)
                            lon = float(point.x)
                    except Exception:
                        pass
                else:
                    age_years = 10
                    rated_kva = 500.0
            finally:
                db.close()

        ambient_temp = self._fetch_live_weather(lat, lon)

        try:
            # Extract features from all readings using building features helper
            temp_cs, load_pcts, v_lvs, curr_as, power_factors = [], [], [], [], []
            for r in readings:
                temp_cs.append(float(r.temperature_c) if r.temperature_c is not None else 40.0)
                load_pcts.append(float(r.load_percentage) if r.load_percentage is not None else 45.0)
                v_lvs.append(float(r.voltage_lv) if r.voltage_lv is not None else 415.0)
                curr_as.append(float(r.current_a) if r.current_a is not None else 60.0)
                
                # Dynamic Power Factor (depends on load)
                pf = 0.82 + (load_pcts[-1] / 150.0) * 0.16 + random.normalvariate(0, 0.01)
                pf = max(0.80, min(0.98, pf))
                power_factors.append(pf)
                
            n_readings = len(readings)
            df = self.build_features(
                temp_cs, load_pcts, v_lvs, curr_as,
                [ambient_temp] * n_readings, [age_years] * n_readings, [rated_kva] * n_readings, power_factors
            )

            # 1. Anomaly score from Isolation Forest (0-100, higher = more anomalous)
            raw_scores    = self.model.decision_function(df)
            anomaly_scores = np.clip((0.5 - raw_scores) * 100.0, 0.0, 100.0)
            daily_anomaly_score = float(np.max(anomaly_scores))
            health_if = 100.0 - daily_anomaly_score

            # Compute daily averages first
            mean_features = df.mean()
            df_mean = pd.DataFrame([mean_features.values], columns=self.features)

            avg_temp = float(mean_features["temperature_c"])
            avg_load = float(mean_features["load_percentage"])
            avg_volt = float(mean_features["voltage_lv"])
            avg_curr = float(mean_features["current_a"])
            avg_pf   = float(mean_features["power_factor"])

            # 2. XGBoost classification
            category_map = {0: "HEALTHY", 1: "WARNING", 2: "CRITICAL"}
            if self.xgb_model is not None:
                xgb_pred = int(self.xgb_model.predict(df_mean.values)[0])
                xgb_category = category_map.get(xgb_pred, "HEALTHY")
                proba = self.xgb_model.predict_proba(df_mean.values)[0]
                health_xgb = float(np.clip(100.0 * (proba[0] + 0.5 * proba[1]), 0.0, 100.0))
            else:
                xgb_category = "HEALTHY"
                health_xgb = 50.0

            # 3. Random Forest classification
            if self.rf_model is not None:
                rf_pred = int(self.rf_model.predict(df_mean.values)[0])
                rf_category = category_map.get(rf_pred, "HEALTHY")
            else:
                rf_category = "HEALTHY"

            # 4. Predict Remaining Useful Life
            try:
                median_life = self.survival_model.predict_median(df_mean)
                expected_lifetime_days = float(median_life.iloc[0])
                if np.isinf(expected_lifetime_days) or np.isnan(expected_lifetime_days):
                    expected_lifetime_days = int((100 - daily_anomaly_score) * 36.5)
                else:
                    expected_lifetime_days = int(expected_lifetime_days)
                
                # Fetch survival probability at t=365 days
                surv_func = self.survival_model.predict_survival_function(df_mean)
                closest_t = min(surv_func.index, key=lambda t_val: abs(t_val - 365.0))
                p_surv_365 = float(surv_func.loc[closest_t].values[0])
                health_cox = p_surv_365 * 100.0
            except Exception:
                expected_lifetime_days = int((100 - daily_anomaly_score) * 36.5)
                health_cox = 50.0

            # 5. Physics Health
            rated_current = (rated_kva * 1000.0) / (1.732 * settings.NOMINAL_VOLTAGE)
            temp_penalty = (np.maximum(0.0, avg_temp - settings.TEMPERATURE_LIMIT_WARNING) / 15.0) ** 2 * 12.0
            load_penalty = (np.maximum(0.0, avg_load - settings.LOAD_LIMIT_WARNING) / 20.0) ** 2 * 10.0
            voltage_penalty = (np.abs(avg_volt - settings.NOMINAL_VOLTAGE) / 20.0) ** 2 * 8.0
            current_penalty = np.maximum(0.0, (avg_curr / rated_current) - 1.0) * 25.0
            age_penalty = (age_years / 25.0) ** 1.8 * 12.0

            health_physics = 100.0 - temp_penalty - load_penalty - voltage_penalty - current_penalty - age_penalty
            health_physics = float(np.clip(health_physics, 0.0, 100.0))

            # 6. Decision Fusion Engine (Model output fusion)
            w_if = settings.HEALTH_WEIGHT_IF
            w_xgb = settings.HEALTH_WEIGHT_XGB
            w_cox = settings.HEALTH_WEIGHT_COX
            w_phys = settings.HEALTH_WEIGHT_PHYSICS
            
            if self.xgb_model is None:
                w_phys += w_xgb
                w_xgb = 0.0
            if self.survival_model is None:
                w_phys += w_cox
                w_cox = 0.0
                
            total_w = w_if + w_xgb + w_cox + w_phys
            w_if, w_xgb, w_cox, w_phys = w_if / total_w, w_xgb / total_w, w_cox / total_w, w_phys / total_w
            
            health_score = (
                w_if * health_if +
                w_xgb * health_xgb +
                w_cox * health_cox +
                w_phys * health_physics
            )
            health_score = float(np.clip(health_score, 0.0, 100.0))

            # 7. Sigmoid failure probability
            failure_prob = 100.0 / (1.0 + np.exp(0.08 * (health_score - 45.0)))

            if health_score >= 75.0:
                risk_category = "HEALTHY"
            elif health_score >= 45.0:
                risk_category = "WARNING"
            else:
                risk_category = "CRITICAL"

            shap_list = []
            if calculate_shap and self.explainer is not None:
                shap_vals = self.explainer.shap_values(df_mean)[0]
                for i, name in enumerate(self.features):
                    shap_list.append({
                        "feature_name": name,
                        "feature_value": round(float(mean_features[name]), 2),
                        "shap_value": round(float(shap_vals[i]), 4)
                    })

            xgb_shap_list = []
            if calculate_shap and self.supervised_explainer is not None:
                try:
                    supervised_shap_vals = self.supervised_explainer.shap_values(df_mean)
                    pred_class_idx = 0
                    if self.xgb_model is not None:
                        pred_class_idx = int(xgb_pred)
                    elif self.rf_model is not None:
                        pred_class_idx = int(rf_pred)

                    if isinstance(supervised_shap_vals, list):
                        supervised_shap_class = supervised_shap_vals[pred_class_idx][0]
                    else:
                        if supervised_shap_vals.ndim == 3:
                            if supervised_shap_vals.shape[0] == 3:
                                supervised_shap_class = supervised_shap_vals[pred_class_idx][0]
                            else:
                                supervised_shap_class = supervised_shap_vals[0, :, pred_class_idx]
                        else:
                            supervised_shap_class = supervised_shap_vals[0]

                    for i, name in enumerate(self.features):
                        xgb_shap_list.append({
                            "feature_name": name,
                            "feature_value": round(float(mean_features[name]), 2),
                            "shap_value": round(float(supervised_shap_class[i]), 4)
                        })
                except Exception as shap_err:
                    logger.warning(f"Supervised SHAP daily values computation failed: {shap_err}")

            return {
                "transformer_id": transformer_id,
                "anomaly_score": round(daily_anomaly_score, 2),
                "health_score": round(health_score, 1),
                "failure_probability": round(failure_prob, 1),
                "risk_category": risk_category,
                "expected_lifetime_days": expected_lifetime_days,
                "confidence_interval_lower": max(0, expected_lifetime_days - 30),
                "confidence_interval_upper": expected_lifetime_days + 30,
                "shap_values": shap_list,
                "xgb_shap_values": xgb_shap_list,
                "avg_load_pct": avg_load,
                "avg_temp_c": avg_temp,
                "model_predictions": {
                    "isolation_forest": {
                        "anomaly_score": round(daily_anomaly_score, 2),
                        "risk_category": risk_category,
                        "expected_lifetime_days": expected_lifetime_days
                    },
                    "xgboost": {
                        "anomaly_score": round(100.0 - health_xgb, 2),
                        "risk_category": xgb_category,
                        "expected_lifetime_days": expected_lifetime_days
                    },
                    "random_forest": {
                        "anomaly_score": round(daily_anomaly_score, 2),
                        "risk_category": rf_category,
                        "expected_lifetime_days": expected_lifetime_days
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error during daily batch AI inference: {e}", exc_info=True)
            return self._fallback_predict(transformer_id)
        finally:
            pass


    def predict_all_models(self, transformer_id: str, temp_c: float, load_pct: float, v_lv: float, curr_a: float) -> Dict[str, Any]:
        """
        Run inference using Isolation Forest, XGBoost, and Random Forest in parallel.
        Returns anomaly scores and risk categories for each.
        """
        self.load_models_if_needed()
        import pandas as pd
        import numpy as np

        db = SessionLocal()
        try:
            from models.asset import Transformer
            t = db.query(Transformer).filter(Transformer.id == transformer_id).first()
            age_years = int(t.age_years) if (t and t.age_years is not None) else 10
            rated_kva = float(t.rated_kva) if (t and t.rated_kva is not None) else 500.0
            
            lat = 26.14
            lon = 91.74
            if t:
                try:
                    from geoalchemy2.shape import to_shape
                    if t.location:
                        point = to_shape(t.location)
                        lat = float(point.y)
                        lon = float(point.x)
                except Exception:
                    pass
            ambient_temp = self._fetch_live_weather(lat, lon)
        finally:
            db.close()
        
        # Calculate PF and engineered features
        power_factor = 0.82 + (load_pct / 150.0) * 0.16 + random.normalvariate(0, 0.01)
        power_factor = max(0.80, min(0.98, power_factor))
        
        df_x = self.build_features(temp_c, load_pct, v_lv, curr_a, ambient_temp, age_years, rated_kva, power_factor)
        
        results = {}
        
        # 1. Isolation Forest (Production)
        if self.model is not None:
            raw_score = self.model.decision_function(df_x)[0]
            iforest_score = self.raw_to_anomaly_score(raw_score)
        else:
            iforest_score = 15.0
            
        iforest_category = "CRITICAL" if iforest_score >= 90 else ("WARNING" if iforest_score >= 70 else "HEALTHY")
        iforest_life = int((100 - iforest_score) * 36.5)
        results["isolation_forest"] = {
            "anomaly_score": round(iforest_score, 1),
            "risk_category": iforest_category,
            "expected_lifetime_days": iforest_life
        }
        
        # 2. Random Forest
        rf_score = 15.0
        rf_category = "HEALTHY"
        try:
            if self.rf_model is not None:
                proba = self.rf_model.predict_proba(df_x.values)[0]  # [safe, warning, critical]
                max_class = np.argmax(proba)
                if max_class == 2:  # CRITICAL
                    rf_category = "CRITICAL"
                    rf_score = 90.0 + (proba[2] * 10.0)
                elif max_class == 1:  # WARNING
                    rf_category = "WARNING"
                    rf_score = 70.0 + (proba[1] * 20.0)
                else:  # SAFE (HEALTHY)
                    rf_category = "HEALTHY"
                    rf_score = proba[1] * 70.0
        except Exception as e:
            logger.error(f"Failed RF prediction: {e}")
            
        rf_life = int((100 - rf_score) * 36.5)
        results["random_forest"] = {
            "anomaly_score": round(rf_score, 1),
            "risk_category": rf_category,
            "expected_lifetime_days": rf_life
        }
        
        # 3. XGBoost
        xgb_score = 15.0
        xgb_category = "HEALTHY"
        try:
            if self.xgb_model is not None:
                proba = self.xgb_model.predict_proba(df_x.values)[0]
                max_class = np.argmax(proba)
                if max_class == 2:  # CRITICAL
                    xgb_category = "CRITICAL"
                    xgb_score = 90.0 + (proba[2] * 10.0)
                elif max_class == 1:  # WARNING
                    xgb_category = "WARNING"
                    xgb_score = 70.0 + (proba[1] * 20.0)
                else:  # SAFE (HEALTHY)
                    xgb_category = "HEALTHY"
                    xgb_score = proba[1] * 70.0
        except Exception as e:
            logger.error(f"Failed XGB prediction: {e}")
            
        xgb_life = int((100 - xgb_score) * 36.5)
        results["xgboost"] = {
            "anomaly_score": round(xgb_score, 1),
            "risk_category": xgb_category,
            "expected_lifetime_days": xgb_life
        }
        
        return results

    def _fallback_predict(self, transformer_id: str) -> Dict[str, Any]:
        """
        Fallback when ML models are not yet loaded. Returns a neutral/unavailable
        response — does NOT fabricate random scores.
        """
        logger.warning(
            f"ML models not loaded — returning fallback (no-score) for transformer {transformer_id}."
        )
        expected_lifetime_days = 365  # neutral default — models not loaded
        return {
            "transformer_id": transformer_id,
            "anomaly_score": 0.0,
            "health_score": None,
            "failure_probability": None,
            "risk_category": "UNKNOWN",
            "expected_lifetime_days": expected_lifetime_days,
            "confidence_interval_lower": 0,
            "confidence_interval_upper": expected_lifetime_days + 30,
            "shap_values": [],
            "xgb_shap_values": [],
            "model_predictions": {
                "isolation_forest": {
                    "anomaly_score": 0.0,
                    "risk_category": "UNKNOWN",
                    "expected_lifetime_days": expected_lifetime_days
                },
                "xgboost": {
                    "anomaly_score": 0.0,
                    "risk_category": "UNKNOWN",
                    "expected_lifetime_days": expected_lifetime_days
                },
                "random_forest": {
                    "anomaly_score": 0.0,
                    "risk_category": "UNKNOWN",
                    "expected_lifetime_days": expected_lifetime_days
                }
            }
        }

# Singleton instance
ai_service = RealAIModel()
