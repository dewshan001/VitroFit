# DietPlanService/src/utils/security.py
"""Role-based access for the approval endpoints. Built directly on auth.py's
JWT verification (no reimplementation) - just adds a role check on top of the
already-verified claims.

Confirmed against BackendAPI/VitroFit.API/Services/TokenService.cs, which adds
the role via `new Claim(ClaimTypes.Role, user.Role.ToString())`. ClaimTypes.Role
is a .NET constant that serializes as the long URI below, not a short "role"
key - so both are checked to be safe against a future change. Role values come
from BackendAPI/VitroFit.API/Entities/UserRole.cs: User, Trainer, Admin, Gym_Owner.
"""
import hmac
import os

from fastapi import Depends, Header, HTTPException

from src.utils.auth import get_current_user_claims

_ROLE_CLAIM_KEYS = (
    "role",
    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
)


def _extract_role(claims: dict) -> str | None:
    for key in _ROLE_CLAIM_KEYS:
        if key in claims:
            return claims[key]
    return None


def require_roles(*roles: str):
    """FastAPI dependency factory: require_roles("Trainer", "Admin")."""

    def dependency(claims: dict = Depends(get_current_user_claims)) -> dict:
        role = _extract_role(claims)
        if role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role permissions.")
        return claims

    return dependency


MIN_SERVICE_KEY_LENGTH = 32


def require_service_key(x_diet_agent_key: str | None = Header(default=None)) -> None:
    """Internal-only mode. When DIET_AGENT_KEY is set, every /api/diet route needs the
    shared X-Diet-Agent-Key header, so only the ASP.NET API (which holds the key) can
    reach this service - a browser cannot. The caller's JWT is still verified here for
    identity, ownership and roles.

    When DIET_AGENT_KEY is not set the service behaves exactly as it always did
    (directly reachable with just a JWT), so nothing breaks until it is configured.
    A key that is set but too short fails closed with 503, like the gym agent.
    """
    key = os.getenv("DIET_AGENT_KEY", "")
    if not key:
        return
    if len(key) < MIN_SERVICE_KEY_LENGTH:
        raise HTTPException(status_code=503, detail="The diet service is not configured correctly.")
    if not x_diet_agent_key or not hmac.compare_digest(x_diet_agent_key.encode(), key.encode()):
        raise HTTPException(status_code=401, detail="Invalid or missing service key.")
