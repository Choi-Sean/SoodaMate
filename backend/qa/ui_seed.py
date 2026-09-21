"""Seeds a set of realistic QA users/scenarios into the shared DB for the
browser (RN-Web) UI walk-through. Nothing here is cleaned up automatically -
run `python qa/leak_audit.py <since> --delete` when the UI pass is finished.

Phone users use the QA bypass numbers configured in qa/run_backend.cmd
(code 424242) so the app can log in through the real UI."""
import json
import uuid

from PIL import Image, ImageDraw, ImageFont

from qa import harness as H


class _TC:
    def __getattr__(self, name):
        return getattr(H.tc, name)


tc = _TC()

PW = "QaAdmin!2026"


def portrait(initial, color, size=(720, 900)):
    img = Image.new("RGB", size, color)
    d = ImageDraw.Draw(img)
    for i in range(0, size[1], 6):  # soft vertical gradient
        shade = tuple(min(255, c + int(40 * i / size[1])) for c in color)
        d.rectangle([0, i, size[0], i + 6], fill=shade)
    d.ellipse([size[0] * 0.25, size[1] * 0.18, size[0] * 0.75, size[1] * 0.58], fill=(255, 235, 225))
    d.rectangle([size[0] * 0.18, size[1] * 0.6, size[0] * 0.82, size[1]], fill=(255, 235, 225))
    d.text((size[0] * 0.45, size[1] * 0.3), initial, fill=(120, 60, 60))
    import io

    b = io.BytesIO()
    img.save(b, "JPEG", quality=88)
    return b.getvalue()


def upload_photos(u, initial, color, n=3):
    for pos in range(n):
        p = tc.post("/uploads/presign", headers=u.h, json={"content_type": "image/jpeg", "position": pos}).json()
        H.put_to_r2(p["upload_url"], portrait(initial, tuple((c + pos * 12) % 256 for c in color)), "image/jpeg")
        r = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": p["gcs_object_path"], "position": pos})
        assert r.status_code == 201, r.text


def phone_user(phone, name, gender, interested, age, initial, color, lang="ko", **kw):
    u = H.signup_phone(phone)
    r = tc.put("/profiles/me", headers=u.h, json=H.profile_body(name, age, gender, interested, location_lat=37.5665, location_lng=126.978, **kw))
    assert r.status_code == 200, r.text
    upload_photos(u, initial, color)
    tc.put("/account/language", headers=u.h, json={"language": lang})
    return u


