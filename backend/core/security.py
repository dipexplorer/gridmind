from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import urllib.request
import json
import ssl
from core.config import settings

# Supabase uses HS256 algorithm by default
ALGORITHM = "HS256"
SUPABASE_JWT_SECRET = settings.SUPABASE_JWT_SECRET

_jwks_cache = None

def get_supabase_jwks():
    global _jwks_cache
    if not _jwks_cache:
        try:
            # Try to derive project ref from POSTGRES_USER if using connection pooler (postgres.xyz)
            project_ref = None
            if "." in settings.POSTGRES_USER and settings.POSTGRES_USER.startswith("postgres."):
                project_ref = settings.POSTGRES_USER.split(".")[1]
            else:
                # Fallback to deriving from POSTGRES_HOST (db.xyz.supabase.co)
                host_parts = settings.POSTGRES_HOST.split(".")
                if len(host_parts) >= 3 and host_parts[0] == "db" and host_parts[-2:] == ["supabase", "co"]:
                    project_ref = host_parts[1]
            
            if project_ref:
                jwks_url = f"https://{project_ref}.supabase.co/auth/v1/.well-known/jwks.json"
                
                # Fetch JWKS
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                with urllib.request.urlopen(jwks_url, context=ctx) as response:
                    _jwks_cache = json.loads(response.read().decode("utf-8"))
        except Exception as e:
            print(f"Failed to fetch JWKS: {e}")
            _jwks_cache = None
            
    return _jwks_cache

security = HTTPBearer()

def validate_token_string(token: str):
    """
    Validates a JWT token string directly. Useful for WebSockets.
    """
    try:
        unverified_header = jwt.get_unverified_header(token)
        token_alg = unverified_header.get("alg", "HS256")
        
        if token_alg != "HS256":
            key = get_supabase_jwks()
            if not key:
                raise ValueError("JWKS could not be loaded to verify asymmetric token")
        else:
            key = SUPABASE_JWT_SECRET
            
        payload = jwt.decode(
            token, 
            key, 
            algorithms=[token_alg], 
            options={"verify_aud": False}
        )
        return payload
    except Exception as e:
        print(f"JWT Verification Failed: {type(e).__name__} - {str(e)}")
        raise e

def verify_supabase_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    """
    Verifies that the provided JWT token was issued by Supabase.
    """
    token = credentials.credentials
    try:
        return validate_token_string(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
