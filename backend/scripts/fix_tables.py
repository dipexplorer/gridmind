import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from core.database import SessionLocal

db = SessionLocal()
try:
    print("Dropping intelligence tables...")
    db.execute(text("DROP TABLE IF EXISTS shap_explanations CASCADE"))
    db.execute(text("DROP TABLE IF EXISTS transformer_scores CASCADE"))
    db.execute(text("DROP TABLE IF EXISTS score_run_metadata CASCADE"))
    db.execute(text("DROP TABLE IF EXISTS model_registry CASCADE"))
    db.commit()
    print("Tables dropped.")
except Exception as e:
    print("Error:", e)
finally:
    db.close()

from core.database import engine
from models.intelligence import ScoreRunMetadata, TransformerScore, ShapExplanation
print("Recreating intelligence tables...")
ScoreRunMetadata.metadata.create_all(engine, tables=[
    ScoreRunMetadata.__table__,
    TransformerScore.__table__,
    ShapExplanation.__table__
])
print("Done.")
