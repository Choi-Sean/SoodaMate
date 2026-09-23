from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import get_current_user
from app.models.user import User
from app.services.call_service import get_twilio_ice_servers

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("/ice-servers")
async def get_ice_servers(user: User = Depends(get_current_user)) -> dict:
    """Twilio's Network Traversal Service (STUN+TURN, reusing the account
    already configured for Twilio Verify/Lookup) is tried first — it's what
    actually makes calls connect reliably across two phones on different
    networks/restrictive NATs. Falls back to public STUN (+ a manually
    configured TURN_URL, if one is ever set) when Twilio isn't configured or
    the request fails — never hardcode TURN credentials client-side, hence
    this endpoint instead of baking them into the mobile app."""
    twilio_ice_servers = await get_twilio_ice_servers()
    if twilio_ice_servers:
        return {"ice_servers": twilio_ice_servers}

    ice_servers = [{"urls": settings.stun_url_list}]
    if settings.turn_url:
        ice_servers.append(
            {"urls": [settings.turn_url], "username": settings.turn_username, "credential": settings.turn_credential}
        )
    return {"ice_servers": ice_servers}
