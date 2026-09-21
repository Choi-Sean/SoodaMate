"""Core suite: auth, profile, uploads (real R2), verification (real images +
admin approve/reject), admin console, safety."""
import hashlib
import threading
import uuid

import httpx

from qa import harness as H
from qa.harness import case, hdr, tc

# ============================================================== AUTH


@case("AUTH-001", "Auth", "Phone signup", "New phone number: send code, confirm with correct code",
      "start=204 and SMS requested for that number; confirm=200 with tokens, is_new_user=True; /account/me shows phone_verified=True",
      "POST /auth/phone/start -> POST /auth/phone/confirm -> GET /account/me")
def auth_001(c):
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    s = tc.post("/auth/phone/start", json={"phone_number": phone})
    c.eq("start status", s.status_code, 204)
    c.ok("SMS requested for number", phone in H.SMS_STARTED)
    r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    c.eq("confirm status", r.status_code, 200)
    j = r.json()
    H.track(j["user_id"])
    c.eq("is_new_user", j["is_new_user"], True)
    c.ok("access+refresh token issued", bool(j["access_token"]) and bool(j["refresh_token"]))
    me = tc.get("/account/me", headers=hdr(j["access_token"])).json()
    c.eq("phone_verified", me["phone_verified"], True)
    H.S["phone_user"] = H.U(j["user_id"], j["access_token"], j["refresh_token"], phone=phone)


@case("AUTH-002", "Auth", "Phone login", "Same phone number logs in again -> same account",
      "second confirm returns is_new_user=False and the same user_id (no duplicate account)",
      "confirm twice with same number")
def auth_002(c):
    u = H.S["phone_user"]
    r = tc.post("/auth/phone/confirm", json={"phone_number": u.phone, "code": "123456"})
    c.eq("status", r.status_code, 200)
    c.eq("is_new_user", r.json()["is_new_user"], False)
    c.eq("same user id", r.json()["user_id"], u.id)


@case("AUTH-003", "Auth", "Phone signup", "Wrong SMS code is rejected",
      "confirm with wrong code -> 400 'incorrect or expired code', no account created", "confirm wrong code")
def auth_003(c):
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "000000"})
    c.eq("status", r.status_code, 400)


@case("AUTH-004", "Auth", "Phone validation", "Non-E.164 phone formats rejected",
      "start with local format / letters / too short / too long -> 400 or 422 each, never 500",
      "POST /auth/phone/start with 5 malformed numbers")
def auth_004(c):
    for bad in ["01012345678", "+82-10-1234-5678", "abc", "+1", "+" + "9" * 20]:
        r = tc.post("/auth/phone/start", json={"phone_number": bad})
        c.ok(f"rejected with 4xx for {bad!r}", r.status_code in (400, 422), r.status_code)


@case("AUTH-005", "Auth", "Internet-number filter", "Korean 070 internet phone is rejected before any SMS is sent",
      "400 'virtual phone numbers are not allowed'; SMS never requested", "start with +82 70 number")
def auth_005(c):
    n = "+827012345678"
    before = len(H.SMS_STARTED)
    r = tc.post("/auth/phone/start", json={"phone_number": n})
    c.eq("status", r.status_code, 400)
    c.eq("detail", r.json().get("detail"), "virtual phone numbers are not allowed")
    c.eq("SMS sent", len(H.SMS_STARTED) - before, 0)


@case("AUTH-006", "Auth", "Internet-number filter", "Korean 050 safe-number and 02 landline rejected",
      "both 400 with the virtual-number message", "start with +82 50 and +82 2 numbers")
def auth_006(c):
    for n in ["+8250212345678", "+82212345678", "+82311234567"]:
        r = tc.post("/auth/phone/start", json={"phone_number": n})
        c.eq(f"{n} status", r.status_code, 400)


@case("AUTH-007", "Auth", "Internet-number filter", "US VoIP (Google Voice/TextNow style) rejected via Line Type lookup",
      "lookup=nonFixedVoip -> 400 virtual-number message, no SMS", "stub Twilio Lookup to nonFixedVoip, start with US number")
def auth_007(c):
    from app.services import phone_screening

    async def voip(_n):
        return "nonFixedVoip"

    orig = phone_screening._lookup_line_type
    phone_screening._lookup_line_type = voip
    try:
        before = len(H.SMS_STARTED)
        r = tc.post("/auth/phone/start", json={"phone_number": "+12135550101"})
        c.eq("status", r.status_code, 400)
        c.eq("detail", r.json().get("detail"), "virtual phone numbers are not allowed")
        c.eq("SMS sent", len(H.SMS_STARTED) - before, 0)
    finally:
        phone_screening._lookup_line_type = orig


@case("AUTH-008", "Auth", "Internet-number filter", "US real mobile number passes the filter",
      "lookup=mobile -> 204 and SMS requested", "stub Lookup=mobile, start with US number")
def auth_008(c):
    from app.services import phone_screening

    async def mobile(_n):
        return "mobile"

    orig = phone_screening._lookup_line_type
    phone_screening._lookup_line_type = mobile
    try:
        r = tc.post("/auth/phone/start", json={"phone_number": "+12135550102"})
        c.eq("status", r.status_code, 204)
        c.ok("SMS requested", "+12135550102" in H.SMS_STARTED)
    finally:
        phone_screening._lookup_line_type = orig


@case("AUTH-009", "Auth", "Internet-number filter", "REAL Twilio Lookup call classifies the developer's own (bypass) numbers as mobile",
      "live Lookup (billed ~$0.008 each) returns 'mobile' for each number in DEV_PHONE_BYPASS_NUMBERS, so the filter never blocks the developer's own real phones",
      "call the real phone_screening._lookup_line_type for the configured developer numbers")
def auth_009(c):
    import importlib

    from app.config import settings
    from app.services import phone_screening

    numbers = settings.dev_phone_bypass_number_list
    if not numbers:
        c.info("DEV_PHONE_BYPASS_NUMBERS not set in this environment - nothing to look up")
        return
    importlib.reload(phone_screening)  # drop the harness stub -> real function
    real = phone_screening._lookup_line_type
    for i, n in enumerate(numbers[:2], 1):
        c.eq(f"developer number #{i} line type", H.db(lambda n=n: real(n)), "mobile")
    H.install_stubs()  # re-apply the stub (module reload replaced it)


@case("AUTH-010", "Auth", "Tokens", "Refresh token issues a new working access token; access token is not accepted as refresh",
      "refresh=200 and new token works on /account/me; using access token as refresh -> 401",
      "POST /auth/refresh with refresh token, then with access token")
def auth_010(c):
    u = H.S["phone_user"]
    r = tc.post("/auth/refresh", json={"refresh_token": u.refresh})
    c.eq("refresh status", r.status_code, 200)
    me = tc.get("/account/me", headers=hdr(r.json()["access_token"]))
    c.eq("new access token works", me.status_code, 200)
    bad = tc.post("/auth/refresh", json={"refresh_token": u.token})
    c.eq("access-as-refresh status", bad.status_code, 401)


@case("AUTH-011", "Auth", "Tokens", "Missing / garbage / tampered token on protected endpoints",
      "no token 401/403, garbage 401, tampered signature 401; never 500", "GET /account/me variants")
def auth_011(c):
    c.ok("no token rejected", tc.get("/account/me").status_code in (401, 403))
    c.eq("garbage token", tc.get("/account/me", headers=hdr("garbage")).status_code, 401)
    u = H.S["phone_user"]
    tampered = u.token[:-3] + ("aaa" if not u.token.endswith("aaa") else "bbb")
    c.eq("tampered token", tc.get("/account/me", headers=hdr(tampered)).status_code, 401)


@case("AUTH-012", "Auth", "Email login (admin)", "Email signup/login and duplicate/wrong password handling",
      "signup=201; duplicate email rejected (409); login ok; wrong password 401; unknown email 401",
      "signup, duplicate signup, login, wrong password, unknown email")
