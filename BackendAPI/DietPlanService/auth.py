# DietPlanService/auth.py
"""Verifies the same JWTs VitroFit.API issues (HS256, shared signing key from its
JwtSettings config) so /api/diet/generate and /api/diet/confirm can trust the
authenticated user's id instead of a client-supplied user_id. Neither sibling
Python service (chatbot_service, GymAgentService) does this today - both are
open/unauthenticated - but this service writes user-linked rows, so it needs it.

JwtSettings are read directly from VitroFit.API's own appsettings.json (rather
than duplicated into this service's .env) so the two services can never end up
with mismatched secrets.
"""
import json
import os
import jwt
from fastapi import Header, HTTPException

_APPSETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "VitroFit.API", "appsettings.json"
)

with open(_APPSETTINGS_PATH, "r", encoding="utf-8") as f:
    _jwt_settings = json.load(f)["JwtSettings"]

JWT_SIGNING_KEY = _jwt_settings["Secret"]
JWT_ISSUER = _jwt_settings["Issuer"]
JWT_AUDIENCE = _jwt_settings["Audience"]


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
