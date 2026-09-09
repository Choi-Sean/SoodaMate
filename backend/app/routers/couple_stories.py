import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.couple_story import CoupleStory
from app.models.profile import Profile
from app.models.user import User
from app.schemas.couple_story import CoupleStoryCreate, CoupleStoryOut, CoupleStoryReportCreate
from app.services import couple_story_service, push_service

router = APIRouter(prefix="/couple-stories", tags=["couple-stories"])


async def _to_out(db: AsyncSession, story: CoupleStory) -> CoupleStoryOut:
    author_profile = await db.get(Profile, story.author_id)
    peer_profile = await db.get(Profile, story.peer_id)
    return CoupleStoryOut(
        id=story.id,
        match_id=story.match_id,
        author_id=story.author_id,
        peer_id=story.peer_id,
        author_display_name=author_profile.display_name if author_profile else "",
        peer_display_name=peer_profile.display_name if peer_profile else "",
        story_text=story.story_text,
        photo_object_path=story.photo_object_path,
        status=story.status,
        created_at=story.created_at,
        published_at=story.published_at,
    )


@router.post("", response_model=CoupleStoryOut, status_code=201)
async def create_story(
    body: CoupleStoryCreate, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CoupleStoryOut:
    match = await couple_story_service.get_match_for_participant(db, body.match_id, user.id)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "match not found")

    existing = await db.scalar(select(CoupleStory).where(CoupleStory.match_id == body.match_id))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "a story already exists for this match")

    story = await couple_story_service.create_story(db, match, user.id, body.story_text, body.photo_object_path)
    author_profile = await db.get(Profile, user.id)
    await push_service.send_couple_story_request_notification(
        db, story.peer_id, author_name=author_profile.display_name if author_profile else "", story_id=story.id
    )
    return await _to_out(db, story)


@router.post("/{story_id}/confirm", response_model=CoupleStoryOut)
async def confirm_story(
    story_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CoupleStoryOut:
    story = await couple_story_service.get_story_for_peer_action(db, story_id, user.id)
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "story not found")
    story = await couple_story_service.confirm_story(db, story)
    await push_service.send_couple_story_published_notification(db, story.author_id, story.id)
    return await _to_out(db, story)


@router.post("/{story_id}/decline", response_model=CoupleStoryOut)
async def decline_story(
    story_id: uuid.UUID, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> CoupleStoryOut:
    story = await couple_story_service.get_story_for_peer_action(db, story_id, user.id)
    if story is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "story not found")
    story = await couple_story_service.decline_story(db, story)
    return await _to_out(db, story)


@router.get("/feed", response_model=list[CoupleStoryOut])
async def feed(
    before: datetime | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CoupleStoryOut]:
    stories = await couple_story_service.get_feed(db, user.id, limit=limit, before=before)
    return [await _to_out(db, s) for s in stories]


@router.get("/mine", response_model=list[CoupleStoryOut])
async def mine(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> list[CoupleStoryOut]:
    stories = await couple_story_service.get_mine(db, user.id)
    return [await _to_out(db, s) for s in stories]


@router.post("/{story_id}/report", status_code=204)
async def report_story(
    story_id: uuid.UUID,
    body: CoupleStoryReportCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    await couple_story_service.report_story(db, story_id, user.id, body.reason)