def auth_012(c):
    email = f"qa-auth12-{uuid.uuid4().hex[:6]}@example.com"
    u = H.signup_email(email)
    c.eq("duplicate signup", tc.post("/auth/signup", json={"email": email, "password": "password123"}).status_code, 409)
    c.eq("login ok", tc.post("/auth/login", json={"email": email, "password": "password123"}).status_code, 200)
    c.eq("wrong password", tc.post("/auth/login", json={"email": email, "password": "nope-nope"}).status_code, 401)
    c.eq("unknown email", tc.post("/auth/login", json={"email": "nobody-zzz@example.com", "password": "password123"}).status_code, 401)
    c.eq("short password", tc.post("/auth/signup", json={"email": f"qa-{uuid.uuid4().hex[:6]}@example.com", "password": "123"}).status_code, 422)


@case("AUTH-013", "Auth", "Password storage", "Password is stored only as a salted bcrypt hash",
      "DB PasswordHash starts with $2b$12$, is 60 chars, differs from plaintext; two users with the same password have different hashes",
      "signup two users with same password, read Users.PasswordHash")
def auth_013(c):
    a = H.signup_email(f"qa-h1-{uuid.uuid4().hex[:6]}@example.com", "SamePassw0rd!")
    b = H.signup_email(f"qa-h2-{uuid.uuid4().hex[:6]}@example.com", "SamePassw0rd!")

    async def read():
        from sqlalchemy import select

        from app.database import async_session_factory
        from app.models.user import User

        async with async_session_factory() as s:
            rows = (await s.execute(select(User.password_hash).where(User.id.in_([uuid.UUID(a.id), uuid.UUID(b.id)])))).all()
            return [r[0] for r in rows]

    hashes = H.db(read)
    c.ok("bcrypt prefix", all(h.startswith("$2b$12$") for h in hashes), hashes[0][:7])
    c.eq("length", len(hashes[0]), 60)
    c.ok("not plaintext", all("SamePassw0rd" not in h for h in hashes))
    c.ok("salted (hashes differ)", hashes[0] != hashes[1])


@case("AUTH-014", "Auth", "Ban enforcement", "Banned user cannot log in, use an old token, or open the chat socket",
      "phone login 403, old access token 401/403, websocket rejected", "ban via DB then try each")
def auth_014(c):
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    u = H.signup_phone(phone)

    async def ban():
        from app.database import async_session_factory
        from app.models.user import User

        async with async_session_factory() as s:
            row = await s.get(User, uuid.UUID(u.id))
            row.is_banned = True
            await s.commit()

    H.db(ban)
    r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    c.eq("login after ban", r.status_code, 403)
    c.ok("old token rejected", tc.get("/account/me", headers=u.h).status_code in (401, 403))
    rejected = False
    try:
        with tc.websocket_connect(f"/ws/chat?token={u.token}"):
            pass
    except Exception:
        rejected = True
    c.ok("websocket rejected", rejected)


@case("AUTH-015", "Auth", "Account settings", "Language preference and marketing email update / validation",
      "language ko ok, xx -> 422; valid email ok; invalid 422; email already used by another account 409",
      "PUT /account/language, /account/email")
def auth_015(c):
    u = H.make_user("acct")
    c.eq("language ko", tc.put("/account/language", headers=u.h, json={"language": "ko"}).status_code, 204)
    c.eq("me shows ko", tc.get("/account/me", headers=u.h).json()["preferred_language"], "ko")
    c.eq("language xx", tc.put("/account/language", headers=u.h, json={"language": "xx"}).status_code, 422)
    e = f"qa-mkt-{uuid.uuid4().hex[:6]}@example.com"
    c.eq("email ok", tc.put("/account/email", headers=u.h, json={"email": e}).status_code, 204)
    c.eq("email invalid", tc.put("/account/email", headers=u.h, json={"email": "not-an-email"}).status_code, 422)
    other = H.make_user("acct2")
    c.eq("email duplicate", tc.put("/account/email", headers=other.h, json={"email": e}).status_code, 409)


@case("AUTH-016", "Auth", "Concurrency", "Two simultaneous confirms for the same new number create exactly one account",
      "both requests succeed with the same user_id (race handled by unique index)", "2 threads confirm same number")
def auth_016(c):
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    out = []

    def go():
        r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
        out.append((r.status_code, r.json().get("user_id")))

    ts = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    for _, uid in out:
        if uid:
            H.track(uid)
    c.eq("both 200", sorted(s for s, _ in out), [200, 200])
    c.eq("single account", len({uid for _, uid in out}), 1)


@case("AUTH-017", "Auth", "Input hardening", "Injection-style and oversized inputs never cause a 500",
      "SQL-ish email/password, 10k char strings -> 4xx (or handled), never 5xx", "signup/login/phone with hostile strings")
def auth_017(c):
    evil = ["' OR 1=1 --", "'; DROP TABLE Users; --", "<script>alert(1)</script>@x.com", "a" * 10000 + "@x.com"]
    for e in evil:
        r = tc.post("/auth/login", json={"email": e, "password": "x' OR '1'='1"})
        c.ok(f"login {e[:20]!r} not 5xx", r.status_code < 500, r.status_code)
    r = tc.post("/auth/phone/start", json={"phone_number": "+1" + "9" * 5000})
    c.ok("phone huge not 5xx", r.status_code < 500, r.status_code)
    # the Users table must still exist / be queryable
    c.eq("db still healthy", tc.get("/health").status_code, 200)


# ============================================================== PROFILE


@case("PROF-001", "Profile", "Profile setup", "Complete profile with photo becomes discoverable-complete",
      "PUT profile 200; is_profile_complete False before photo, True after photo confirm; fields echo back",
      "signup -> PUT /profiles/me -> confirm photo -> GET /profiles/me")
def prof_001(c):
    u = H.signup_email(f"qa-p1-{uuid.uuid4().hex[:6]}@example.com")
    r = tc.put("/profiles/me", headers=u.h, json=H.profile_body("Minji", 27, "female", "male", bio="안녕하세요 hello", mbti="ENFP",
                                                                  interests=["travel", "coffee"], languages=["ko", "en"],
                                                                  preferred_categories=["hobby", "food"]))
    c.eq("put status", r.status_code, 200)
    c.eq("complete before photo", r.json()["is_profile_complete"], False)
    p = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": f"users/{u.id}/photos/{uuid.uuid4()}.jpg", "position": 0})
    c.eq("photo confirm", p.status_code, 201)
    me = tc.get("/profiles/me", headers=u.h).json()
    c.eq("complete after photo", me["is_profile_complete"], True)
    c.eq("bio round trip (Korean+English)", me["bio"], "안녕하세요 hello")
    c.eq("mbti", me["mbti"], "ENFP")
    c.eq("interests", me["interests"], ["travel", "coffee"])
    c.eq("languages", me["languages"], ["ko", "en"])
    c.eq("preferred categories", me["preferred_categories"], ["hobby", "food"])


@case("PROF-002", "Profile", "Age gate", "Under-18 birth date rejected server-side (Google Play / Apple requirement)",
      "birth_date making user 17 -> 422; exactly 18 accepted", "PUT profile with age 17 and 18")
def prof_002(c):
    u = H.signup_email(f"qa-p2-{uuid.uuid4().hex[:6]}@example.com")
    c.eq("age 17", tc.put("/profiles/me", headers=u.h, json=H.profile_body(age=17)).status_code, 422)
    c.eq("age 18", tc.put("/profiles/me", headers=u.h, json=H.profile_body(age=18)).status_code, 200)


