from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    print("Dropping useless tables...")
    db.execute(text("DROP TABLE IF EXISTS load_readings CASCADE;"))
    db.execute(text("DROP TABLE IF EXISTS alerts CASCADE;"))
    db.execute(text("DROP TABLE IF EXISTS maintenance_tickets CASCADE;"))
    db.execute(text("DROP TABLE IF EXISTS shap_explanations CASCADE;"))
    db.execute(text("DROP TABLE IF EXISTS transformer_scores CASCADE;"))
    db.execute(text("DROP TABLE IF EXISTS score_run_metadata CASCADE;"))
    db.commit()
    print("Successfully dropped all useless tables!")
except Exception as e:
    db.rollback()
    print(f"Error dropping tables: {e}")
finally:
    db.close()
