from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
import uvicorn
import threading
import urllib.request
import time

app = FastAPI()
security = HTTPBearer()

@app.get("/test")
def test(cred = Depends(security)):
    return "ok"

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

t = threading.Thread(target=run_server, daemon=True)
t.start()
time.sleep(1)

def get_status(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        urllib.request.urlopen(req)
        return 200
    except Exception as e:
        return e.code

print("No header:", get_status("http://127.0.0.1:8001/test"))
print("Bad header:", get_status("http://127.0.0.1:8001/test", {"Authorization": "Foo bar"}))