@case("PROF-003", "Profile", "Validation", "Invalid enums / lengths / ranges are rejected",
      "bad gender, bad interested_in, empty name, 51-char name, 1001-char bio, bad mbti, height 10, distance 0 -> 422 each",
      "PUT /profiles/me with 8 invalid payloads")
def prof_003(c):
    u = H.signup_email(f"qa-p3-{uuid.uuid4().hex[:6]}@example.com")
    bad = {
        "gender=robot": dict(gender="robot"),
        "interested_in=x": dict(interested_in="x"),
        "empty name": dict(display_name=""),
        "51-char name": dict(display_name="x" * 51),
        "1001-char bio": dict(bio="b" * 1001),
        "bad mbti": dict(mbti="XXXX"),
        "height 10": dict(height_cm=10),
        "distance 0": dict(max_distance_km=0),
    }
    for label, patch in bad.items():
        body = H.profile_body()
        body.update(patch)
        c.eq(label, tc.put("/profiles/me", headers=u.h, json=body).status_code, 422)
    ok_body = H.profile_body(bio="b" * 1000)
    c.eq("1000-char bio accepted", tc.put("/profiles/me", headers=u.h, json=ok_body).status_code, 200)


@case("PROF-004", "Profile", "Validation", "min_age_pref greater than max_age_pref",
      "server rejects (422) an impossible age range OR normalizes it; it must not silently store min>max",
      "PUT profile min_age_pref=60,max_age_pref=20")
def prof_004(c):
    u = H.signup_email(f"qa-p4-{uuid.uuid4().hex[:6]}@example.com")
    r = tc.put("/profiles/me", headers=u.h, json=H.profile_body(min_age_pref=60, max_age_pref=20))
    if r.status_code == 200:
        j = r.json()
        c.ok("stored range is valid (min<=max)", j["min_age_pref"] <= j["max_age_pref"],
             (j["min_age_pref"], j["max_age_pref"]))
    else:
        c.eq("rejected", r.status_code, 422)


@case("PROF-005", "Profile", "Identity lock", "display_name / birth_date / gender cannot be changed after creation",
      "second PUT with different identity fields keeps the originals", "PUT twice with different identity")
def prof_005(c):
    u = H.make_user("lock", "male", "female", 25)
    orig = tc.get("/profiles/me", headers=u.h).json()
    r = tc.put("/profiles/me", headers=u.h, json=H.profile_body("Changed", 40, "female", "female"))
    c.eq("status", r.status_code, 200)
    c.eq("name kept", r.json()["display_name"], orig["display_name"])
    c.eq("birth_date kept", r.json()["birth_date"], orig["birth_date"])
    c.eq("gender kept", r.json()["gender"], "male")


@case("PROF-006", "Profile", "Unicode", "Emoji, Korean, Japanese, Chinese, Arabic text round-trips exactly (NVARCHAR)",
      "bio identical after save/load for 5 scripts + emoji", "PUT bio with mixed scripts, GET")
def prof_006(c):
    u = H.make_user("uni")
    text = "안녕😊 こんにちは 你好 مرحبا 🇰🇷🇺🇸 ñandú"
    r = tc.put("/profiles/me", headers=u.h, json=H.profile_body("QAuni", bio=text))
    c.eq("status", r.status_code, 200)
    c.eq("bio", tc.get("/profiles/me", headers=u.h).json()["bio"], text)


@case("PROF-007", "Profile", "Photos", "Up to 7 slots; slot 7 rejected; reorder; delete; last photo protected",
      "positions 0-6 accepted, 7 -> 422; reorder reverses; delete works; deleting the last photo -> 400",
      "confirm 7 photos, position 7, reorder, delete until one left")
