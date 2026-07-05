import random
import uuid
from typing import List, Dict, Any

class MockAIModel:
    """
    Ek Dummy (Mock) AI Model jo Isolation Forest (Anomaly Detection) aur 
    Survival Analysis (Time-to-failure) ko simulate karega.
    """
    
    def __init__(self):
        # AI Model ko load karne ka logic yahan aayega jab real .pkl files hongi
        self.features = [
            "oil_temperature",
            "winding_temperature",
            "load_current",
            "ambient_temperature",
            "vibration_level"
        ]

    def predict_anomaly(self, transformer_id: str) -> Dict[str, Any]:
        """
        Isolation Forest logic (Simulated).
        Returns risk_score (0-100), risk_category, aur SHAP values.
        """
        # Random risk score between 10 and 95
        base_score = random.uniform(10.0, 95.0)
        
        # Categorize risk
        if base_score > 80:
            category = "CRITICAL"
        elif base_score > 60:
            category = "HIGH"
        elif base_score > 40:
            category = "MEDIUM"
        else:
            category = "LOW"
            
        # Generate dummy SHAP (Explainability) values
        shap_values = []
        remaining_score = base_score / 100.0  # Normalize to 0-1 range for SHAP impact
        
        for feature in self.features:
            # Assign random impact to each feature
            impact = random.uniform(-0.1, 0.4)
            shap_values.append({
                "feature_name": feature,
                "feature_value": round(random.uniform(20.0, 100.0), 2),
                "shap_value": impact
            })
            
        # Survival Analysis (Expected Lifetime remaining in days)
        # Higher risk -> Lower lifetime
        expected_lifetime_days = int((100 - base_score) * 36.5) # Approx up to 10 years
            
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
ai_service = MockAIModel()
