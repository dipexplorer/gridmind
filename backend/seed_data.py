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
from models.intelligence import TransformerScore, ShapExplanation
from models.timeseries import Complaint, LoadReading
from models.event import MaintenanceLog, FailureEvent
from geoalchemy2.elements import WKTElement

def create_tables():
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

def clear_data(db: Session):
    print("Clearing old data...")
    db.query(ShapExplanation).delete()
    db.query(TransformerScore).delete()
    db.query(LoadReading).delete()
    db.query(MaintenanceLog).delete()
    db.query(FailureEvent).delete()
    db.query(Complaint).delete()
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

        # 4. Generate 24 Load Readings for each Transformer (SCADA simulation)
        print("Generating historical load readings (SCADA)...")
        readings = []
        for t in db_transformers:
            base_temp = random.uniform(45.0, 65.0)
            base_load = random.uniform(40.0, 75.0)
            for h in range(24):
                time_point = datetime.now(timezone.utc if hasattr(datetime, 'now') else None) - timedelta(hours=24-h)
                temp = base_temp + random.uniform(-5.0, 10.0) + (5.0 if 12 <= h <= 16 else 0.0) # Hotter during afternoon
                load_pct = base_load + random.uniform(-10.0, 15.0) + (15.0 if 18 <= h <= 22 else 0.0) # Peak load evening
                
                readings.append(LoadReading(
                    time=time_point,
                    transformer_id=t.id,
                    load_kw=float(load_pct * float(t.rated_kva) / 100.0),
                    load_kvar=float(load_pct * float(t.rated_kva) * 0.1 / 100.0),
                    load_percentage=float(load_pct),
                    voltage_lv=float(random.uniform(400.0, 420.0)),
                    current_a=float(load_pct * 3.5),
                    temperature_c=float(temp),
                    source='SCADA'
                ))
        db.bulk_save_objects(readings)
        db.commit()

        # 5. Generate historical Maintenance Logs
        print("Generating historical maintenance logs...")
        logs = []
        for i, t in enumerate(db_transformers):
            # Seed maintenance log for 40% of transformers
            if random.random() < 0.4:
                m_date = date.today() - timedelta(days=random.randint(15, 120))
                m_type = random.choice(["OIL_FILTERATION", "BUSHING_REPLACEMENT", "TAP_CHANGER_OVERHAUL", "GENERAL_INSPECTION"])
                
                logs.append(MaintenanceLog(
                    transformer_id=t.id,
                    maintenance_date=m_date,
                    maintenance_type=m_type,
                    components_replaced=["Oil Filter", "Gasket"] if m_type == "OIL_FILTERATION" else ["Bushing Sleeves"] if m_type == "BUSHING_REPLACEMENT" else [],
                    work_description=f"Standard {m_type.lower().replace('_', ' ')} performed during routine inspection.",
                    findings=random.choice(["Insulation levels normal.", "Slight winding discoloration.", "Oil BDV value stable."]),
                    oil_bdv_kv=float(random.uniform(30.0, 60.0)),
                    winding_resistance=float(random.uniform(0.12, 0.45)),
                    insulation_megohm=float(random.uniform(150.0, 600.0)),
                    outcome="COMPLETED",
                    next_maintenance_due=m_date + timedelta(days=180)
                ))
        db.bulk_save_objects(logs)
        db.commit()

        print(f"Successfully inserted {len(db_substations)} Substations, {len(db_feeders)} Feeders, {len(db_transformers)} Transformers, {len(readings)} Load Readings, and {len(logs)} Maintenance Logs!")

    except Exception as e:
        db.rollback()
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    from datetime import timezone
    create_tables()
    seed_data()