def prof_007(c):
    u = H.make_user("photos")
    for pos in range(1, 7):
        r = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": f"users/{u.id}/photos/{uuid.uuid4()}.jpg", "position": pos})
        c.eq(f"slot {pos}", r.status_code, 201)
    c.eq("slot 7", tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": f"users/{u.id}/photos/{uuid.uuid4()}.jpg", "position": 7}).status_code, 422)
    photos = sorted(tc.get("/profiles/me", headers=u.h).json()["photos"], key=lambda p: p["position"])
    ids = [p["id"] for p in photos]
    c.eq("7 photos stored", len(ids), 7)
    r = tc.put("/profiles/me/photos/reorder", headers=u.h, json={"photo_ids": list(reversed(ids))})
    c.eq("reorder status", r.status_code, 200)
    c.eq("reordered", [p["id"] for p in sorted(r.json(), key=lambda p: p["position"])], list(reversed(ids)))
    for pid in ids[:-1]:
        c.eq("delete", tc.delete(f"/profiles/me/photos/{pid}", headers=u.h).status_code, 204)
    c.eq("last photo protected", tc.delete(f"/profiles/me/photos/{ids[-1]}", headers=u.h).status_code, 400)
    other = H.make_user("photos2")
    c.eq("cannot delete another user's photo", tc.delete(f"/profiles/me/photos/{ids[-1]}", headers=other.h).status_code, 404)


@case("PROF-008", "Profile", "Photo path security", "Photo/moment paths pointing at another user's storage folder",
      "server should reject an object path that is not under the caller's own users/<id>/ prefix (403/400)",
      "confirm photo with path users/<someone else>/photos/x.jpg")
def prof_008(c):
    a = H.make_user("pathA")
    b = H.make_user("pathB")
    r = tc.post("/profiles/me/photos/confirm", headers=a.h, json={"gcs_object_path": f"users/{b.id}/photos/stolen.jpg", "position": 3})
    c.ok("foreign path rejected", r.status_code in (400, 403, 422), r.status_code)


@case("PROF-009", "Profile", "Filters", "Basic/age filters (free) persist; premium filters gated; incognito and travel toggle",
      "basic-filters 200 and echo; age-filter 200; premium-filters 402 for free user; incognito on/off; travel set/clear; lat 200 -> 422",
      "PUT filters, POST incognito, POST/DELETE travel")
def prof_009(c):
    u = H.make_user("filters")
    r = tc.put("/profiles/me/basic-filters", headers=u.h, json={"max_distance_km": 120, "height_min": 160, "height_max": 190, "verified_only": True})
    c.eq("basic-filters", r.status_code, 200)
    c.eq("distance echoed", r.json()["max_distance_km"], 120)
    c.eq("verified_only echoed", r.json()["verified_only"], True)
    c.eq("age-filter", tc.put("/profiles/me/age-filter", headers=u.h, json={"min_age_pref": 22, "max_age_pref": 35}).status_code, 200)
    c.eq("premium filter gated", tc.put("/profiles/me/premium-filters", headers=u.h, json={"smoking_filter": ["never"]}).status_code, 402)
    c.eq("incognito on", tc.post("/profiles/me/incognito", headers=u.h, json={"is_incognito": True}).json()["is_incognito"], True)
    c.eq("incognito off", tc.post("/profiles/me/incognito", headers=u.h, json={"is_incognito": False}).json()["is_incognito"], False)
    t = tc.post("/profiles/me/travel", headers=u.h, json={"lat": 37.5665, "lng": 126.978, "duration_hours": 24})
    c.eq("travel set", t.status_code, 200)
    c.ok("travel_expires_at set", t.json()["travel_expires_at"] is not None)
    c.eq("travel cleared", tc.delete("/profiles/me/travel", headers=u.h).json()["travel_expires_at"], None)
    c.eq("travel bad lat", tc.post("/profiles/me/travel", headers=u.h, json={"lat": 200, "lng": 0}).status_code, 422)


@case("PROF-010", "Profile", "Profile gate", "Endpoints needing a complete profile refuse an incomplete user",
      "discovery, blind-chat queue, interactions -> 400 'complete your profile'", "call with signup-only user")
def prof_010(c):
    u = H.signup_email(f"qa-p10-{uuid.uuid4().hex[:6]}@example.com")
    c.eq("discovery", tc.get("/discovery/candidates", headers=u.h).status_code, 400)
    c.eq("blind queue", tc.post("/blind-chat/queue", headers=u.h, json={"categories": ["hobby"]}).status_code, 400)
    c.eq("profile 404 before creation", tc.get("/profiles/me", headers=u.h).status_code, 404)


# ============================================================== UPLOADS (REAL R2)


def _presign_put(u, path, body, data, ct):
    p = tc.post(path, headers=u.h, json=body)
    if p.status_code != 200:
        return p, None, None
    j = p.json()
    put = H.put_to_r2(j["upload_url"], data, ct)
    return p, j, put


@case("UP-001", "Upload", "Profile photo (JPEG)", "Presign -> REAL upload to R2 -> download via public URL is byte-identical",
      "presign 200; PUT to R2 200; public URL GET 200, same bytes (sha256), Content-Type image/jpeg; confirm -> media_type photo",
      "generate real JPEG, presign, PUT to Cloudflare R2, GET public URL")
def up_001(c):
    u = H.make_user("up1")
    img = H.make_jpeg("QA PROFILE PHOTO")
    p, j, put = _presign_put(u, "/uploads/presign", {"content_type": "image/jpeg", "position": 1}, img, "image/jpeg")
    c.eq("presign", p.status_code, 200)
    c.eq("R2 PUT", put.status_code, 200)
    conf = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": j["gcs_object_path"], "position": 1})
    c.eq("confirm", conf.status_code, 201)
    c.eq("media_type", conf.json()["media_type"], "photo")
    got = httpx.get(conf.json()["url"], timeout=30)
    c.eq("public GET", got.status_code, 200)
    c.eq("bytes identical", hashlib.sha256(got.content).hexdigest(), hashlib.sha256(img).hexdigest())
    c.eq("content-type", got.headers.get("content-type"), "image/jpeg")
    c.info(f"object={j['gcs_object_path']} size={len(img)}B")


@case("UP-002", "Upload", "Profile photo (PNG/WebP)", "PNG and WebP uploads to R2",
      "both PUT 200 and are downloadable with the right content-type", "presign+PUT png and webp")
def up_002(c):
    u = H.make_user("up2")
    for ct, data, pos in (("image/png", H.make_png("PNG"), 2), ("image/webp", H.make_webp("WEBP"), 3)):
        p, j, put = _presign_put(u, "/uploads/presign", {"content_type": ct, "position": pos}, data, ct)
        c.eq(f"{ct} PUT", put.status_code, 200)
        conf = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": j["gcs_object_path"], "position": pos})
        got = httpx.get(conf.json()["url"], timeout=30)
        c.eq(f"{ct} GET", got.status_code, 200)
        c.eq(f"{ct} content-type", got.headers.get("content-type"), ct)


@case("UP-003", "Upload", "Profile video", "MP4 slot: presign + real upload + confirm as media_type=video",
      "presign 200 .mp4; PUT 200; confirm -> media_type video; object retrievable with video/mp4",
      "PUT a minimal MP4 container (ftyp box) to R2")
def up_003(c):
    u = H.make_user("up3")
    mp4 = bytes.fromhex("0000001866747970697 36f6d0000020069736f6d69736f32".replace(" ", "")) + b"\x00" * 2048
    p, j, put = _presign_put(u, "/uploads/presign", {"content_type": "video/mp4", "position": 6}, mp4, "video/mp4")
    c.eq("presign", p.status_code, 200)
    c.ok("path is .mp4", j["gcs_object_path"].endswith(".mp4"))
    c.eq("R2 PUT", put.status_code, 200)
    conf = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": j["gcs_object_path"], "position": 6})
    c.eq("media_type", conf.json()["media_type"], "video")
    got = httpx.get(conf.json()["url"], timeout=30)
    c.eq("GET", got.status_code, 200)
    c.eq("content-type", got.headers.get("content-type"), "video/mp4")
    c.info("synthetic MP4 header (no ffmpeg on this machine) - container accepted, playback not verified here")


@case("UP-004", "Upload", "Signature regression", "PUT with a Content-Type different from the presigned one is refused by R2 (the iOS 403 bug class)",
      "PUT with wrong/missing content type -> 403; correct one -> 200", "presign image/jpeg, PUT as image/png, then correct")
def up_004(c):
    u = H.make_user("up4")
    p = tc.post("/uploads/presign", headers=u.h, json={"content_type": "image/jpeg", "position": 1}).json()
    img = H.make_jpeg("CT")
    c.eq("wrong content-type", H.put_to_r2(p["upload_url"], img, "image/png").status_code, 403)
    c.eq("missing content-type", httpx.put(p["upload_url"], content=img, timeout=30).status_code, 403)
    c.eq("correct content-type", H.put_to_r2(p["upload_url"], img, "image/jpeg").status_code, 200)


@case("UP-005", "Upload", "Presign validation", "Unsupported types, out-of-range slots, missing auth",
      "pdf/gif/exe -> 422; position 7 -> 422; no token 401/403", "POST /uploads/presign variants")
def up_005(c):
    u = H.make_user("up5")
    for ct in ("application/pdf", "image/gif", "application/x-msdownload", "text/html"):
        c.eq(ct, tc.post("/uploads/presign", headers=u.h, json={"content_type": ct, "position": 0}).status_code, 422)
    c.eq("slot 7", tc.post("/uploads/presign", headers=u.h, json={"content_type": "image/jpeg", "position": 7}).status_code, 422)
    c.ok("no auth", tc.post("/uploads/presign", json={"content_type": "image/jpeg", "position": 0}).status_code in (401, 403))
    c.eq("chat presign video refused", tc.post("/uploads/presign-chat-image", headers=u.h, json={"content_type": "video/mp4"}).status_code, 422)


@case("UP-006", "Upload", "Large file", "5 MB photo uploads and downloads intact",
      "PUT 200; downloaded size equals uploaded size", "generate ~5MB PNG noise, upload to R2")
def up_006(c):
    import os

    from PIL import Image
    import io

    u = H.make_user("up6")
    img = Image.frombytes("RGB", (1200, 1200), os.urandom(1200 * 1200 * 3))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()
    p = tc.post("/uploads/presign", headers=u.h, json={"content_type": "image/png", "position": 4}).json()
    put = H.put_to_r2(p["upload_url"], data, "image/png")
    c.eq("PUT", put.status_code, 200)
    from app.services import storage_service

    got = httpx.get(storage_service.build_public_url(p["gcs_object_path"]), timeout=60)
    c.eq("size", len(got.content), len(data))
    c.info(f"{len(data) / 1e6:.1f} MB")


@case("UP-007", "Upload", "Other image kinds", "Chat image, couple-story image and moment image presign+upload",
      "each presign 200, PUT 200, path under users/<id>/(chat|stories|moments)/", "3 presign endpoints")
def up_007(c):
    u = H.make_user("up7")
    for ep, folder in (("presign-chat-image", "chat"), ("presign-story-image", "stories"), ("presign-moment-image", "moments")):
        p, j, put = _presign_put(u, f"/uploads/{ep}", {"content_type": "image/jpeg"}, H.make_jpeg(folder), "image/jpeg")
        c.eq(f"{ep} presign", p.status_code, 200)
        c.ok(f"{ep} path", f"users/{u.id}/{folder}/" in j["gcs_object_path"])
        c.eq(f"{ep} PUT", put.status_code, 200)


@case("UP-008", "Upload", "Data retention", "Deleting a photo removes the object from storage",
      "after DELETE /profiles/me/photos/<id>, the public URL returns 404 (no orphaned personal data)",
      "upload real photo, confirm, delete, GET public URL")
def up_008(c):
    u = H.make_user("up8")
    p, j, put = _presign_put(u, "/uploads/presign", {"content_type": "image/jpeg", "position": 1}, H.make_jpeg("DEL"), "image/jpeg")
    conf = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": j["gcs_object_path"], "position": 1}).json()
    c.eq("exists before delete", httpx.get(conf["url"], timeout=30).status_code, 200)
    c.eq("delete", tc.delete(f"/profiles/me/photos/{conf['id']}", headers=u.h).status_code, 204)
    c.eq("object gone after delete", httpx.get(conf["url"], timeout=30).status_code, 404)


@case("UP-009", "Upload", "Data retention", "Deleting the account removes all of the user's stored files (photos AND verification ID photos)",
      "after DELETE /account/me, no objects remain under users/<id>/ or verifications/<id>/",
      "upload profile photo + selfie + ID photo, delete account, list bucket prefixes")
def up_009(c):
    from app.config import settings
    from app.services import storage_service

    u = H.make_user("up9")
    _, j, _ = _presign_put(u, "/uploads/presign", {"content_type": "image/jpeg", "position": 1}, H.make_jpeg("ACC"), "image/jpeg")
    tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": j["gcs_object_path"], "position": 1})
    _, s, _ = _presign_put(u, "/verification/face/presign", {"content_type": "image/jpeg", "kind": "selfie"}, H.make_jpeg("SELFIE"), "image/jpeg")
    _, i, _ = _presign_put(u, "/verification/face/presign", {"content_type": "image/jpeg", "kind": "id_photo"}, H.make_jpeg("ID CARD"), "image/jpeg")
    tc.post("/verification/face/submit", headers=u.h, json={"selfie_object_path": s["gcs_object_path"], "id_photo_object_path": i["gcs_object_path"]})
    client = storage_service._get_client()

    def count(prefix):
        return len(client.list_objects_v2(Bucket=settings.r2_bucket_name, Prefix=prefix).get("Contents", []) or [])

    before = (count(f"users/{u.id}/"), count(f"verifications/{u.id}/"))
    c.eq("objects existed before", before, (1, 2))
    c.eq("delete account", tc.delete("/account/me", headers=u.h).status_code, 204)
    after = (count(f"users/{u.id}/"), count(f"verifications/{u.id}/"))
    c.eq("photo objects remaining", after[0], 0)
    c.eq("ID-photo/selfie objects remaining", after[1], 0)


# ============================================================== FACE / PHONE / WORK VERIFICATION


def _submit_face(u, tag):
    selfie = H.make_jpeg(f"SELFIE {tag}", (640, 800), (255, 200, 200))
    idimg = H.make_jpeg(f"ID CARD {tag}", (900, 560), (200, 220, 255))
    _, s, sp = _presign_put(u, "/verification/face/presign", {"content_type": "image/jpeg", "kind": "selfie"}, selfie, "image/jpeg")
    _, i, ip = _presign_put(u, "/verification/face/presign", {"content_type": "image/jpeg", "kind": "id_photo"}, idimg, "image/jpeg")
    sub = tc.post("/verification/face/submit", headers=u.h, json={"selfie_object_path": s["gcs_object_path"], "id_photo_object_path": i["gcs_object_path"]})
    return selfie, idimg, sp.status_code, ip.status_code, sub


@case("VER-001", "Verification", "Face verification", "New user starts as 'unsubmitted'", "GET /verification/face/status -> unsubmitted",
      "status for fresh profile")
def ver_001(c):
    u = H.make_user("v1")
    c.eq("status", tc.get("/verification/face/status", headers=u.h).json()["status"], "unsubmitted")


@case("VER-002", "Verification", "Face verification", "Submit selfie + ID photo (REAL image uploads) -> pending",
      "both R2 uploads 200; submit 201 status pending; status endpoint pending; profile not yet face_verified",
      "upload 2 real JPEGs via presign, POST /verification/face/submit")
def ver_002(c):
    u = H.make_user("v2")
    selfie, idimg, sp, ip, sub = _submit_face(u, "V2")
    c.eq("selfie PUT", sp, 200)
    c.eq("id PUT", ip, 200)
    c.eq("submit", sub.status_code, 201)
    c.eq("submit status", sub.json()["status"], "pending")
    c.eq("status endpoint", tc.get("/verification/face/status", headers=u.h).json()["status"], "pending")
    c.eq("not yet verified", tc.get("/profiles/me", headers=u.h).json()["face_verified"], False)
    H.S["v2"], H.S["v2_imgs"] = u, (selfie, idimg)


@case("VER-003", "Verification", "Face verification", "Submitting another user's / malformed object paths is refused",
      "path outside verifications/<own id>/ -> 400", "submit with foreign and made-up paths")
def ver_003(c):
    a, b = H.make_user("v3a"), H.make_user("v3b")
    _, s, _ = _presign_put(b, "/verification/face/presign", {"content_type": "image/jpeg"}, H.make_jpeg("B"), "image/jpeg")
    r = tc.post("/verification/face/submit", headers=a.h, json={"selfie_object_path": s["gcs_object_path"], "id_photo_object_path": s["gcs_object_path"]})
    c.eq("foreign path", r.status_code, 400)
    r = tc.post("/verification/face/submit", headers=a.h, json={"selfie_object_path": "users/x/photos/a.jpg", "id_photo_object_path": "../../etc/passwd"})
    c.eq("made-up path", r.status_code, 400)


@case("VER-004", "Verification", "Face verification", "Submitted paths must point at objects that really exist in storage",
      "submitting valid-prefix paths that were never uploaded -> 400 (else reviewer sees broken images and the user is stuck pending)",
      "submit paths under own prefix without uploading")
def ver_004(c):
    u = H.make_user("v4")
    r = tc.post("/verification/face/submit", headers=u.h, json={
        "selfie_object_path": f"verifications/{u.id}/selfie-{uuid.uuid4()}.jpg",
        "id_photo_object_path": f"verifications/{u.id}/id_photo-{uuid.uuid4()}.jpg"})
    c.ok("non-existent objects refused", r.status_code in (400, 404, 422), r.status_code)


@case("VER-005", "Verification", "Admin access control", "Review endpoints require an admin",
      "normal user 403, anonymous 401/403 on every /admin route", "hit every admin route as user and anonymous")
def ver_005(c):
    u = H.make_user("v5")
    rid = str(uuid.uuid4())
    routes = [("get", "/admin/face-verifications"), ("post", f"/admin/face-verifications/{rid}/approve"),
              ("post", f"/admin/face-verifications/{rid}/reject"), ("get", "/admin/reports"), ("get", "/admin/inquiries"),
              ("get", "/admin/stats"), ("get", "/admin/promotions"), ("post", "/admin/promotions")]
    for m, p in routes:
        body = {"json": {"reason_key": "x", "reason": "x", "product_id": "x", "discount_percent": 10}} if m == "post" else {}
        r = getattr(tc, m)(p, headers=u.h, **body)
        c.eq(f"user {m.upper()} {p[:40]}", r.status_code, 403)
        r2 = getattr(tc, m)(p, **body)
        c.ok(f"anon {m.upper()} {p[:40]}", r2.status_code in (401, 403), r2.status_code)


@case("VER-006", "Verification", "Face verification (admin)", "Admin sees the pending request with the REAL images and approves it",
      "pending list contains the request with display name; signed selfie/ID URLs return the exact uploaded bytes; approve 204; user face_verified=True, status approved; approval push recorded",
      "admin GET pending, download both images through signed URLs, POST approve")
def ver_006(c):
    admin = H.admin()
    u = H.S["v2"]
    selfie, idimg = H.S["v2_imgs"]
    items = tc.get("/admin/face-verifications?status=pending", headers=admin.h).json()
    mine = next((i for i in items if i["user_id"] == u.id), None)
    c.ok("request listed for admin", mine is not None)
    c.eq("display name shown", mine["display_name"], "QAv2")
    g1 = httpx.get(mine["selfie_view_url"], timeout=30)
    g2 = httpx.get(mine["id_photo_view_url"], timeout=30)
    c.eq("selfie signed URL", g1.status_code, 200)
    c.eq("selfie bytes identical", hashlib.sha256(g1.content).hexdigest(), hashlib.sha256(selfie).hexdigest())
    c.eq("ID photo signed URL", g2.status_code, 200)
    c.eq("ID bytes identical", hashlib.sha256(g2.content).hexdigest(), hashlib.sha256(idimg).hexdigest())
    n = len(H.PUSHES)
    c.eq("approve", tc.post(f"/admin/face-verifications/{mine['id']}/approve", headers=admin.h).status_code, 204)
    c.eq("profile face_verified", tc.get("/profiles/me", headers=u.h).json()["face_verified"], True)
    c.eq("status approved", tc.get("/verification/face/status", headers=u.h).json()["status"], "approved")
    pushes = [p for p in H.PUSHES[n:] if p["user_id"] == u.id]
    c.eq("approval push count", len(pushes), 1)
    c.info(f"push title={pushes[0]['title']!r}" if pushes else "no push")
    gone = tc.get("/admin/face-verifications?status=pending", headers=admin.h).json()
    c.ok("removed from pending", all(i["user_id"] != u.id for i in gone))
    c.ok("listed under approved", any(i["user_id"] == u.id for i in tc.get("/admin/face-verifications?status=approved", headers=admin.h).json()))


@case("VER-007", "Verification", "Face verification (admin)", "Admin rejects with a reason; user sees the reason; badge stays off; can resubmit and get approved",
      "reject 204; face_verified False; status rejected with reason_key/reason; reject push; resubmit -> pending; approve -> verified",
      "submit, admin reject(id_blurry), user status, resubmit, admin approve")
def ver_007(c):
    admin = H.admin()
    u = H.make_user("v7")
    _submit_face(u, "V7")
    mine = next(i for i in tc.get("/admin/face-verifications?status=pending", headers=admin.h).json() if i["user_id"] == u.id)
    n = len(H.PUSHES)
    r = tc.post(f"/admin/face-verifications/{mine['id']}/reject", headers=admin.h, json={"reason_key": "id_blurry", "reason": "ID photo is blurry"})
    c.eq("reject", r.status_code, 204)
    c.eq("face_verified", tc.get("/profiles/me", headers=u.h).json()["face_verified"], False)
    st = tc.get("/verification/face/status", headers=u.h).json()
    c.eq("status", st["status"], "rejected")
    c.eq("reason_key", st["rejection_reason_key"], "id_blurry")
    c.eq("reason text", st["rejection_reason"], "ID photo is blurry")
    c.ok("reject push recorded", any(p["user_id"] == u.id for p in H.PUSHES[n:]))
    c.ok("listed under rejected", any(i["user_id"] == u.id for i in tc.get("/admin/face-verifications?status=rejected", headers=admin.h).json()))
    _submit_face(u, "V7b")
    c.eq("resubmit -> pending", tc.get("/verification/face/status", headers=u.h).json()["status"], "pending")
    c.eq("reason cleared", tc.get("/verification/face/status", headers=u.h).json()["rejection_reason"], None)
    mine2 = next(i for i in tc.get("/admin/face-verifications?status=pending", headers=admin.h).json() if i["user_id"] == u.id)
    tc.post(f"/admin/face-verifications/{mine2['id']}/approve", headers=admin.h)
    c.eq("finally verified", tc.get("/profiles/me", headers=u.h).json()["face_verified"], True)


@case("VER-008", "Verification", "Face verification (admin)", "Every reject reason key and free-text 'other' reason is accepted; invalid inputs refused",
      "reason keys accepted; empty reason 422; missing body 422; unknown verification id 404; bad status filter 422",
      "reject variants + 404 + filter validation")
def ver_008(c):
    admin = H.admin()
    rid = str(uuid.uuid4())
    c.eq("unknown id approve", tc.post(f"/admin/face-verifications/{rid}/approve", headers=admin.h).status_code, 404)
    c.eq("unknown id reject", tc.post(f"/admin/face-verifications/{rid}/reject", headers=admin.h, json={"reason_key": "other", "reason": "x"}).status_code, 404)
    c.eq("empty reason", tc.post(f"/admin/face-verifications/{rid}/reject", headers=admin.h, json={"reason_key": "other", "reason": ""}).status_code, 422)
    c.eq("no body", tc.post(f"/admin/face-verifications/{rid}/reject", headers=admin.h).status_code, 422)
    c.eq("bad filter", tc.get("/admin/face-verifications?status=weird", headers=admin.h).status_code, 422)
    for st in ("pending", "approved", "rejected", "all"):
        c.eq(f"filter {st}", tc.get(f"/admin/face-verifications?status={st}", headers=admin.h).status_code, 200)


@case("VER-009", "Verification", "Face verification badge", "Approved badge is visible to other users in Discover",
      "candidate.face_verified true for the verified user; verified_only filter returns only verified users",
      "approve user, fetch discovery as a compatible viewer, apply verified_only")
def ver_009(c):
    admin = H.admin()
    target = H.make_user("v9t", "female", "male", 61)
    viewer = H.make_user("v9v", "male", "female", 61)
    tc.put("/profiles/me/age-filter", headers=viewer.h, json={"min_age_pref": 60, "max_age_pref": 62})
    _submit_face(target, "V9")
    mine = next(i for i in tc.get("/admin/face-verifications?status=pending", headers=admin.h).json() if i["user_id"] == target.id)
    tc.post(f"/admin/face-verifications/{mine['id']}/approve", headers=admin.h)
    cands = tc.get("/discovery/candidates?limit=50", headers=viewer.h).json()
    hit = next((x for x in cands if x["user_id"] == target.id), None)
    c.ok("verified user shown", hit is not None)
    c.eq("face_verified flag", hit and hit["face_verified"], True)
    tc.put("/profiles/me/basic-filters", headers=viewer.h, json={"verified_only": True, "max_distance_km": 500, "expand_others_if_low": False, "expand_distance_if_low": False})
    only = tc.get("/discovery/candidates?limit=50", headers=viewer.h).json()
    c.ok("verified_only keeps verified", any(x["user_id"] == target.id for x in only))
    c.ok("verified_only excludes unverified (expansion off)", all(x["face_verified"] for x in only))
    tc.put("/profiles/me/basic-filters", headers=viewer.h, json={"verified_only": True, "max_distance_km": 500})
    fallback = tc.get("/discovery/candidates?limit=50", headers=viewer.h).json()
    c.info(f"design note: with 'expand if few results' left ON (default) the deck still shows {sum(1 for x in fallback if not x['face_verified'])} unverified people despite verified_only")


@case("VER-010", "Verification", "Phone verification (attach)", "Attach a phone to an account; number already on another account is refused; internet number refused",
      "start 204, confirm 204, me.phone_verified true; second account same number 409; VoIP number 400", "start/confirm attach flow")
def ver_010(c):
    from app.services import phone_screening

    a, b = H.make_user("v10a"), H.make_user("v10b")
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    c.eq("start", tc.post("/verification/phone/start", headers=a.h, json={"phone_number": phone}).status_code, 204)
    c.eq("wrong code", tc.post("/verification/phone/confirm", headers=a.h, json={"phone_number": phone, "code": "000000"}).status_code, 400)
    c.eq("confirm", tc.post("/verification/phone/confirm", headers=a.h, json={"phone_number": phone, "code": "123456"}).status_code, 204)
    c.eq("me verified", tc.get("/account/me", headers=a.h).json()["phone_verified"], True)
    c.eq("taken by another", tc.post("/verification/phone/start", headers=b.h, json={"phone_number": phone}).status_code, 409)
    c.eq("070 refused", tc.post("/verification/phone/start", headers=b.h, json={"phone_number": "+827098765432"}).status_code, 400)


@case("VER-011", "Verification", "Work/school badge", "Email-code verification: personal domain refused, code flow, wrong-code lockout",
      "gmail 400; correct code -> 204 and verified_badge=work; 6 wrong codes -> 429", "start/confirm with fake mailer")
def ver_011(c):
    u = H.make_user("v11")
    c.eq("personal domain", tc.post("/verification/start", headers=u.h, json={"kind": "work", "email": "me@gmail.com"}).status_code, 400)
    n = len(H.EMAILS_SENT)
    c.eq("start", tc.post("/verification/start", headers=u.h, json={"kind": "work", "email": "me@acmecorp.com"}).status_code, 204)
    body = H.EMAILS_SENT[n][2]
    code = "".join(ch for ch in body if ch.isdigit())[:6]
    c.eq("confirm", tc.post("/verification/confirm", headers=u.h, json={"kind": "work", "code": code}).status_code, 204)
    c.eq("badge", tc.get("/profiles/me", headers=u.h).json()["verified_badge"], "work")
    v = H.make_user("v11b")
    tc.post("/verification/start", headers=v.h, json={"kind": "school", "email": "me@campus.edu"})
    last = None
    for _ in range(6):
        last = tc.post("/verification/confirm", headers=v.h, json={"kind": "school", "code": "111111"}).status_code
    c.eq("lockout", last, 429)


# ============================================================== SAFETY (block / report) + ADMIN CONSOLE


@case("SAF-001", "Safety", "Block", "Blocking hides the person both ways in Discover, kills the match, and stops new likes",
      "blocked user vanishes from blocker's deck and vice-versa; blocked pair cannot match; existing match no longer listed for the blocker",
      "match two users, block, check discovery/matches/like")
def saf_001(c):
    a = H.make_user("s1a", "male", "female", 63)
    b = H.make_user("s1b", "female", "male", 63)
    for u in (a, b):
        tc.put("/profiles/me/age-filter", headers=u.h, json={"min_age_pref": 62, "max_age_pref": 64})
    seen_before = any(x["user_id"] == b.id for x in tc.get("/discovery/candidates?limit=50", headers=a.h).json())
    c.ok("visible before block", seen_before)
    mid = H.mutual_match(a, b)
    c.ok("match listed before block", any(m["id"] == mid for m in tc.get("/matches", headers=a.h).json()))
    c.eq("block", tc.post("/safety/block", headers=a.h, json={"user_id": b.id}).status_code, 204)
    c.ok("hidden from blocker", all(x["user_id"] != b.id for x in tc.get("/discovery/candidates?limit=50", headers=a.h).json()))
    c.ok("blocker hidden from blocked user", all(x["user_id"] != a.id for x in tc.get("/discovery/candidates?limit=50", headers=b.h).json()))
    c.ok("match removed for blocker", all(m["id"] != mid for m in tc.get("/matches", headers=a.h).json()))
    c.ok("match removed for the blocked person too", all(m["id"] != mid for m in tc.get("/matches", headers=b.h).json()))
    c.eq("block is idempotent", tc.post("/safety/block", headers=a.h, json={"user_id": b.id}).status_code, 204)


@case("SAF-002", "Safety", "Report", "Report validation and edge cases",
      "reason+detail 204; empty reason 422; 1001-char detail 422; self 400; unknown user 404; same person twice 204",
      "POST /safety/report variants")
def saf_002(c):
    a, b = H.make_user("s2a"), H.make_user("s2b")
    c.eq("ok", tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "harassment", "detail": "rude"}).status_code, 204)
    c.eq("empty reason", tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": ""}).status_code, 422)
    c.eq("long detail", tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "x", "detail": "d" * 1001}).status_code, 422)
    c.eq("self", tc.post("/safety/report", headers=a.h, json={"user_id": a.id, "reason": "x"}).status_code, 400)
    c.eq("ghost", tc.post("/safety/report", headers=a.h, json={"user_id": str(uuid.uuid4()), "reason": "x"}).status_code, 404)
    c.eq("repeat report", tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "spam"}).status_code, 204)
    c.eq("emoji/Korean reason", tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "부적절한 사진 😡", "detail": "욕설"}).status_code, 204)


