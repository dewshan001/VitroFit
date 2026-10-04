# DietPlanService/security.py
"""Role-based access for the approval endpoints. Built directly on auth.py's
JWT verification (no reimplementation) - just adds a role check on top of the
already-verified claims.

Confirmed against BackendAPI/VitroFit.API/Services/TokenService.cs, which adds
the role via `new Claim(ClaimTypes.Role, user.Role.ToString())`. ClaimTypes.Role
is a .NET constant that serializes as the long URI below, not a short "role"
key - so both are checked to be safe against a future change. Role values come
from BackendAPI/VitroFit.API/Entities/UserRole.cs: User, Trainer, Admin, Gym_Owner.
"""
from fastapi import Depends, HTTPException

from auth import get_current_user_claims

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
