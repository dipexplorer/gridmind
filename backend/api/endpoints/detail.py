from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid
import random

from core.database import get_db
from models.asset import Transformer, Substation, Feeder
from models.event import MaintenanceLog
from schemas.detail import LoadReadingResponse, MaintenanceLogResponse, MaintenanceLogCreate
from schemas.asset import TransformerResponse

router = APIRouter()

@router.get("/transformers/{id}/detail", response_model=Dict[str, Any])
def get_transformer_detail(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch comprehensive transformer details including Feeder and Substation names.
    """
    tx = db.query(Transformer).filter(Transformer.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transformer not found")
        
    feeder = db.query(Feeder).filter(Feeder.id == tx.feeder_id).first()
    substation = db.query(Substation).filter(Substation.id == tx.substation_id).first()
    
    # Convert location from PostGIS geometry using Shapely
    location_str = None
    if tx.location is not None:
        try:
            from geoalchemy2.shape import to_shape
            shape = to_shape(tx.location)
            location_str = f"POINT({shape.x} {shape.y})"
        except Exception:
            pass

    return {
        "id": tx.id,
        "transformer_code": tx.transformer_code,
        "rated_kva": tx.rated_kva,
        "voltage_hv_kv": tx.voltage_hv_kv,
        "voltage_lv_v": tx.voltage_lv_v,
        "installation_type": tx.installation_type,
        "cooling_type": tx.cooling_type,
        "manufacturer": tx.manufacturer,
        "address_text": tx.address_text,
        "district": tx.district,
        "is_flood_prone": tx.is_flood_prone,
        "is_high_lightning": tx.is_high_lightning,
        "installation_date": tx.installation_date,
        "operational_status": tx.operational_status,
        "location": location_str,
        "feeder_name": feeder.name if feeder else "Unknown Feeder",
        "substation_name": substation.name if substation else "Unknown Substation"
    }

@router.get("/transformers/{id}/timeseries", response_model=List[Dict[str, Any]])
def get_transformer_timeseries(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Generate latest 24 load and temperature readings for a transformer.
    Reads from the memory-cached telemetry dataset with a dynamic simulation fallback.
    """
    tx = db.query(Transformer).filter(Transformer.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transformer not found")

    from services.data_cache import get_telemetry_history
    history_df = get_telemetry_history(str(id))
    
    if not history_df.empty:
        readings = []
        for _, row in history_df.iterrows():
            readings.append({
                "id": str(uuid.uuid4()),
                "transformer_id": str(id),
                "time": row["timestamp"],
                "load_percentage": float(row["load_percentage"]),
                "voltage_lv": float(row["voltage_lv"]),
                "current_a": float(row["current_a"]),
                "temperature_c": float(row["temperature_c"]),
                "source": "STATIC_CSV"
            })
        return readings

    # Fallback to simulation if cache is empty
    from services.ai_service import ai_service
    lat = 26.14
    lon = 91.74
    try:
        from geoalchemy2.shape import to_shape
        if tx.location:
            point = to_shape(tx.location)
            lat = float(point.y)
            lon = float(point.x)
    except Exception:
        pass
    ambient_temp = ai_service._fetch_live_weather(lat, lon)

    from datetime import datetime, timezone, timedelta
    import random
    
    now = datetime.now(timezone.utc)
    readings = []
    
    status = (tx.current_status or "").lower()
    is_critical = status == "critical"
    is_warning = status == "warning"
    
    for h in range(24):
        time_pt = now - timedelta(hours=(23 - h))
        hour = time_pt.hour
        
        seed_str = f"{id}_{time_pt.strftime('%Y%m%d%H')}"
        local_random = random.Random(seed_str)
        
        if is_critical:
            temp = ambient_temp + local_random.uniform(55, 75)
            load = local_random.uniform(105, 135)
            voltage = local_random.uniform(350, 375)
        elif is_warning:
            temp = ambient_temp + local_random.uniform(35, 55)
            load = local_random.uniform(85, 110)
            voltage = local_random.uniform(370, 395)
        else:
            temp_offset = local_random.uniform(5, 12) if 11 <= hour <= 16 else local_random.uniform(0, 4)
            temp = ambient_temp + temp_offset + local_random.uniform(-1, 1)
            load = local_random.uniform(40, 80)
            voltage = local_random.uniform(405, 420)
        
        base_current = (float(tx.rated_kva) * 1000.0) / (415.0 * 1.732) if tx.rated_kva else 139.0
        current = base_current * (load / 100.0) + local_random.uniform(-5, 5)
        
        readings.append({
            "id": str(uuid.uuid4()),
            "transformer_id": str(id),
            "time": time_pt.isoformat(),
            "load_percentage": round(load, 2),
            "voltage_lv": round(voltage, 1),
            "current_a": round(current, 1),
            "temperature_c": round(temp, 1),
            "source": "SIMULATION"
        })
        
    return readings

@router.get("/transformers/{id}/maintenance", response_model=List[MaintenanceLogResponse])
def get_transformer_maintenance(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch historical maintenance logs.
    """
    logs = db.query(MaintenanceLog)\
        .filter(MaintenanceLog.transformer_id == id)\
        .order_by(MaintenanceLog.maintenance_date.desc())\
        .all()
    return logs

@router.post("/transformers/{id}/maintenance", response_model=MaintenanceLogResponse)
def log_transformer_maintenance(id: uuid.UUID, log: MaintenanceLogCreate, db: Session = Depends(get_db)):
    """
    Create a new maintenance log entry.
    """
    tx = db.query(Transformer).filter(Transformer.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transformer not found")
        
    db_log = MaintenanceLog(
        transformer_id=id,
        maintenance_date=log.maintenance_date,
        maintenance_type=log.maintenance_type,
        components_replaced=log.components_replaced,
        work_description=log.work_description,
        findings=log.findings,
        oil_bdv_kv=log.oil_bdv_kv,
        winding_resistance=log.winding_resistance,
        insulation_megohm=log.insulation_megohm,
        outcome=log.outcome,
        next_maintenance_due=log.next_maintenance_due
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/transformers/{id}/shap-explanations")
def get_transformer_shap_explanations(id: uuid.UUID, model: str = "isolation_forest", db: Session = Depends(get_db)):
    """
    Fetch the real SHAP feature contributions calculated dynamically from the ML models.
    """
    from services.inference_service import inference_service
    res = inference_service.score_transformer(str(id), db)
    if not res:
        raise HTTPException(status_code=404, detail="Transformer not found")
    
    if model == "xgboost":
        return res.get("xgb_shap_values", [])
    return res.get("shap_values", [])

@router.get("/transformers/{id}/score-history", response_model=List[Dict[str, Any]])
def get_transformer_score_history(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch the historical health/anomaly scores for a specific transformer.
    Reads from the memory-cached health trend dataset with a stable fallback.
    """
    tx = db.query(Transformer).filter(Transformer.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transformer not found")

    from services.data_cache import get_trend_history
    trend_df = get_trend_history(str(id))
    
    if not trend_df.empty:
        history = []
        for _, row in trend_df.iterrows():
            history.append({
                "id": str(uuid.uuid4()),
                "anomaly_score": float(row["anomaly_score"]),
                "health_score": int(row["health_score"]),
                "calculated_at": row["timestamp"]
            })
        return history
        
    current_anomaly = float(tx.current_failure_risk * 100.0) if tx.current_failure_risk is not None else 15.0
    
    from datetime import datetime, timedelta, timezone
    history = []
    
    # Seed random with transformer UUID bytes to ensure trend is stable across refreshes
    random.seed(id.bytes)
    
    for i in range(7):
        day = datetime.now(timezone.utc) - timedelta(days=6 - i)
        variance = random.uniform(-4.0, 4.0)
        day_anomaly = max(5.0, min(98.0, current_anomaly + (6 - i) * random.uniform(-1.5, 0.5) + variance))
        if i == 6:
            day_anomaly = current_anomaly
            
        history.append({
            "id": str(uuid.uuid4()),
            "anomaly_score": round(day_anomaly, 2),
            "health_score": int(100 - day_anomaly),
            "calculated_at": day.isoformat()
        })
    return history

@router.get("/transformers/{id}/forecast", response_model=List[Dict[str, Any]])
def get_transformer_forecast(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Generate a 24-hour future load forecast for a transformer.
    Uses a live forward pass of the PyTorch LSTM model.
    """
    tx = db.query(Transformer).filter(Transformer.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transformer not found")

    from services.data_cache import get_telemetry_history
    from services.deep_learning import predict_lstm_forecast
    import numpy as np

    history_df = get_telemetry_history(str(id))
    if not history_df.empty and len(history_df) >= 24:
        # Extract features of past 24 hours: [temperature_c, load_percentage, voltage_lv, current_a]
        past_seq = history_df[["temperature_c", "load_percentage", "voltage_lv", "current_a"]].values[-24:]
        forecast_preds = predict_lstm_forecast(past_seq) # shape (24, 2)
        
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        forecast = []
        for h in range(1, 25):
            future_time = now + timedelta(hours=h)
            pred_load = float(forecast_preds[h-1, 0])
            pred_temp = float(forecast_preds[h-1, 1])
            forecast.append({
                "time": future_time.isoformat(),
                "predicted_load_percentage": round(pred_load, 2),
                "predicted_temperature_c": round(pred_temp, 1),
                "confidence_lower": max(0.0, round(pred_load * 0.85, 2)),
                "confidence_upper": min(150.0, round(pred_load * 1.15, 2))
            })
        return forecast

    # Fallback if telemetry cache is not populated
    base_load = float(tx.current_load_pct) if tx and tx.current_load_pct is not None else 45.0
    from datetime import datetime, timezone, timedelta
    import random
    
    now = datetime.now(timezone.utc)
    forecast = []
    
    for h in range(1, 25):
        future_time = now + timedelta(hours=h)
        hour_of_day = future_time.hour
        peak_factor = 1.2 if 18 <= hour_of_day <= 22 else (0.8 if 2 <= hour_of_day <= 6 else 1.0)
        
        base_load = base_load * 0.90 + (random.uniform(40, 80) * 0.10)
        pred_load = min(150.0, max(0.0, base_load * peak_factor + random.uniform(-3, 3)))
        
        forecast.append({
            "time": future_time.isoformat(),
            "predicted_load_percentage": round(pred_load, 2),
            "predicted_temperature_c": round(tx.current_oil_temp_c or 45.0, 1),
            "confidence_lower": max(0, round(pred_load * 0.85, 2)),
            "confidence_upper": min(150, round(pred_load * 1.15, 2))
        })
        
    return forecast

@router.get("/transformers/{id}/weather-impact", response_model=Dict[str, Any])
def get_weather_impact(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch the live weather and calculate the thermal penalty currently applied to the Risk Score.
    """
    tx = db.query(Transformer).filter(Transformer.id == id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transformer not found")
        
    lat = float(tx.latitude) if tx.latitude else 0.0
    lon = float(tx.longitude) if tx.longitude else 0.0
    
    from services.ai_service import ai_service
    ambient_temp = ai_service._fetch_live_weather(lat, lon)
    
    penalty = 0.0
    if ambient_temp > 35.0:
        penalty = min(15.0, (ambient_temp - 35.0) * 2.0)
        
    return {
        "ambient_temperature_c": ambient_temp,
        "weather_penalty_percentage": round(penalty, 2),
        "is_hot_day": ambient_temp > 35.0
    }