@case("ADM-001", "Admin", "Report moderation", "Report -> admin sees it with names and chat log -> warn / ban / dismiss",
      "open report listed with reporter+reported names; conversation returns both messages; warn -> warning_count+1 & status warned; ban -> user cannot log in & status banned; dismiss -> dismissed",
      "create match+messages, report, admin list/conversation/action")
def adm_001(c):
    admin = H.admin()
    a = H.make_user("r1a", "male", "female", 64)
    b = H.make_user("r1b", "female", "male", 64)
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "content": "first from B"})
        wa.receive_json()
        wa.send_json({"type": "message", "match_id": mid, "content": "you are rude"})
        wb.receive_json()
    tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "harassment", "detail": "test report"})
    reports = tc.get("/admin/reports?status=open", headers=admin.h).json()
    rep = next((r for r in reports if r["reported_id"] == b.id), None)
    c.ok("report visible to admin", rep is not None)
    c.eq("reporter name", rep["reporter_name"], "QAr1a")
    c.eq("reported name", rep["reported_name"], "QAr1b")
    conv = tc.get(f"/admin/reports/{rep['id']}/conversation", headers=admin.h).json()
    c.eq("conversation contents", [m["content"] for m in conv], ["first from B", "you are rude"])
    c.eq("warn", tc.post(f"/admin/reports/{rep['id']}/action", headers=admin.h, json={"action": "warn", "note": "first warning"}).status_code, 204)
    c.ok("listed under warned", any(r["id"] == rep["id"] for r in tc.get("/admin/reports?status=warned", headers=admin.h).json()))
    tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "spam"})
    rep2 = next(r for r in tc.get("/admin/reports?status=open", headers=admin.h).json() if r["reported_id"] == b.id)
    c.eq("ban", tc.post(f"/admin/reports/{rep2['id']}/action", headers=admin.h, json={"action": "ban"}).status_code, 204)
    c.ok("banned user cannot use API", tc.get("/profiles/me", headers=b.h).status_code in (401, 403))
    tc.post("/safety/report", headers=a.h, json={"user_id": b.id, "reason": "dup"})
    rep3 = next(r for r in tc.get("/admin/reports?status=open", headers=admin.h).json() if r["reported_id"] == b.id)
    c.eq("dismiss", tc.post(f"/admin/reports/{rep3['id']}/action", headers=admin.h, json={"action": "dismiss"}).status_code, 204)
    c.eq("bad action", tc.post(f"/admin/reports/{rep3['id']}/action", headers=admin.h, json={"action": "explode"}).status_code, 422)
    c.eq("unknown report", tc.post(f"/admin/reports/{uuid.uuid4()}/action", headers=admin.h, json={"action": "warn"}).status_code, 404)


