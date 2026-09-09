import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.couple_story import CoupleStory, CoupleStoryReport
from app.models.interaction import Block, Match

# Auto-hide (pending manual review — no moderation queue UI exists yet,
# same documented gap as FaceVerification's manual review page) once this
# many distinct users have reported a published story.
REPORT_HIDE_THRESHOLD = 3


async def get_match_for_participant(db: AsyncSession, match_id: uuid.UUID, user_id: uuid.UUID) -> Match | None:
    match = await db.get(Match, match_id)
    if match is None or user_id not in (match.user_a_id, match.user_b_id):
        return None
    return match


async def create_story(
    db: AsyncSession, match: Match, author_id: uuid.UUID, story_text: str, photo_object_path: str | None
) -> CoupleStory:
    peer_id = match.user_b_id if match.user_a_id == author_id else match.user_a_id
    story = CoupleStory(
        match_id=match.id,
        author_id=author_id,
        peer_id=peer_id,
        story_text=story_text,
        photo_object_path=photo_object_path,
        status="pending",
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return story


async def get_story_for_peer_action(db: AsyncSession, story_id: uuid.UUID, user_id: uuid.UUID) -> CoupleStory | None:
    """Only the non-author matched participant, and only while still
    pending — confirm/decline aren't re-doable once a story has already
    moved on (routers/couple_stories.py)."""
    story = await db.get(CoupleStory, story_id)
    if story is None or story.peer_id != user_id or story.status != "pending":
        return None
    return story


async def confirm_story(db: AsyncSession, story: CoupleStory) -> CoupleStory:
    story.status = "published"
    story.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(story)
    return story


async def decline_story(db: AsyncSession, story: CoupleStory) -> CoupleStory:
    story.status = "declined"
    await db.commit()
    await db.refresh(story)
    return story


async def get_feed(
    db: AsyncSession, viewer_id: uuid.UUID, limit: int = 30, before: datetime | None = None
) -> list[CoupleStory]:
    blocked_ids = select(Block.blocked_id).where(Block.blocker_id == viewer_id).union(
        select(Block.blocker_id).where(Block.blocked_id == viewer_id)
    )
    stmt = (
        select(CoupleStory)
        .where(
            CoupleStory.status == "published",
            CoupleStory.author_id.not_in(blocked_ids),
            CoupleStory.peer_id.not_in(blocked_ids),
        )
        .order_by(CoupleStory.published_at.desc())
        .limit(limit)
    )
    if before is not None:
        stmt = stmt.where(CoupleStory.published_at < before)
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


async def get_mine(db: AsyncSession, user_id: uuid.UUID) -> list[CoupleStory]:
    stmt = (
        select(CoupleStory)
        .where((CoupleStory.author_id == user_id) | (CoupleStory.peer_id == user_id))
        .order_by(CoupleStory.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows)


async def report_story(db: AsyncSession, story_id: uuid.UUID, reporter_id: uuid.UUID, reason: str) -> bool:
    """False if the story doesn't exist or this reporter already reported
    it (idempotent, not an error) — True once recorded. Auto-hides at
    REPORT_HIDE_THRESHOLD distinct reports."""
    story = await db.get(CoupleStory, story_id)
    if story is None:
        return False
    existing = await db.scalar(
        select(CoupleStoryReport).where(
            CoupleStoryReport.story_id == story_id, CoupleStoryReport.reporter_id == reporter_id
        )
    )
    if existing is not None:
        return False

    db.add(CoupleStoryReport(story_id=story_id, reporter_id=reporter_id, reason=reason))
    story.report_count += 1
    if story.report_count >= REPORT_HIDE_THRESHOLD:
        story.status = "hidden"
    await db.commit()
    return True
