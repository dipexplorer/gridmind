import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tasks.scoring import score_all_transformers
import uuid

try:
    print("Testing scoring...")
    result = score_all_transformers(str(uuid.uuid4()))
    print("Result:", result)
except Exception as e:
    import traceback
    traceback.print_exc()