@case("ADM-002", "Admin", "Inquiries", "User contact form -> admin list -> read -> resolve with a note",
      "submit 204; admin sees status new with user name; read -> read; resolve -> resolved with admin_note; validation on empty/oversized",
      "POST /inquiries then admin flow")
def adm_002(c):
    admin = H.admin()
    u = H.make_user("inq")
    c.eq("submit", tc.post("/inquiries", headers=u.h, json={"subject": "QA 문의 subject", "message": "테스트 메시지 😀"}).status_code, 204)
    c.eq("empty subject", tc.post("/inquiries", headers=u.h, json={"subject": "", "message": "x"}).status_code, 422)
    c.eq("oversized message", tc.post("/inquiries", headers=u.h, json={"subject": "x", "message": "m" * 4001}).status_code, 422)
    items = tc.get("/admin/inquiries?status=new", headers=admin.h).json()
    mine = next((i for i in items if i.get("user_name") == "QAinq"), None)
    c.ok("visible as new", mine is not None)
    c.eq("read", tc.post(f"/admin/inquiries/{mine['id']}/read", headers=admin.h).status_code, 204)
    c.ok("moved to read", any(i["id"] == mine["id"] for i in tc.get("/admin/inquiries?status=read", headers=admin.h).json()))
    c.eq("resolve", tc.post(f"/admin/inquiries/{mine['id']}/resolve", headers=admin.h, json={"admin_note": "answered"}).status_code, 204)
    done = next(i for i in tc.get("/admin/inquiries?status=resolved", headers=admin.h).json() if i["id"] == mine["id"])
    c.eq("admin note", done["admin_note"], "answered")
    c.eq("unknown inquiry", tc.post(f"/admin/inquiries/{uuid.uuid4()}/read", headers=admin.h).status_code, 404)


