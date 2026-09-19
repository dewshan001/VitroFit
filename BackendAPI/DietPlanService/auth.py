# DietPlanService/auth.py
"""Verifies the same JWTs VitroFit.API issues (HS256, shared signing key from its
JwtSettings config) so /api/diet/generate and /api/diet/confirm can trust the
authenticated user's id instead of a client-supplied user_id. Neither sibling
Python service (chatbot_service, GymAgentService) does this today - both are
open/unauthenticated - but this service writes user-linked rows, so it needs it.
"""
import os
import jwt
from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()

JWT_SIGNING_KEY = os.getenv("JWT_SIGNING_KEY")
JWT_ISSUER = os.getenv("JWT_ISSUER", "VitroFitApi")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "VitroFitWeb")

if not JWT_SIGNING_KEY:
    print("WARNING: JWT_SIGNING_KEY is missing! Set it to match VitroFit.API's JwtSettings.Secret.")


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
