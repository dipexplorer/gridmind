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
            # Derive project ref from POSTGRES_HOST (e.g., db.xyz.supabase.co -> xyz)
            host_parts = settings.POSTGRES_HOST.split(".")
            if len(host_parts) >= 3 and host_parts[0] == "db" and host_parts[-2:] == ["supabase", "co"]:
                project_ref = host_parts[1]
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

def verify_supabase_token(credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]):
    """
    Verifies that the provided JWT token was issued by Supabase.
    Validates a Supabase JWT. It supports both symmetric (HS256) and asymmetric (ES256/RS256) tokens.
    """
    token = credentials.credentials
    
    try:
        unverified_header = jwt.get_unverified_header(token)
        token_alg = unverified_header.get("alg", "HS256")
        
        if token_alg != "HS256":
            # Asymmetric token: Use JWKS
            key = get_supabase_jwks()
            if not key:
                raise ValueError("JWKS could not be loaded to verify asymmetric token")
        else:
            # Symmetric token: Use JWT secret
            key = SUPABASE_JWT_SECRET
            
        payload = jwt.decode(
            token, 
            key, 
            algorithms=[token_alg], 
            options={"verify_aud": False} # Supabase aud can vary
        )
        return payload
    except Exception as e:
        print(f"JWT Verification Failed: {type(e).__name__} - {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