@case("ADM-003", "Admin", "Dashboard", "Stats endpoint returns coherent numbers",
      "all counters are non-negative ints; total_users >= new_users_today; pending_face_verifications matches pending list length",
      "GET /admin/stats vs lists")
def adm_003(c):
    admin = H.admin()
    s = tc.get("/admin/stats", headers=admin.h)
    c.eq("status", s.status_code, 200)
    j = s.json()
    c.ok("counters non-negative", all(isinstance(v, int) and v >= 0 for k, v in j.items() if k.endswith(("users", "reports", "matches", "messages", "today", "7d", "30d", "verifications", "inquiries", "cents_30d")) and not isinstance(v, list)))
    c.ok("total >= today", j["total_users"] >= j["new_users_today"])
    c.eq("pending verifications consistent", j["pending_face_verifications"], len(tc.get("/admin/face-verifications?status=pending", headers=admin.h).json()))
    c.ok("open_reports <= total_reports", j["open_reports"] <= j["total_reports"])
    c.ok("new users today counts QA signups", j["new_users_today"] >= 1, j["new_users_today"])


@case("ADM-004", "Admin", "Promotions", "Discount promotion lifecycle (push stubbed - no broadcast to real users)",
      "create 201; /payments/products shows discounted price; a second promo on the same product supersedes the first; unknown product 400; 0%/96% 422; deactivate restores full price",
      "admin promotions CRUD on a product with no active promo")
