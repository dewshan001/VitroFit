# DietPlanService/src/utils/auth.py
"""Verifies the same JWTs VitroFit.API issues (HS256, shared signing key from its
JwtSettings config) so /api/diet/generate and /api/diet/confirm can trust the
authenticated user's id instead of a client-supplied user_id. Neither sibling
Python service (chatbot_service, GymAgentService) does this today - both are
open/unauthenticated - but this service writes user-linked rows, so it needs it.

The signing secret comes from the shared BackendAPI/.env (JwtSettings__Secret, the
same variable VitroFit.API reads), so the two services can never end up with
mismatched secrets. Issuer/audience come from VitroFit.API's appsettings.json.
"""
import json
import os
import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

_APPSETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "VitroFit.API", "appsettings.json"
)

with open(_APPSETTINGS_PATH, "r", encoding="utf-8") as f:
    _jwt_settings = json.load(f)["JwtSettings"]

# Env vars, when set, override the values read from VitroFit.API's
# appsettings.json (e.g. for tests, which sign their own tokens and must
# never touch the real shared secret).
JWT_SIGNING_KEY = os.getenv("JWT_SECRET") or os.getenv("JwtSettings__Secret") or _jwt_settings["Secret"]
JWT_ISSUER = os.getenv("JWT_ISSUER") or os.getenv("JwtSettings__Issuer") or _jwt_settings["Issuer"]
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE") or os.getenv("JwtSettings__Audience") or _jwt_settings["Audience"]


def get_current_user_id(authorization: str = Header(default=None)) -> int:
    """FastAPI dependency: extracts and verifies the bearer token, returning the
    numeric user id from the 'sub' claim. Raises 401 on any missing/invalid/expired token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = authorization[len("Bearer "):]
    try:
        payload = jwt.decode(
            token,
            JWT_SIGNING_KEY,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim.")

    try:
        return int(sub)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token 'sub' claim is not a valid user id.")


def get_current_user_claims(authorization: str = Header(default=None)) -> dict:
    """Same verification as get_current_user_id, but returns the full decoded
    claims dict instead of just the numeric id - used by security.require_roles
    for role-based checks (e.g. the trainer/admin claim), which get_current_user_id
    intentionally doesn't expose.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header.")

    token = authorization[len("Bearer "):]
    try:
        return jwt.decode(
            token,
            JWT_SIGNING_KEY,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
