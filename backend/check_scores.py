from core.database import SessionLocal
from models.asset import Transformer
from services.ai_service import ai_service
import random

db = SessionLocal()
transformers = db.query(Transformer).limit(20).all()
ambient_temp = 30.0

for t in transformers:
    # normal
    readings_normal = []
    for h in range(24):
        temp_offset = random.uniform(5, 12) if 11 <= h <= 16 else random.uniform(0, 4)
        temp = ambient_temp + temp_offset
        load = random.uniform(85, 115) if 18 <= h <= 22 else random.uniform(40, 75)
        voltage = 400.0
        current = 100.0
        
        class ReadingNormal:
            temperature_c = temp
            load_percentage = load
            voltage_lv = voltage
            current_a = current
        readings_normal.append(ReadingNormal())
        
    pred_normal = ai_service.predict_daily_health(str(t.id), readings_normal, calculate_shap=False)
    
    # anomalous
    readings_anom = []
    for h in range(24):
        temp = ambient_temp + random.uniform(50, 75)
        load = random.uniform(105, 135)
        voltage = 360.0
        current = 200.0
        
        class ReadingAnom:
            temperature_c = temp
            load_percentage = load
            voltage_lv = voltage
            current_a = current
        readings_anom.append(ReadingAnom())
        
    pred_anom = ai_service.predict_daily_health(str(t.id), readings_anom, calculate_shap=False)
    
    print(f"Normal score: {pred_normal['anomaly_score']} | Anomalous score: {pred_anom['anomaly_score']}")
db.close()