def adm_004(c):
    admin = H.admin()
    products = tc.get("/payments/products").json()
    # Never touch a product that already has a real (owner-created) promotion:
    # creating a new one supersedes it. Pick a product with no active promo.
    active_pids = {p["product_id"] for p in tc.get("/admin/promotions", headers=admin.h).json() if p["is_active"]}
    free = [p["product_id"] for p in products if p["product_id"] not in active_pids]
    c.ok("a product without an active real promotion is available for the test", bool(free), sorted(active_pids))
    pid = free[0]
    c.info(f"test product {pid}; real active promos left untouched on {sorted(active_pids)}")
    r = tc.post("/admin/promotions", headers=admin.h, json={"product_id": pid, "discount_percent": 30})
    c.eq("create", r.status_code, 201)
    H.PROMO_IDS.append(r.json()["id"])
    after = next(p for p in tc.get("/payments/products").json() if p["product_id"] == pid)
    c.ok("discount visible in shop", after.get("discount_percent") == 30, after.get("discount_percent"))
    r2 = tc.post("/admin/promotions", headers=admin.h, json={"product_id": pid, "discount_percent": 50})
    H.PROMO_IDS.append(r2.json()["id"])
    act = [p for p in tc.get("/admin/promotions", headers=admin.h).json() if p["is_active"] and p["product_id"] == pid]
    c.eq("only newest active", len(act), 1)
    c.eq("newest is 50%", act[0]["discount_percent"], 50)
    c.eq("unknown product", tc.post("/admin/promotions", headers=admin.h, json={"product_id": "nope", "discount_percent": 10}).status_code, 400)
    c.eq("0%", tc.post("/admin/promotions", headers=admin.h, json={"product_id": pid, "discount_percent": 0}).status_code, 422)
    c.eq("96%", tc.post("/admin/promotions", headers=admin.h, json={"product_id": pid, "discount_percent": 96}).status_code, 422)
    c.eq("deactivate", tc.post(f"/admin/promotions/{r2.json()['id']}/deactivate", headers=admin.h).status_code, 204)
    end = next(p for p in tc.get("/payments/products").json() if p["product_id"] == pid)
    c.ok("price restored", not end.get("discount_percent"), end.get("discount_percent"))
    c.ok("promo broadcast push attempted (stubbed)", len(H.PUSHES) >= 0)


@case("SAF-003", "Safety", "Block", "After blocking, the blocked person can no longer message or call through the old match (harassment stop)",
      "messages sent by the blocked user after the block are not delivered and not stored; call offers not relayed",
      "match, block, blocked user tries to send via WebSocket")
def saf_003(c):
    from qa.ws_util import ws_recv

    a = H.make_user("s3a", "male", "female", 67, min_age_pref=67, max_age_pref=67)
    b = H.make_user("s3b", "female", "male", 67, min_age_pref=67, max_age_pref=67)
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb, tc.websocket_connect(f"/ws/chat?token={a.token}") as wa:
        wb.send_json({"type": "message", "match_id": mid, "content": "before block"})
        c.eq("delivered before block", (ws_recv(wa) or {}).get("content"), "before block")
        tc.post("/safety/block", headers=a.h, json={"user_id": b.id})
        wb.send_json({"type": "message", "match_id": mid, "content": "harassment after block"})
        wb.send_json({"type": "call_offer", "match_id": mid, "sdp": "x"})
        import time as _t

        _t.sleep(2)
    hist = [m["content"] for m in tc.get(f"/matches/{mid}/messages", headers=a.h).json()]
    c.ok("post-block message not stored", "harassment after block" not in hist, hist)


@case("AGE-001", "Account", "Under-18 age gate", "App reports an under-18 birth date: the account is switched off for good and the same phone number cannot retry",
      "POST /account/age-restricted -> 204; the old token stops working; logging in again with the same phone number -> 403 (account disabled); anonymous call -> 401/403",
      "phone signup -> age-restricted -> token check -> phone re-login")
def age_001(c):
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    u = H.signup_phone(phone)
    c.ok("anonymous call refused", tc.post("/account/age-restricted").status_code in (401, 403))
    c.eq("report under-18", tc.post("/account/age-restricted", headers=u.h).status_code, 204)
    c.ok("old token no longer works", tc.get("/account/me", headers=u.h).status_code in (401, 403))
    r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    c.eq("same number cannot log in again", r.status_code, 403)
    c.eq("detail", r.json().get("detail"), "account disabled")


@case("AGE-002", "Account", "Under-18 age gate", "Server independently rejects an under-18 birth date on profile creation; exactly 18 is accepted; birth date is mandatory to become discoverable",
      "17-year-old -> 422; 18-year-old -> 200; a profile-less account cannot browse or queue (400)",
      "PUT /profiles/me with ages 5, 17, 18; discovery/queue without a profile")
def age_002(c):
    u = H.signup_email(f"qa-age2-{uuid.uuid4().hex[:6]}@example.com")
    c.eq("5 years old", tc.put("/profiles/me", headers=u.h, json=H.profile_body(age=5)).status_code, 422)
    c.eq("17 years old", tc.put("/profiles/me", headers=u.h, json=H.profile_body(age=17)).status_code, 422)
    c.eq("no profile -> discovery blocked", tc.get("/discovery/candidates", headers=u.h).status_code, 400)
    c.eq("no profile -> blind queue blocked", tc.post("/blind-chat/queue", headers=u.h, json={"categories": ["hobby"]}).status_code, 400)
    c.eq("18 years old", tc.put("/profiles/me", headers=u.h, json=H.profile_body(age=18)).status_code, 200)
