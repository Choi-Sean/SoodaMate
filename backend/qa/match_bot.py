"""Keeps ONE clearly-labelled test partner waiting in the blind-chat queue so a
tester who presses "match" gets paired immediately.

Runs the real app in-process against the shared DB with NO stubs (a real
"you're paired" push reaches the tester if they were the one waiting).
The partner is locked to the tester's exact age/gender so real users are
extremely unlikely to be paired with it. Stops as soon as a match exists.

python -m qa.match_bot <tester_user_id> [max_minutes] [existing_bot_user_id]
"""
import json
import sys
import time
import uuid
from datetime import date

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["APP_ENV"] = "test"
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from sqlalchemy import or_, select
from starlette.testclient import TestClient

from app.database import async_session_factory
from app.main import app
from app.models.interaction import Match
from app.models.profile import Profile
from qa import harness as H  # only for make_jpeg / put_to_r2 helpers


def main(tester_id, max_minutes=90, reuse_bot_id=None):
    tester_uuid = uuid.UUID(tester_id)
    with TestClient(app) as tc:
        async def tester_profile():
            async with async_session_factory() as s:
                return await s.get(Profile, tester_uuid)

        p = tc.portal.call(tester_profile)
        today = date.today()
        age = today.year - p.birth_date.year - ((today.month, today.day) < (p.birth_date.month, p.birth_date.day))
        want_gender = p.interested_in if p.interested_in in ("male", "female") else "female"
        bot_gender = want_gender
        bot_interest = p.gender if p.gender in ("male", "female") else "all"
        print(f"tester: age {age}, {p.gender} seeking {p.interested_in}; bot will be {bot_gender} seeking {bot_interest}", flush=True)

        # --- create the partner (fully labelled as a test account), or reuse one
        if reuse_bot_id:
            from app.services.auth_service import issue_tokens

            bot_id = reuse_bot_id
            tok = issue_tokens(uuid.UUID(bot_id))
            j = {"user_id": bot_id, "access_token": tok.access_token}
            h = {"Authorization": f"Bearer {tok.access_token}"}
        else:
            r = tc.post("/auth/signup", json={"email": f"qa-matchbot-{uuid.uuid4().hex[:6]}@example.com", "password": "password123"})
            j = r.json()
            bot_id = j["user_id"]
            h = {"Authorization": f"Bearer {j['access_token']}"}
            birth_year = today.year - max(age - 5, 21) if age > 26 else today.year - 25
            body = {
                "display_name": "QA테스트", "legal_first_name": "QA테스트", "birth_date": f"{birth_year}-01-01", "gender": bot_gender,
                "interested_in": bot_interest, "min_age_pref": 18, "max_age_pref": 99, "max_distance_km": 500,
                "bio": "테스트용 상대예요 (QA) — This is a test partner.", "mbti": "INFJ", "interests": ["travel", "music"],
                "languages": ["ko", "en"], "preferred_categories": ["travel", "music"],
                "location_lat": p.location_lat, "location_lng": p.location_lng,
            }
            assert tc.put("/profiles/me", headers=h, json=body).status_code == 200
            pr = tc.post("/uploads/presign", headers=h, json={"content_type": "image/jpeg", "position": 0}).json()
            H.put_to_r2(pr["upload_url"], H.make_jpeg("QA TEST PARTNER", (720, 900), (255, 200, 215)), "image/jpeg")
            assert tc.post("/profiles/me/photos/confirm", headers=h, json={"gcs_object_path": pr["gcs_object_path"], "position": 0}).status_code == 201
        Path(H.OUT / "match_bot.json").write_text(json.dumps({"bot_user_id": bot_id, "tester_id": tester_id}), encoding="utf-8")
        print("bot user", bot_id, flush=True)

        queue_body = {"categories": ["travel", "music"], "gender": bot_interest, "min_age": age, "max_age": age}

        def matched():
            async def q():
                async with async_session_factory() as s:
                    return await s.scalar(
                        select(Match.id).where(
                            or_((Match.user_a_id == uuid.UUID(bot_id)) & (Match.user_b_id == tester_uuid),
                                (Match.user_b_id == uuid.UUID(bot_id)) & (Match.user_a_id == tester_uuid))
                        )
                    )

            return tc.portal.call(q)

        deadline = time.time() + max_minutes * 60
        last_refresh = 0.0
        while time.time() < deadline:
            mid = matched()
            if mid:
                print("MATCHED", mid, flush=True)
                with tc.websocket_connect(f"/ws/chat?token={j['access_token']}") as ws:
                    ws.send_json({"type": "message", "match_id": str(mid), "content": "Hi! I'm a test partner 👋 (테스트 상대예요)"})
                    time.sleep(3)
                print("greeting sent; done", flush=True)
                return
            if time.time() - last_refresh > 240:  # queue entries go stale after 15 min: re-join every 4
                tc.delete("/blind-chat/queue", headers=h)
                resp = tc.post("/blind-chat/queue", headers=h, json=queue_body)
                print("queue ->", resp.status_code, resp.json(), flush=True)
                last_refresh = time.time()
            time.sleep(15)
        tc.delete("/blind-chat/queue", headers=h)
        print("timed out waiting; left the queue", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 90, sys.argv[3] if len(sys.argv) > 3 else None)
