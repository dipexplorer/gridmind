from sqlalchemy.orm import Session
from models.intelligence import ScoreRunMetadata, TransformerScore, ShapExplanation

def get_latest_score_run(db: Session):
    return db.query(ScoreRunMetadata).order_by(ScoreRunMetadata.started_at.desc()).first()

def get_transformer_score(db: Session, transformer_id: str):
    # Get the latest score for this specific transformer
    return db.query(TransformerScore).filter(TransformerScore.transformer_id == transformer_id).order_by(TransformerScore.calculated_at.desc()).first()

def get_shap_explanations(db: Session, score_id: str):
    return db.query(ShapExplanation).filter(ShapExplanation.score_id == score_id).all()
