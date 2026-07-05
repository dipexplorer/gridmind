import sys
import os
import uuid
import random
from datetime import datetime, date, timedelta

# Add backend directory to sys.path so we can import from core and models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from core.database import SessionLocal, engine
from models.base import Base
from models.asset import Substation, Feeder, Transformer
from models.intelligence import TransformerScore
from geoalchemy2.elements import WKTElement

def create_tables():
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

def clear_data(db: Session):
    print("Clearing old data...")
    db.query(TransformerScore).delete()
    db.query(Transformer).delete()
    db.query(Feeder).delete()
    db.query(Substation).delete()
    db.commit()
    print("Old data cleared.")

def seed_data():
    db = SessionLocal()
    try:
        clear_data(db)

        print("Seeding dummy data for Guwahati region...")

        # 1. Create Substations
        substations_data = [
            {"name": "Paltan Bazaar SS", "code": "SS_PALTAN", "voltage_kv": 33.0, "district": "Kamrup Metropolitan", "lat": 26.177, "lon": 91.758},
            {"name": "Dispur SS", "code": "SS_DISPUR", "voltage_kv": 33.0, "district": "Kamrup Metropolitan", "lat": 26.143, "lon": 91.789},
            {"name": "Maligaon SS", "code": "SS_MALIGAON", "voltage_kv": 33.0, "district": "Kamrup Metropolitan", "lat": 26.160, "lon": 91.700},
        ]
        
        db_substations = []
        for s_data in substations_data:
            ss = Substation(
                name=s_data["name"],
                code=s_data["code"],
                voltage_kv=s_data["voltage_kv"],
                district=s_data["district"],
                location=WKTElement(f"POINT({s_data['lon']} {s_data['lat']})", srid=4326)
            )
            db.add(ss)
            db_substations.append(ss)
        
        db.commit()
        for ss in db_substations: db.refresh(ss)

        # 2. Create Feeders
        db_feeders = []
        for ss in db_substations:
            for i in range(2): # 2 Feeders per substation
                feeder = Feeder(
                    substation_id=ss.id,
                    name=f"{ss.name} Feeder {i+1}",
                    code=f"FDR_{ss.code}_{i+1}",
                    voltage_kv=11.0,
                    feeder_type="OVERHEAD"
                )
                db.add(feeder)
                db_feeders.append(feeder)
        
        db.commit()
        for f in db_feeders: db.refresh(f)

        # 3. Create 100 Transformers (Randomly distributed around Substations)
        db_transformers = []
        for i in range(100):
            feeder = random.choice(db_feeders)
            
            # Generate random location near the feeder's substation
            # 0.01 degrees is roughly 1km
            lat_offset = random.uniform(-0.02, 0.02)
            lon_offset = random.uniform(-0.02, 0.02)
            
            # Find the parent substation for the coordinates
            ss = next(s for s in db_substations if s.id == feeder.substation_id)
            t_lon = ss.location.data.split("(")[1].split(" ")[0] if isinstance(ss.location, WKTElement) else 91.75
            t_lat = ss.location.data.split(" ")[1].split(")")[0] if isinstance(ss.location, WKTElement) else 26.17
            
            t_lon = float(t_lon) + lon_offset
            t_lat = float(t_lat) + lat_offset

            # Random characteristics
            cooling_type = random.choice(["ONAN", "ONAF", "OFAF"])
            rated_kva = random.choice([100, 250, 500, 1000])
            is_flood_prone = random.random() < 0.2 # 20% chance
            
            # Installation date between 5 and 20 years ago
            days_ago = random.randint(5 * 365, 20 * 365)
            inst_date = date.today() - timedelta(days=days_ago)

            transformer = Transformer(
                transformer_code=f"TRF_GHY_{i+1:03d}",
                feeder_id=feeder.id,
                substation_id=feeder.substation_id,
                rated_kva=rated_kva,
                voltage_hv_kv=11.0,
                voltage_lv_v=415.0,
                installation_type=random.choice(["POLE_MOUNTED", "PAD_MOUNTED"]),
                cooling_type=cooling_type,
                manufacturer=random.choice(["BHEL", "ABB", "Siemens", "Crompton"]),
                location=WKTElement(f"POINT({t_lon} {t_lat})", srid=4326),
                address_text=f"Street {i+1}, Guwahati",
                district="Kamrup Metropolitan",
                is_flood_prone=is_flood_prone,
                installation_date=inst_date,
                num_consumers=random.randint(50, 500),
                consumer_category=random.choice(["RESIDENTIAL", "COMMERCIAL", "MIXED"]),
                operational_status="IN_SERVICE"
            )
            db.add(transformer)
            db_transformers.append(transformer)
        
        db.commit()
        for t in db_transformers: db.refresh(t)

        print(f"Successfully inserted {len(db_substations)} Substations, {len(db_feeders)} Feeders, and {len(db_transformers)} Transformers!")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
    seed_data()
