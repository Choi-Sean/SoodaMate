import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.match import IcebreakerOut, MatchOut
from app.services import chat_service, icebreaker_service
from app.services.match_service import accept_blind_reveal, list_matches, request_blind_reveal

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
async def get_matches(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[MatchOut]:
    return await list_matches(db, user.id)


@router.get("/{match_id}/icebreaker", response_model=IcebreakerOut)
async def get_icebreaker(
    match_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> IcebreakerOut:
    # get_match_for_user (not get_active_match_for_user) — a suggestion is
    # still harmless to show for a chat that's gone stale/expired; only
    # sending a message is actually gated.
    match = await chat_service.get_match_for_user(db, match_id, user.id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")

    peer_id = chat_service.other_participant(match, user.id)
    viewer_profile = await db.get(Profile, user.id)
    peer_profile = await db.get(Profile, peer_id)
    if viewer_profile is None or peer_profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "profile not found")

    result = icebreaker_service.get_icebreaker(viewer_profile, peer_profile)
    return IcebreakerOut(**result)


@router.post("/{match_id}/blind-reveal/request", response_model=MatchOut)
async def blind_reveal_request(
    match_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> MatchOut:
    result = await request_blind_reveal(db, match_id, user.id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return result


@router.post("/{match_id}/blind-reveal/accept", response_model=MatchOut)
async def blind_reveal_accept(
    match_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> MatchOut:
    result = await accept_blind_reveal(db, match_id, user.id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return result
