"""Deletes the accounts that own the given phone numbers through the app's own
DELETE /account/me (so matches, swipes, files in R2 etc. are removed exactly as
for a user-initiated deletion). Usage: python -m qa.delete_users_by_phone +1... +82..."""
import sys
import uuid

from sqlalchemy import func, select

from qa import harness as H
from app.config import settings
from app.database import async_session_factory
from app.models.profile import FaceVerification, Photo, Profile
from app.models.user import User
from app.services import storage_service
from app.services.auth_service import issue_tokens


def main(numbers):
    H.start()
    try:
        client = storage_service._get_client()

        def r2_count(prefix):
            return len(client.list_objects_v2(Bucket=settings.r2_bucket_name, Prefix=prefix).get("Contents", []) or [])

        for n in numbers:
            async def find():
                async with async_session_factory() as s:
                    row = (await s.execute(select(User.id, Profile.display_name).join(Profile, Profile.user_id == User.id, isouter=True)
                                           .where(User.phone_number == n))).first()
                    if row is None:
                        return None
                    photos = await s.scalar(select(func.count()).select_from(Photo).where(Photo.user_id == row.id))
                    fv = await s.scalar(select(FaceVerification.status).where(FaceVerification.user_id == row.id))
                    return row.id, row.display_name, photos, fv

            info = H.db(find)
            if info is None:
                print(f"{n}: no account")
                continue
            uid, name, photos, fv = info
            before = (r2_count(f"users/{uid}/"), r2_count(f"verifications/{uid}/"))
            print(f"{n}: account {str(uid)[:8]} name={name!r} photos={photos} face_verification={fv} r2(users,verifications)={before}")
            token = issue_tokens(uid).access_token
            r = H.tc.delete("/account/me", headers={"Authorization": f"Bearer {token}"})
            print(f"  DELETE /account/me -> {r.status_code}")

            async def exists():
                async with async_session_factory() as s:
                    return await s.scalar(select(func.count()).select_from(User).where(User.id == uid))

            print(f"  user rows left: {H.db(exists)}; r2 left: {(r2_count(f'users/{uid}/'), r2_count(f'verifications/{uid}/'))}")
    finally:
        H.stop()


if __name__ == "__main__":
    main(sys.argv[1:])
