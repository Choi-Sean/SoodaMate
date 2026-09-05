from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("/ice-servers")
async def get_ice_servers(user: User = Depends(get_current_user)) -> dict:
    """STUN is always available (public, no account needed); TURN only
    appears once the user provisions one (Twilio/coturn/etc.) — see
    docs/ENV_VARS.md. Never hardcode TURN credentials client-side, hence
    this endpoint instead of baking them into the mobile app."""
    ice_servers = [{"urls": settings.stun_url_list}]
    if settings.turn_url:
        ice_servers.append(
            {"urls": [settings.turn_url], "username": settings.turn_username, "credential": settings.turn_credential}
        )
    return {"ice_servers": ice_servers}
