import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moment import Moment

# Rolling window — the newest this many per user; older ones are pruned on
# every insert so "요즘 나 / Lately" always reads as *recent*, with no
# management burden on the user.
MOMENT_LIMIT = 6


async def create_moment(
    db: AsyncSession, user_id: uuid.UUID, image_object_path: str, caption: str | None
) -> Moment:
    moment = Moment(user_id=user_id, image_object_path=image_object_path, caption=caption)
    db.add(moment)
    await db.flush()

    # Prune anything beyond the newest MOMENT_LIMIT for this user.
    stale = (
        await db.execute(
            select(Moment)
            .where(Moment.user_id == user_id)
            .order_by(Moment.created_at.desc())
            .offset(MOMENT_LIMIT)
        )
    ).scalars().all()
    for old in stale:
        await db.delete(old)

    await db.commit()
    await db.refresh(moment)
    return moment


async def list_moments(db: AsyncSession, user_id: uuid.UUID) -> list[Moment]:
    rows = (
        await db.execute(
            select(Moment).where(Moment.user_id == user_id).order_by(Moment.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


async def delete_moment(db: AsyncSession, moment_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    moment = await db.get(Moment, moment_id)
    if moment is None or moment.user_id != user_id:
        return False
    await db.delete(moment)
    await db.commit()
    return True


async def get_moments_for_users(
    db: AsyncSession, user_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[Moment]]:
    if not user_ids:
        return {}
    rows = (
        await db.execute(
            select(Moment).where(Moment.user_id.in_(user_ids)).order_by(Moment.user_id, Moment.created_at.desc())
        )
    ).scalars().all()
    out: dict[uuid.UUID, list[Moment]] = {uid: [] for uid in user_ids}
    for moment in rows:
        out.setdefault(moment.user_id, []).append(moment)
    return out
