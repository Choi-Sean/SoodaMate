"""Find (and with --delete remove) QA leftovers if a run was killed before its own cleanup.
Only touches: @example.com QA accounts and users created after --since (UTC) that are phone-only
without any real-looking profile. Prints everything it would touch first."""
import asyncio, sys, uuid
from datetime import datetime, timezone
sys.path.insert(0, ".")
from sqlalchemy import delete, or_, select
from app.config import settings
from app.database import async_session_factory
from app.models.interaction import Block, Match, Report, Swipe
from app.models.profile import Profile
from app.models.promotion import Promotion
from app.models.user import User
from app.services import storage_service

async def main(since, do_delete):
    since_dt = datetime.fromisoformat(since).replace(tzinfo=timezone.utc)
    async with async_session_factory() as s:
        rows = (await s.execute(
            select(User.id, User.email, User.phone_number, User.created_at, Profile.display_name)
            .join(Profile, Profile.user_id == User.id, isouter=True)
            .where(or_(User.email.like("qa-%@example.com"),
                       (User.created_at >= since_dt) & (User.email.is_(None)) & ((Profile.display_name.is_(None)) | Profile.display_name.like("QA%"))))
            .order_by(User.created_at))).all()
        print(len(rows), "candidate QA users")
        for r in rows[:8]: print("  ", r.email, r.phone_number, r.display_name, r.created_at)
        if len(rows) > 8: print("   ...")
        real_looking = [r for r in rows if r.email is None and r.display_name is None]
        print("phone-only, no profile:", [(r.phone_number, str(r.created_at)) for r in real_looking])
        if not do_delete: return
        uids = [r.id for r in rows]
        client = storage_service._get_client()
        n = 0
        for uid in uids:
            for prefix in (f"users/{uid}/", f"verifications/{uid}/"):
                resp = client.list_objects_v2(Bucket=settings.r2_bucket_name, Prefix=prefix)
                for o in resp.get("Contents", []) or []:
                    client.delete_object(Bucket=settings.r2_bucket_name, Key=o["Key"]); n += 1
        await s.execute(delete(Promotion).where(Promotion.created_by.in_(uids)))
        await s.execute(delete(Match).where(Match.user_a_id.in_(uids) | Match.user_b_id.in_(uids)))
        await s.execute(delete(Swipe).where(Swipe.from_user_id.in_(uids) | Swipe.to_user_id.in_(uids)))
        await s.execute(delete(Block).where(Block.blocker_id.in_(uids) | Block.blocked_id.in_(uids)))
        await s.execute(delete(Report).where(Report.reporter_id.in_(uids) | Report.reported_id.in_(uids)))
        await s.execute(delete(User).where(User.id.in_(uids)))
        await s.commit()
        print("deleted users:", len(uids), "R2 objects:", n)

asyncio.run(main(sys.argv[1], "--delete" in sys.argv))
