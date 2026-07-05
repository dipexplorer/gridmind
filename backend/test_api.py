import urllib.request
import json
import sys

try:
    print("Fetching transformers list...")
    req = urllib.request.urlopen("http://localhost:8000/api/v1/transformers/")
    transformers = json.loads(req.read())
    print("Found", len(transformers), "transformers.")
    if not transformers:
        print("Error: No transformers found in database!")
        sys.exit(1)
        
    first_tx = transformers[0]
    id = first_tx["id"]
    print("Testing detail for ID:", id)
    
    # Detail
    try:
        detail_req = urllib.request.urlopen(f"http://localhost:8000/api/v1/transformers/{id}/detail")
        detail = json.loads(detail_req.read())
        print("Detail OK:", detail["transformer_code"])
    except Exception as e:
        print("Detail API failed:", e)
        
    # Timeseries
    try:
        ts_req = urllib.request.urlopen(f"http://localhost:8000/api/v1/transformers/{id}/timeseries")
        ts = json.loads(ts_req.read())
        print("Timeseries OK:", len(ts), "readings")
    except Exception as e:
        print("Timeseries API failed:", e)

    # Maintenance
    try:
        m_req = urllib.request.urlopen(f"http://localhost:8000/api/v1/transformers/{id}/maintenance")
        m = json.loads(m_req.read())
        print("Maintenance OK:", len(m), "logs")
    except Exception as e:
        print("Maintenance API failed:", e)

    # SHAP
    try:
        s_req = urllib.request.urlopen(f"http://localhost:8000/api/v1/transformers/{id}/shap-explanations")
        s = json.loads(s_req.read())
        print("SHAP OK:", len(s), "factors")
    except Exception as e:
        print("SHAP API failed:", e)
        
except Exception as e:
    print("Main request failed:", e)