def main():
    H.start()
    out = {}
    admin = H.make_admin("uiadmin")
    # give the admin a known email + password login for the web admin pages
    async def set_email():
        import uuid as _u
        from app.core.security import hash_password
        from app.database import async_session_factory
        from app.models.user import User

        async with async_session_factory() as s:
            row = await s.get(User, _u.UUID(admin.id))
            row.email = "qa-uiadmin@example.com"
            row.password_hash = hash_password(PW)
            await s.commit()

    H.db(set_email)
    out["admin"] = {"email": "qa-uiadmin@example.com", "password": PW, "id": admin.id}

    # main user (Korean UI), fully set up
    main = phone_user("+821099990001", "QA수다", "female", "male", 27, "S", (255, 170, 190),
                      bio="안녕하세요! 커피와 여행을 좋아해요 ☕✈️", mbti="ENFP", interests=["travel", "coffee"],
                      languages=["ko", "en"], preferred_categories=["hobby", "food", "travel"])
    out["main"] = {"phone": "+821099990001", "id": main.id}

    # partners
    man = H.make_user("uiMan", "male", "female", 28, location_lat=37.57, location_lng=126.98, bio="Hi, I'm QA man")
    upload_photos(man, "M", (140, 190, 255))
    out["man"] = man.id

    # 1) classic match + chat with text and a real image message
    mid = H.mutual_match(man, main)
    img = H.make_jpeg("PHOTO FROM CHAT", (800, 600))
    p = tc.post("/uploads/presign-chat-image", headers=man.h, json={"content_type": "image/jpeg"}).json()
    H.put_to_r2(p["upload_url"], img, "image/jpeg")
    with tc.websocket_connect(f"/ws/chat?token={main.token}") as wm, tc.websocket_connect(f"/ws/chat?token={man.token}") as wa:
        wm.send_json({"type": "message", "match_id": mid, "content": "안녕하세요! 프로필 보고 연락했어요 😊"})
        wa.receive_json()
        wa.send_json({"type": "message", "match_id": mid, "content": "Hi! Nice to meet you 👋"})
        wm.receive_json()
        wa.send_json({"type": "message", "match_id": mid, "message_type": "image", "image_object_path": p["gcs_object_path"], "content": ""})
        wm.receive_json()
    out["classic_match"] = mid

    # 2) blind match (masked) for the main user
    b_age = 27
    bm = H.make_user("uiBlind", "male", "female", b_age, min_age_pref=27, max_age_pref=27, bio="Blind partner QA")
    tc.post("/blind-chat/queue", headers=bm.h, json={"categories": ["hobby", "food"], "gender": "female", "min_age": 27, "max_age": 27})
    q = tc.post("/blind-chat/queue", headers=main.h, json={"categories": ["food", "travel"], "gender": "male", "min_age": 27, "max_age": 27}).json()
    out["blind_match"] = q.get("match_id")
    if q.get("match_id"):
        with tc.websocket_connect(f"/ws/chat?token={bm.token}") as wb:
            wb.send_json({"type": "message", "match_id": q["match_id"], "content": "요즘 빠진 음식 있어요? 🍜"})
            import time

            time.sleep(0.7)

    # purchase history + membership for main
    import hashlib, hmac, json as _j, time as _t
    from app.config import settings

    def buy(user, product):
        evt = {"id": f"evt_ui_{uuid.uuid4().hex[:8]}", "object": "event", "type": "checkout.session.completed",
               "data": {"object": {"id": f"cs_ui_{uuid.uuid4().hex[:6]}", "object": "checkout.session",
                                   "metadata": {"user_id": user.id, "product_id": product}, "subscription": "sub_ui"}}}
        raw = _j.dumps(evt).encode()
        ts = int(_t.time())
        sig = hmac.new(settings.stripe_webhook_secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        tc.post("/payments/webhook", content=raw, headers={"stripe-signature": f"t={ts},v1={sig}"})

    buy(main, "ai_match_pack_5")
    buy(main, "unlimited_matching_week")
    out["purchases"] = ["ai_match_pack_5", "unlimited_matching_week"]

    # fresh phone user without a profile -> ProfileSetup screen
    out["new_user_phone"] = "+821099990002"

    # face verification states
    def face(phone, name, initial, color, final):
        u = phone_user(phone, name, "female", "male", 26, initial, color)
        selfie = portrait(initial, color)
        idimg = H.make_jpeg(f"ID CARD {name}", (900, 560), (210, 225, 255))
        for kind, data in (("selfie", selfie), ("id_photo", idimg)):
            pr = tc.post("/verification/face/presign", headers=u.h, json={"content_type": "image/jpeg", "kind": kind}).json()
            H.put_to_r2(pr["upload_url"], data, "image/jpeg")
            if kind == "selfie":
                sp = pr["gcs_object_path"]
            else:
                ip = pr["gcs_object_path"]
        tc.post("/verification/face/submit", headers=u.h, json={"selfie_object_path": sp, "id_photo_object_path": ip})
        if final:
            item = next(i for i in tc.get("/admin/face-verifications?status=pending", headers=admin.h).json() if i["user_id"] == u.id)
            if final == "approved":
                tc.post(f"/admin/face-verifications/{item['id']}/approve", headers=admin.h)
            else:
                tc.post(f"/admin/face-verifications/{item['id']}/reject", headers=admin.h, json={"reason_key": "id_blurry", "reason": "ID photo is blurry"})
        return u

    face("+821099990003", "QA심사대기", "P", (255, 210, 150), None)  # pending -> for admin approve/reject in the UI
    face("+821099990004", "QA승인됨", "A", (170, 230, 180), "approved")
    face("+821099990005", "QA거절됨", "R", (230, 170, 230), "rejected")
    out["face_users"] = {"pending": "+821099990003", "approved": "+821099990004", "rejected": "+821099990005"}

    # a report + inquiry for the admin console
    troll = H.make_user("uiTroll", "male", "female", 30, bio="QA reported user")
    tc.post("/safety/report", headers=main.h, json={"user_id": troll.id, "reason": "부적절한 메시지", "detail": "QA 신고 테스트"})
    tc.post("/inquiries", headers=main.h, json={"subject": "QA 문의", "message": "앱 사용 중 궁금한 점이 있어요 🙂"})

    # who-liked-me + couple story + moment for feed screens
    liker = H.make_user("uiLiker", "male", "female", 27, bio="Liked you")
    upload_photos(liker, "L", (255, 200, 120))
    tc.post("/interactions/like", headers=liker.h, json={"to_user_id": main.id})

    json.dump(out, open(H.OUT / "ui_seed.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    H.stop()


if __name__ == "__main__":
    main()
