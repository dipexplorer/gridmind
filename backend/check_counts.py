from core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    res = db.execute(text("SELECT current_status, COUNT(*) FROM transformers GROUP BY current_status;"))
    for row in res:
        print(row)
finally:
    db.close()
