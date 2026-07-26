import os
from jose import jwt, JWTError

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9vaWFxdnh6YXFlcWp6ZmhlamdtIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMwODQyODAsImV4cCI6MjA5ODY2MDI4MH0.B1vJ4irAMGMvZkQlTXHKgpSXbHdb3Fkxhui6j6km9JU"
secret = "uYAQTAaNXn3lLi6bzlwoMjUDFJ/xw+5o3sE+2McVij7kEJRVFZE28u1JPou7N78x902T6octeIrrxPkmUK1HZQ=="

try:
    payload = jwt.decode(token, secret, algorithms=["HS256"], options={"verify_aud": False})
    print("Success:", payload)
except Exception as e:
    print("Failed string secret:", str(e))

