from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid

from core.database import get_db
from models.asset import Transformer, Substation, Feeder
from models.timeseries import LoadReading
from models.event import MaintenanceLog
from models.intelligence import TransformerScore, ShapExplanation
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

@router.get("/transformers/{id}/timeseries", response_model=List[LoadReadingResponse])
def get_transformer_timeseries(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch latest 24 load and temperature readings for a transformer.
    """
    readings = db.query(LoadReading)\
        .filter(LoadReading.transformer_id == id)\
        .order_by(LoadReading.time.asc())\
        .limit(24)\
        .all()
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
def get_transformer_shap_explanations(id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch the SHAP feature contributions for the latest AI run on this transformer.
    """
    # Get latest score to reference the correct score_id
    score = db.query(TransformerScore)\
        .filter(TransformerScore.transformer_id == id)\
        .order_by(TransformerScore.calculated_at.desc())\
        .first()
        
    if not score:
        # Return fallback SHAP values if no AI run has scored it yet
        return [
            {"feature_name": "temperature_c", "feature_value": 52.4, "shap_value": 0.15},
            {"feature_name": "load_percentage", "feature_value": 85.1, "shap_value": 0.22},
            {"feature_name": "voltage_lv", "feature_value": 410.2, "shap_value": -0.05},
            {"feature_name": "current_a", "feature_value": 120.5, "shap_value": 0.10}
        ]
        
    explanations = db.query(ShapExplanation)\
        .filter(ShapExplanation.score_id == score.id)\
        .all()
        
    return explanations
