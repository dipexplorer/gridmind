import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.database import engine
from models.system import SystemSettings

print("Creating SystemSettings table...")
SystemSettings.metadata.create_all(engine, tables=[SystemSettings.__table__])
print("Done.")
