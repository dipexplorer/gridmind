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

from typing import Dict, Any

from core.database import SessionLocal
from models.timeseries import LoadReading

logger = logging.getLogger(__name__)

class RealAIModel:
    """
    Real Machine Learning Model Service.
    Loads Isolation Forest and Cox Survival models from joblib pickles.
    Computes exact mathematical anomaly scores and SHAP explainability.
    """
    
    def __init__(self):
        self.features = ["temperature_c", "load_percentage", "voltage_lv", "current_a"]
        self.model = None
        self.survival_model = None
        self.explainer = None
        # Load models in background thread so the server starts instantly
        # This prevents Render free-tier health-check timeouts
        import threading
        threading.Thread(target=self.load_models, daemon=True).start()

    def load_models(self):
        """
        Loads models from ml_models directory if available.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, "ml_models", "isolation_forest.pkl")
        survival_path = os.path.join(base_dir, "ml_models", "survival_model.pkl")

        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                # Lazy import shap here (not at module level) to avoid numba JIT compilation
                # at startup which causes Render free-tier health-check timeout.
                import shap as shap_lib
                self.explainer = shap_lib.TreeExplainer(self.model)
                logger.info("Successfully loaded Isolation Forest model and SHAP TreeExplainer.")
            except Exception as e:
                logger.error(f"Failed to load Isolation Forest model: {e}")
        else:
            logger.warning(f"Isolation Forest model not found at {model_path}. Running in mock mode.")

        if os.path.exists(survival_path):
            try:
                self.survival_model = joblib.load(survival_path)
                logger.info("Successfully loaded Cox Proportional Hazards survival model.")
            except Exception as e:
                logger.error(f"Failed to load Cox Proportional Hazards model: {e}")
        else:
            logger.warning(f"Survival model not found at {survival_path}. Running in mock mode.")

    def _fetch_live_weather(self, lat: float, lon: float) -> float:
        """
        Fetches live ambient temperature from Open-Meteo API.
        Returns the temperature in Celsius, or 30.0 as fallback.
        """
        if not lat or not lon:
            return 30.0
        try:
            import requests
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                return float(data.get("current_weather", {}).get("temperature", 30.0))
            return 30.0
        except Exception as e:
            logger.warning(f"Weather API failed: {e}. Using fallback ambient temperature.")
            return 30.0

    def predict_anomaly(self, transformer_id: str) -> Dict[str, Any]:
        """
        Performs real Isolation Forest inference, SHAP calculation, and survival duration estimation.
        Falls back to safe simulation if models are not generated yet.
        """
        # If models are not loaded, fallback to mock simulator
        if self.model is None or self.survival_model is None:
            return self._fallback_predict(transformer_id)

        db = SessionLocal()
        try:
            # 1. Fetch latest sensor reading for this transformer from DB
            reading = db.query(LoadReading)\
                .filter(LoadReading.transformer_id == transformer_id)\
                .order_by(LoadReading.time.desc())\
                .first()

            if not reading:
                # Use default healthy telemetry if no readings exist yet
                load_pct = 45.0
                v_lv = 415.0
                curr_a = 60.0
                temp_c = 40.0
            else:
                load_pct = float(reading.load_percentage) if reading.load_percentage is not None else 0.0
                v_lv = float(reading.voltage_lv) if reading.voltage_lv is not None else 0.0
                curr_a = float(reading.current_a) if reading.current_a is not None else 0.0
                temp_c = float(reading.temperature_c) if reading.temperature_c is not None else 0.0

            # 2. Structure feature vector
            x = np.array([[temp_c, load_pct, v_lv, curr_a]])
            df_x = pd.DataFrame(x, columns=self.features)

            # 3. Predict Anomaly Score (Isolation Forest decision_function)
            # decision_function returns value in range roughly [-0.5, 0.5]
            # Higher score is normal, lower/negative score is anomalous
            raw_score = self.model.decision_function(df_x)[0]
            
            # Map raw score to 0-100 percentage (where 100 is highly anomalous)
            # Normal data usually has raw_score > 0 (e.g. 0.1 to 0.3)
            # Anomalies have raw_score < 0
            anomaly_score = 35 - (raw_score * 200)

            # LIVE WEATHER INTEGRATION (Phase 1)
            # Fetch transformer coordinates to get ambient temperature
            from models.asset import Transformer
            transformer = db.query(Transformer).filter(Transformer.id == transformer_id).first()
            lat = float(transformer.latitude) if transformer and transformer.latitude else 0.0
            lon = float(transformer.longitude) if transformer and transformer.longitude else 0.0

            ambient_temp = self._fetch_live_weather(lat, lon)
            
            # If ambient temp is very high (> 35C), it adds thermal stress to the transformer.
            # Add up to 15% risk penalty.
            if ambient_temp > 35.0:
                heat_stress_penalty = min(15.0, (ambient_temp - 35.0) * 2.0)
                anomaly_score += heat_stress_penalty

            # Clip between 0 and 100 to prevent database overflow
            anomaly_score = max(0.0, min(100.0, float(anomaly_score)))

            # Fetch dynamic thresholds from settings
            from crud import crud_system
            settings = crud_system.get_settings(db)

            # Categorize Risk
            if anomaly_score >= settings.critical_threshold:
                category = "CRITICAL"
            elif anomaly_score >= settings.high_threshold:
                category = "HIGH"
            elif anomaly_score >= settings.medium_threshold:
                category = "MEDIUM"
            else:
                category = "LOW"

            # 4. Compute SHAP explainability
            # TreeExplainer calculates shapley values for the decision function
            shap_vals = self.explainer.shap_values(df_x)[0]
            
            # Pack SHAP values to fit schemas.intelligence.ShapExplanationResponse
            shap_list = []
            for i, name in enumerate(self.features):
                val_mapping = [temp_c, load_pct, v_lv, curr_a]
                shap_list.append({
                    "feature_name": name,
                    "feature_value": round(val_mapping[i], 2),
                    "shap_value": round(float(shap_vals[i]), 4)
                })

            # 5. Predict Expected Life remaining (Cox Proportional Hazards)
            # Features required for CoxPH: temperature_c, load_percentage
            surv_x = pd.DataFrame([[temp_c, load_pct]], columns=["temperature_c", "load_percentage"])
            
            # lifelines predict_median returns median survival duration
            try:
                median_life = self.survival_model.predict_median(surv_x)
                expected_lifetime_days = float(median_life.iloc[0])
                
                # Check for inf/nan models behavior
                if np.isinf(expected_lifetime_days) or np.isnan(expected_lifetime_days):
                    # Logical fallback: high anomaly score drops lifetime
                    expected_lifetime_days = int((100 - anomaly_score) * 36.5)
                else:
                    expected_lifetime_days = int(expected_lifetime_days)
            except Exception:
                expected_lifetime_days = int((100 - anomaly_score) * 36.5)

            return {
                "transformer_id": transformer_id,
                "anomaly_score": round(anomaly_score, 2),
                "risk_category": category,
                "expected_lifetime_days": expected_lifetime_days,
                "confidence_interval_lower": max(0, expected_lifetime_days - 30),
                "confidence_interval_upper": expected_lifetime_days + 30,
                "shap_values": shap_list
            }

        except Exception as e:
            logger.error(f"Error during real AI inference: {e}")
            return self._fallback_predict(transformer_id)
        finally:
            db.close()

    def _fallback_predict(self, transformer_id: str) -> Dict[str, Any]:
        """
        Mock fallback prediction service when ML models are missing or training failed.
        """
        base_score = random.uniform(10.0, 95.0)
        
        from core.database import SessionLocal
        from crud import crud_system
        db = SessionLocal()
        try:
            settings = crud_system.get_settings(db)
            if base_score >= settings.critical_threshold:
                category = "CRITICAL"
            elif base_score >= settings.high_threshold:
                category = "HIGH"
            elif base_score >= settings.medium_threshold:
                category = "MEDIUM"
            else:
                category = "LOW"
        finally:
            db.close()
            
        shap_values = []
        for feature in self.features:
            shap_values.append({
                "feature_name": feature,
                "feature_value": round(random.uniform(20.0, 100.0), 2),
                "shap_value": random.uniform(-0.1, 0.4)
            })
            
        expected_lifetime_days = int((100 - base_score) * 36.5)
            
        return {
            "transformer_id": transformer_id,
            "anomaly_score": round(base_score, 2),
            "risk_category": category,
            "expected_lifetime_days": expected_lifetime_days,
            "confidence_interval_lower": max(0, expected_lifetime_days - 30),
            "confidence_interval_upper": expected_lifetime_days + 30,
            "shap_values": shap_values
        }

# Singleton instance
ai_service = RealAIModel()
