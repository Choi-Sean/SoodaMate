import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.discovery import CandidateOut
from app.schemas.match import BlindChatFeedbackCreate, BlindChatFeedbackOut, IcebreakerOut, MatchOut
from app.services import chat_service, icebreaker_service
from app.services.blind_chat_service import submit_blind_chat_feedback
from app.services.match_service import (
    HideIdentityError,
    accept_blind_reveal,
    delete_match,
    get_matched_profile,
    list_matches,
    request_blind_reveal,
    use_blind_peek,
)

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchOut])
async def get_matches(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[MatchOut]:
    return await list_matches(db, user.id)


@router.delete("/{match_id}", status_code=204)
async def delete_match_endpoint(
    match_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> None:
    if not await delete_match(db, match_id, user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")


@router.get("/{match_id}/profile", response_model=CandidateOut)
async def get_match_profile(
    match_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CandidateOut:
    try:
        result = await get_matched_profile(db, match_id, user.id)
    except HideIdentityError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "profiles aren't revealed in this match yet")
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return result


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


@router.post("/{match_id}/blind-peek", response_model=MatchOut)
async def blind_peek(
    match_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> MatchOut:
    """Consumes 1 Profile.stealth_peek_credits (shop product blind_peek_1) to
    let the caller alone see the other side's real profile in a still-
    anonymous blind match — no consent, no notice to the peer."""
    result = await use_blind_peek(db, match_id, user.id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return result


@router.post("/{match_id}/blind-feedback", response_model=BlindChatFeedbackOut)
async def submit_blind_feedback(
    match_id: uuid.UUID,
    body: BlindChatFeedbackCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BlindChatFeedbackOut:
    result = await submit_blind_chat_feedback(db, match_id, user.id, body)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")
    return result
