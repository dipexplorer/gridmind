import uuid
from celery_app import celery_app
from core.database import SessionLocal
from crud import crud_asset, crud_intelligence
from services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="tasks.scoring.score_all_transformers")
def score_all_transformers(task_id: str = None):
    """
    Celery background task:
    1. Gets all transformers from DB.
    2. Runs AI Mock model on each.
    3. Saves results in intelligence tables.
    """
    if not task_id:
        task_id = str(uuid.uuid4())
        
    db = SessionLocal()
    try:
        # Mark run as started
        crud_intelligence.create_score_run(db, task_id)
        
        # Get all transformers
        transformers = crud_asset.get_transformers(db, limit=1000)
        
        anomalies_detected = 0
        
        for t in transformers:
            # 1. AI Inference
            prediction = ai_service.predict_anomaly(str(t.id))
            
            # 2. Extract SHAP and remove from main dict
            shap_values = prediction.pop("shap_values")
            
            # 3. Save to database
            crud_intelligence.create_transformer_score(
                db=db,
                run_id=task_id,
                data=prediction,
                shap_values=shap_values
            )
            
            if prediction["risk_category"] in ["HIGH", "CRITICAL"]:
                anomalies_detected += 1
                # Create an Alert and Ticket in the Database automatically
                from models.event import Alert, MaintenanceTicket
                
                alert_msg = f"AI Predicted {prediction['risk_category']} risk for transformer {t.name}."
                alert = Alert(
                    transformer_id=t.id,
                    severity=prediction["risk_category"],
                    message=alert_msg
                )
                db.add(alert)
                db.flush() # flush to get alert.id
                
                ticket = MaintenanceTicket(
                    transformer_id=t.id,
                    alert_id=alert.id,
                    status="OPEN",
                    priority=prediction["risk_category"],
                    description=f"Auto-generated ticket due to {prediction['risk_category']} anomaly score: {prediction['anomaly_score']}"
                )
                db.add(ticket)
                
        db.commit()
        # Mark run as completed
        crud_intelligence.update_score_run(
            db=db, 
            run_id=task_id, 
            status="COMPLETED", 
            anomalies_detected=anomalies_detected
        )
        
        logger.info(f"AI Scoring run {task_id} completed. Anomalies: {anomalies_detected}")
        return {"status": "success", "run_id": task_id, "anomalies_detected": anomalies_detected}
        
    except Exception as e:
        logger.error(f"Error in score_all_transformers: {str(e)}")
        crud_intelligence.update_score_run(db, task_id, status="FAILED")
        raise e
    finally:
        db.close()
