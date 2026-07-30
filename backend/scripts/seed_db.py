import os
import sys
import uuid
import csv
import logging
from datetime import datetime
from geoalchemy2.elements import WKTElement

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import SessionLocal
from models.asset import Substation, Feeder, Transformer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DBSeeder")

def seed_database():
    db = SessionLocal()
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seed_path = os.path.join(base_dir, "data", "seed_transformers.csv")
        
        if not os.path.exists(seed_path):
            logger.error(f"Seed file not found at {seed_path}. Please run generate_datasets.py first.")
            return

        logger.info(f"Seeding database from: {seed_path}")
        
        # Load substations and feeders to prevent duplicate lookups
        substations_cache = {s.code: s.id for s in db.query(Substation).all()}
        feeders_cache = {f.code: f.id for f in db.query(Feeder).all()}
        
        with open(seed_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        logger.info(f"Loaded {len(rows)} asset rows to seed.")

        # 1. Upsert Substations
        logger.info("Upserting substations...")
        for row in rows:
            sub_code = row["substation_code"]
            sub_name = row["substation_name"]
            district = row["district"]
            lon = float(row["longitude"])
            lat = float(row["latitude"])
            
            if sub_code not in substations_cache:
                sub_id = uuid.uuid4()
                location_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
                db_sub = Substation(
                    id=sub_id,
                    name=sub_name,
                    code=sub_code,
                    voltage_kv=33.0,
                    district=district,
                    location=location_geom
                )
                db.add(db_sub)
                db.flush()
                substations_cache[sub_code] = sub_id
                
        # 2. Upsert Feeders
        logger.info("Upserting feeders...")
        for row in rows:
            sub_code = row["substation_code"]
            fd_code = row["feeder_code"]
            fd_name = row["feeder_name"]
            sub_id = substations_cache[sub_code]
            
            if fd_code not in feeders_cache:
                fd_id = uuid.uuid4()
                db_fd = Feeder(
                    id=fd_id,
                    name=fd_name,
                    code=fd_code,
                    substation_id=sub_id,
                    voltage_kv=11.0,
                    feeder_type='OVERHEAD'
                )
                db.add(db_fd)
                db.flush()
                feeders_cache[fd_code] = fd_id

        # 3. Upsert Transformers
        logger.info("Upserting transformers...")
        for idx, row in enumerate(rows):
            t_id = uuid.UUID(row["transformer_id"])
            t_code = row["transformer_code"]
            sub_id = substations_cache[row["substation_code"]]
            fd_id = feeders_cache[row["feeder_code"]]
            
            lon = float(row["longitude"])
            lat = float(row["latitude"])
            location_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)
            
            tx = db.query(Transformer).filter(Transformer.transformer_code == t_code).first()
            
            install_date = datetime.strptime(row["installation_date"], "%Y-%m-%d").date()
            
            data_fields = {
                "feeder_id": fd_id,
                "substation_id": sub_id,
                "rated_kva": float(row["rated_kva"]),
                "age_years": int(row["age_years"]),
                "is_metered": row["is_metered"].lower() == "true",
                "current_load_pct": float(row["current_load_pct"]),
                "current_oil_temp_c": float(row["current_oil_temp_c"]),
                "current_health_score": int(row["current_health_score"]),
                "current_failure_risk": float(row["current_failure_risk"]),
                "current_status": row["current_status"],
                "location": location_geom,
                "address_text": row["address_text"],
                "district": row["district"],
                "num_consumers": int(row["num_consumers"]),
                "manufacturer": row["manufacturer"],
                "cooling_type": row["cooling_type"],
                "installation_date": install_date,
                "is_flood_prone": row["is_flood_prone"].lower() == "true",
                "is_high_lightning": row["is_high_lightning"].lower() == "true",
                "operational_status": row["operational_status"],
                "voltage_hv_kv": 11.0,
                "voltage_lv_v": 415.0
            }
            
            if tx:
                for k, v in data_fields.items():
                    setattr(tx, k, v)
            else:
                db_tx = Transformer(
                    id=t_id,
                    transformer_code=t_code,
                    **data_fields
                )
                db.add(db_tx)
                
            if (idx + 1) % 500 == 0:
                logger.info(f"Processed {idx + 1}/{len(rows)} transformers...")
                db.flush()

        db.commit()
        logger.info("Database seeding completed successfully!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Seeding failed: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
