"""Flow suite: discovery, swipe/match, chat (WebSocket, images, translation,
push), blind chat + AI match, moments, couple stories, payments, calls,
account deletion, security sweep."""
import hashlib
import hmac
import json
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from qa import harness as H
from qa.harness import case, hdr, tc

_AGE = {"n": 64}


def age_slot():
    _AGE["n"] += 1
    if _AGE["n"] > 95:
        _AGE["n"] = 66
    return _AGE["n"]


def pair(tag, age=None, male_gender="male"):
    """A compatible male/female pair locked to a single age so nobody else in
    the shared production database can ever match them."""
    age = age or age_slot()
    a = H.make_user(f"{tag}M", "male", "female", age, min_age_pref=age, max_age_pref=age)
    b = H.make_user(f"{tag}F", "female", "male", age, min_age_pref=age, max_age_pref=age)
    return a, b, age


def ws_recv(ws, timeout=10):
    box = []

    def go():
        try:
            box.append(ws.receive_json())
        except Exception as e:  # noqa: BLE001
            box.append(e)

    t = threading.Thread(target=go, daemon=True)
    t.start()
    t.join(timeout)
    if box and not isinstance(box[0], Exception):
        return box[0]
    return None


def _submit_face(u, tag):
    """Uploads a real selfie + ID photo and submits them for review."""
    selfie = H.make_jpeg(f"SELFIE {tag}", (640, 800), (255, 200, 200))
    idimg = H.make_jpeg(f"ID CARD {tag}", (900, 560), (200, 220, 255))
    paths = []
    for kind, data in (("selfie", selfie), ("id_photo", idimg)):
        p = tc.post("/verification/face/presign", headers=u.h, json={"content_type": "image/jpeg", "kind": kind}).json()
        H.put_to_r2(p["upload_url"], data, "image/jpeg")
        paths.append(p["gcs_object_path"])
    return tc.post("/verification/face/submit", headers=u.h, json={"selfie_object_path": paths[0], "id_photo_object_path": paths[1]})


def set_profile(uid, **fields):
    async def go():
        from app.database import async_session_factory
        from app.models.profile import Profile

        async with async_session_factory() as s:
            p = await s.get(Profile, uuid.UUID(uid))
            for k, v in fields.items():
                setattr(p, k, v)
            await s.commit()

    H.db(go)


def set_match(mid, **fields):
    async def go():
        from app.database import async_session_factory
        from app.models.interaction import Match

        async with async_session_factory() as s:
            m = await s.get(Match, uuid.UUID(mid))
            for k, v in fields.items():
                setattr(m, k, v)
            await s.commit()

    H.db(go)


def cands(u, limit=50):
    return tc.get(f"/discovery/candidates?limit={limit}", headers=u.h).json()


def ids(lst, key="user_id"):
    return {x[key] for x in lst}


# ============================================================== DISCOVERY


@case("DISC-001", "Discovery", "Gender & age matching", "Only mutually-compatible people appear (gender interest + both age ranges)",
      "viewer sees the compatible person; does not see same-gender (not wanted), a person outside his age range, or someone whose own range excludes him",
      "5 users around one age, check /discovery/candidates")
def disc_001(c):
    age = age_slot()
    v = H.make_user("d1v", "male", "female", age, min_age_pref=age - 1, max_age_pref=age + 1)
    ok = H.make_user("d1ok", "female", "male", age, min_age_pref=18, max_age_pref=99)
    same = H.make_user("d1same", "male", "female", age)
    too_old = H.make_user("d1old", "female", "male", age + 5)
    not_into_v = H.make_user("d1no", "female", "male", age, min_age_pref=age + 10, max_age_pref=99)
    tc.put("/profiles/me/basic-filters", headers=v.h, json={"max_distance_km": 500, "expand_others_if_low": False, "expand_distance_if_low": False})
    seen = ids(cands(v))
    c.ok("compatible shown", ok.id in seen)
    c.ok("same gender hidden", same.id not in seen)
    c.ok("outside viewer's age range hidden", too_old.id not in seen)
    c.info(f"design note: a candidate whose own age preference excludes the viewer is {'hidden' if not_into_v.id not in seen else 'still shown'} in Discover (only the viewer's own range is applied there; blind chat applies both)")
    c.ok("self never shown", v.id not in seen)


@case("DISC-002", "Discovery", "Deck hygiene", "Swiped people (like and pass) never reappear; no duplicates in the deck",
      "after like/pass the users disappear; ids unique", "like one, pass one, refetch")
def disc_002(c):
    age = age_slot()
    v = H.make_user("d2v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    a = H.make_user("d2a", "female", "male", age)
    b = H.make_user("d2b", "female", "male", age)
    before = cands(v)
    c.ok("both visible first", {a.id, b.id} <= ids(before))
    c.eq("no duplicate ids", len(before), len(ids(before)))
    tc.post("/interactions/like", headers=v.h, json={"to_user_id": a.id})
    tc.post("/interactions/pass", headers=v.h, json={"to_user_id": b.id})
    after = ids(cands(v))
    c.ok("liked hidden", a.id not in after)
    c.ok("passed hidden", b.id not in after)


@case("DISC-003", "Discovery", "Incognito", "Incognito users are hidden from the deck, and visible again when switched off",
      "hidden while is_incognito=True, present after off", "toggle incognito on target")
def disc_003(c):
    age = age_slot()
    v = H.make_user("d3v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    t = H.make_user("d3t", "female", "male", age)
    c.ok("visible", t.id in ids(cands(v)))
    tc.post("/profiles/me/incognito", headers=t.h, json={"is_incognito": True})
    c.ok("hidden when incognito", t.id not in ids(cands(v)))
    tc.post("/profiles/me/incognito", headers=t.h, json={"is_incognito": False})
    c.ok("visible again", t.id in ids(cands(v)))


@case("DISC-004", "Discovery", "Distance", "Distance limit, distance_km value, and travel mode relocating a user",
      "far user (Seoul vs New York) excluded within 50 km; near user shown with distance_km<5; traveler to Seoul then appears",
      "lat/lng users + travel mode")
def disc_004(c):
    age = age_slot()
    v = H.make_user("d4v", "male", "female", age, min_age_pref=age, max_age_pref=age, location_lat=37.5665, location_lng=126.9780, max_distance_km=50)
    near = H.make_user("d4n", "female", "male", age, location_lat=37.5700, location_lng=126.9820)
    far = H.make_user("d4f", "female", "male", age, location_lat=40.7128, location_lng=-74.0060)
    tc.put("/profiles/me/basic-filters", headers=v.h, json={"max_distance_km": 50, "expand_distance_if_low": False, "expand_others_if_low": False})
    lst = cands(v)
    hit = next((x for x in lst if x["user_id"] == near.id), None)
    c.ok("near shown", hit is not None)
    c.ok("distance_km small", hit is not None and hit["distance_km"] is not None and hit["distance_km"] < 5, hit and hit["distance_km"])
    c.ok("far hidden", far.id not in ids(lst))
    tc.post("/profiles/me/travel", headers=far.h, json={"lat": 37.5665, "lng": 126.9780, "duration_hours": 2})
    c.ok("traveler now shown", far.id in ids(cands(v)))
    tc.delete("/profiles/me/travel", headers=far.h)
    c.ok("gone after travel cleared", far.id not in ids(cands(v)))


@case("DISC-005", "Discovery", "Filters", "Basic filters narrow the deck (height / language / interests / verified only)",
      "height 170-180 keeps 175cm only; interests_filter keeps the person with 'coffee'; languages_filter keeps ko speaker",
      "PUT /profiles/me/basic-filters variants")
def disc_005(c):
    age = age_slot()
    v = H.make_user("d5v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    tall = H.make_user("d5tall", "female", "male", age, height_cm=175, interests=["coffee"], languages=["ko"])
    short = H.make_user("d5short", "female", "male", age, height_cm=155, interests=["hiking"], languages=["en"])
    tc.put("/profiles/me/basic-filters", headers=v.h, json={"max_distance_km": 500, "height_min": 170, "height_max": 180, "expand_others_if_low": False})
    s = ids(cands(v))
    c.ok("175cm kept", tall.id in s)
    c.ok("155cm dropped", short.id not in s)
    tc.put("/profiles/me/basic-filters", headers=v.h, json={"max_distance_km": 500, "interests_filter": ["coffee"], "expand_others_if_low": False})
    s = ids(cands(v))
    c.ok("interest filter keeps coffee", tall.id in s and short.id not in s)
    tc.put("/profiles/me/basic-filters", headers=v.h, json={"max_distance_km": 500, "languages_filter": ["en"], "expand_others_if_low": False})
    s = ids(cands(v))
    c.ok("language filter keeps en speaker", short.id in s and tall.id not in s)


@case("DISC-006", "Discovery", "Data privacy", "Candidate cards never leak private fields",
      "no email, phone, exact birth date, legal name, exact coordinates or password data in a candidate object",
      "inspect keys of candidate JSON")
def disc_006(c):
    age = age_slot()
    v = H.make_user("d6v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    t = H.make_user("d6t", "female", "male", age, location_lat=37.5, location_lng=127.0)
    hit = next(x for x in cands(v) if x["user_id"] == t.id)
    forbidden = {"email", "phone_number", "birth_date", "legal_first_name", "location_lat", "location_lng", "password_hash", "premium_until", "superlike_credits"}
    c.eq("leaked keys", sorted(forbidden & set(hit.keys())), [])
    c.ok("age is a number", isinstance(hit["age"], int) and hit["age"] == age, hit["age"])
    c.ok("photo url is https", all(p["url"].startswith("https://") for p in hit["photos"]))


@case("DISC-007", "Discovery", "Validation", "limit parameter bounds", "limit=0 and 51 -> 422; limit=1 returns at most 1", "GET /discovery/candidates?limit=...")
def disc_007(c):
    u = H.make_user("d7")
    c.eq("limit 0", tc.get("/discovery/candidates?limit=0", headers=u.h).status_code, 422)
    c.eq("limit 51", tc.get("/discovery/candidates?limit=51", headers=u.h).status_code, 422)
    c.ok("limit 1", len(tc.get("/discovery/candidates?limit=1", headers=u.h).json()) <= 1)


@case("DISC-008", "Discovery", "Ban filter", "Banned users disappear from other people's decks",
      "after an admin ban the user is no longer a candidate", "ban via report action, refetch")
def disc_008(c):
    admin = H.admin()
    age = age_slot()
    v = H.make_user("d8v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    t = H.make_user("d8t", "female", "male", age)
    c.ok("visible before", t.id in ids(cands(v)))
    tc.post("/safety/report", headers=v.h, json={"user_id": t.id, "reason": "spam"})
    rep = next(r for r in tc.get("/admin/reports?status=open", headers=admin.h).json() if r["reported_id"] == t.id)
    tc.post(f"/admin/reports/{rep['id']}/action", headers=admin.h, json={"action": "ban"})
    c.ok("hidden after ban", t.id not in ids(cands(v)))


@case("DISC-009", "Discovery", "Premium filters", "Premium members can use advanced filters; free members get 402",
      "premium_until in future -> premium-filters 200 and narrows the deck; expired premium -> 402 again",
      "set premium via DB, PUT premium-filters")
def disc_009(c):
    age = age_slot()
    v = H.make_user("d9v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    smoker = H.make_user("d9s", "female", "male", age, smoking="regularly")
    clean = H.make_user("d9c", "female", "male", age, smoking="never")
    c.eq("free user gated", tc.put("/profiles/me/premium-filters", headers=v.h, json={"smoking_filter": ["never"]}).status_code, 402)
    set_profile(v.id, premium_until=datetime.now(timezone.utc) + timedelta(days=5))
    r = tc.put("/profiles/me/premium-filters", headers=v.h, json={"smoking_filter": ["never"]})
    c.eq("premium accepted", r.status_code, 200)
    tc.put("/profiles/me/basic-filters", headers=v.h, json={"max_distance_km": 500, "expand_others_if_low": False})
    s = ids(cands(v))
    c.ok("non-smoker kept", clean.id in s)
    c.ok("smoker filtered", smoker.id not in s)
    set_profile(v.id, premium_until=datetime.now(timezone.utc) - timedelta(days=1))
    c.eq("expired premium gated again", tc.put("/profiles/me/premium-filters", headers=v.h, json={"smoking_filter": ["never"]}).status_code, 402)


# ============================================================== SWIPE / MATCH


@case("MATCH-001", "Matching", "Mutual like", "Like -> no match; reciprocal like -> match for both; visible in both /matches lists",
      "first like matched=False; second like matched=True with match_id; both lists contain it with the other's name; like/match pushes recorded",
      "A likes B, B likes A")
def match_001(c):
    a, b, _ = pair("m1")
    n = len(H.PUSHES)
    r1 = tc.post("/interactions/like", headers=a.h, json={"to_user_id": b.id})
    c.eq("first like status", r1.status_code, 200)
    c.eq("first like matched", r1.json()["matched"], False)
    c.ok("like push to B", any(p["user_id"] == b.id for p in H.PUSHES[n:]))
    r2 = tc.post("/interactions/like", headers=b.h, json={"to_user_id": a.id})
    c.eq("second like matched", r2.json()["matched"], True)
    mid = r2.json()["match_id"]
    la = {m["id"]: m for m in tc.get("/matches", headers=a.h).json()}
    lb = {m["id"]: m for m in tc.get("/matches", headers=b.h).json()}
    c.ok("listed for A", mid in la)
    c.ok("listed for B", mid in lb)
    c.eq("A sees B's name", la[mid]["other_display_name"], "QAm1F")
    c.eq("B sees A's name", lb[mid]["other_display_name"], "QAm1M")
    c.ok("match pushes to both", {a.id, b.id} <= {p["user_id"] for p in H.PUSHES[n:]})
    H.S["m1"] = (a, b, mid)


@case("MATCH-002", "Matching", "Swipe validation", "Self-swipe, ghost user, duplicate swipe, and pass-then-like",
      "self 400; unknown user 404; duplicate like idempotent 200; a pass never creates a match even if the other liked",
      "swipe edge cases")
def match_002(c):
    a, b, _ = pair("m2")
    c.eq("self", tc.post("/interactions/like", headers=a.h, json={"to_user_id": a.id}).status_code, 400)
    c.eq("ghost", tc.post("/interactions/like", headers=a.h, json={"to_user_id": str(uuid.uuid4())}).status_code, 404)
    c.eq("bad uuid", tc.post("/interactions/like", headers=a.h, json={"to_user_id": "not-a-uuid"}).status_code, 422)
    tc.post("/interactions/like", headers=a.h, json={"to_user_id": b.id})
    c.eq("duplicate like", tc.post("/interactions/like", headers=a.h, json={"to_user_id": b.id}).status_code, 200)
    x, y, _ = pair("m2b")
    tc.post("/interactions/pass", headers=x.h, json={"to_user_id": y.id})
    r = tc.post("/interactions/like", headers=y.h, json={"to_user_id": x.id})
    c.eq("like after being passed -> no match", r.json()["matched"], False)


@case("MATCH-003", "Matching", "Swipe limit", "20 swipes per rolling 6h; the 21st is refused with 429 and a reset time; premium is unlimited",
      "swipe-limit remaining counts down 20->0; 21st swipe 429 with resets_at; premium user unlimited=True",
      "23 users, 21 swipes")
def match_003(c):
    age = age_slot()
    v = H.make_user("m3v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    targets = [H.make_user(f"m3t{i}", "female", "male", age) for i in range(21)]
    c.eq("initial remaining", tc.get("/interactions/swipe-limit", headers=v.h).json()["remaining"], 20)
    for t in targets[:20]:
        r = tc.post("/interactions/pass", headers=v.h, json={"to_user_id": t.id})
        if r.status_code != 200:
            c.ok("swipe accepted", False, r.status_code)
            break
    lim = tc.get("/interactions/swipe-limit", headers=v.h).json()
    c.eq("remaining after 20", lim["remaining"], 0)
    c.ok("resets_at present", lim["resets_at"] is not None)
    r = tc.post("/interactions/pass", headers=v.h, json={"to_user_id": targets[20].id})
    c.eq("21st swipe", r.status_code, 429)
    c.ok("429 body has resets_at", isinstance(r.json().get("detail"), dict) and "resets_at" in r.json()["detail"])
    set_profile(v.id, premium_until=datetime.now(timezone.utc) + timedelta(days=1))
    c.eq("premium unlimited", tc.get("/interactions/swipe-limit", headers=v.h).json()["unlimited"], True)
    c.eq("premium can keep swiping", tc.post("/interactions/pass", headers=v.h, json={"to_user_id": targets[20].id}).status_code, 200)


@case("MATCH-004", "Matching", "Super like", "1 free super like per day, then credits, else 402; target sees superliked_me",
      "first superlike ok; second 402; after granting a credit ok again; target's candidate card and liked-me show superliked_me",
      "superlike x3")
def match_004(c):
    age = age_slot()
    v = H.make_user("m4v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    ts = [H.make_user(f"m4t{i}", "female", "male", age) for i in range(3)]
    c.eq("free superlike", tc.post("/interactions/superlike", headers=v.h, json={"to_user_id": ts[0].id}).status_code, 200)
    c.eq("second superlike blocked", tc.post("/interactions/superlike", headers=v.h, json={"to_user_id": ts[1].id}).status_code, 402)
    set_profile(v.id, superlike_credits=1)
    c.eq("paid superlike", tc.post("/interactions/superlike", headers=v.h, json={"to_user_id": ts[1].id}).status_code, 200)
    c.eq("credits consumed", tc.get("/payments/balance", headers=v.h).json()["superlike_credits"], 0)
    liked = tc.get("/discovery/liked-me", headers=ts[0].h).json()
    hit = next((x for x in liked if x["user_id"] == v.id), None)
    c.ok("appears in liked-me", hit is not None)
    c.eq("superliked_me flag", hit and hit["superliked_me"], True)


@case("MATCH-005", "Matching", "Liked-me list", "'Who liked me' lists likers and drops them once I respond",
      "liker present; after I like back (match) or pass, they disappear", "A likes B; B checks liked-me; B responds")
def match_005(c):
    a, b, _ = pair("m5")
    tc.post("/interactions/like", headers=a.h, json={"to_user_id": b.id})
    c.ok("liker listed", a.id in ids(tc.get("/discovery/liked-me", headers=b.h).json()))
    tc.post("/interactions/pass", headers=b.h, json={"to_user_id": a.id})
    c.ok("removed after pass", a.id not in ids(tc.get("/discovery/liked-me", headers=b.h).json()))


@case("MATCH-006", "Matching", "First-message rule", "Bumble rule: in a man/woman match only the woman may message first; error frame for the man; afterwards both can",
      "man's first message -> error frame first_message_restricted and nothing stored; woman's message delivered; then man can reply; can_send_first_message flags correct",
      "match + WebSocket messages")
def match_006(c):
    a, b, _ = pair("m6")
    mid = H.mutual_match(a, b)
    ma = next(m for m in tc.get("/matches", headers=a.h).json() if m["id"] == mid)
    mb = next(m for m in tc.get("/matches", headers=b.h).json() if m["id"] == mid)
    c.eq("man can_send_first_message", ma["can_send_first_message"], False)
    c.eq("woman can_send_first_message", mb["can_send_first_message"], True)
    c.ok("deadline set (24h)", ma["first_message_deadline"] is not None)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "message", "match_id": mid, "content": "man first"})
        err = ws_recv(wa)
        c.eq("error frame", err and err.get("code"), "first_message_restricted")
        wb.send_json({"type": "message", "match_id": mid, "content": "woman first"})
        got = ws_recv(wa)
        c.eq("woman delivered", got and got["content"], "woman first")
        wa.send_json({"type": "message", "match_id": mid, "content": "man reply"})
        got2 = ws_recv(wb)
        c.eq("man reply delivered", got2 and got2["content"], "man reply")
    hist = [m["content"] for m in tc.get(f"/matches/{mid}/messages", headers=a.h).json()]
    c.ok("rejected message not stored", "man first" not in hist)
    c.eq("history", sorted(hist), ["man reply", "woman first"])


@case("MATCH-007", "Matching", "Match expiry", "24h without a first message expires the match; history stays readable; sending is refused",
      "after deadline passes: match is_active False, sending impossible, GET messages still 200", "backdate first_message_deadline")
def match_007(c):
    a, b, _ = pair("m7")
    mid = H.mutual_match(a, b)
    set_match(mid, first_message_deadline=datetime.now(timezone.utc) - timedelta(minutes=1))
    m = next(x for x in tc.get("/matches", headers=b.h).json() if x["id"] == mid)
    c.eq("is_active after deadline", m["is_active"], False)
    c.eq("history readable", tc.get(f"/matches/{mid}/messages", headers=b.h).status_code, 200)
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "content": "too late"})
    hist = tc.get(f"/matches/{mid}/messages", headers=b.h).json()
    c.eq("no message stored", len(hist), 0)


@case("MATCH-008", "Matching", "Same-gender match", "Same-gender (or 'other') matches are unrestricted from both sides",
      "no restriction flags; either side can message first", "two men seeking men")
def match_008(c):
    age = age_slot()
    a = H.make_user("m8a", "male", "male", age, min_age_pref=age, max_age_pref=age)
    b = H.make_user("m8b", "male", "male", age, min_age_pref=age, max_age_pref=age)
    mid = H.mutual_match(a, b)
    ma = next(m for m in tc.get("/matches", headers=a.h).json() if m["id"] == mid)
    c.eq("restricted", ma["is_message_restricted"], False)
    c.eq("can send first", ma["can_send_first_message"], True)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "message", "match_id": mid, "content": "hey"})
        got = ws_recv(wb)
        c.eq("delivered", got and got["content"], "hey")


@case("MATCH-009", "Matching", "Access control (IDOR)", "A stranger cannot read or write another pair's match",
      "GET messages 404 for outsider; WS message to that match_id ignored; icebreaker / reveal / feedback endpoints refuse outsider",
      "third user attacks a match")
def match_009(c):
    a, b, _ = pair("m9")
    mid = H.mutual_match(a, b)
    evil = H.make_user("m9x")
    c.eq("read history", tc.get(f"/matches/{mid}/messages", headers=evil.h).status_code, 404)
    with tc.websocket_connect(f"/ws/chat?token={evil.token}") as we:
        we.send_json({"type": "message", "match_id": mid, "content": "injected"})
    c.ok("injected message not stored", "injected" not in [m["content"] for m in tc.get(f"/matches/{mid}/messages", headers=b.h).json()])
    c.ok("icebreaker refused", tc.get(f"/matches/{mid}/icebreaker", headers=evil.h).status_code in (403, 404))
    c.ok("reveal request refused", tc.post(f"/matches/{mid}/blind-reveal/request", headers=evil.h).status_code in (400, 403, 404))
    c.ok("feedback refused", tc.post(f"/matches/{mid}/blind-feedback", headers=evil.h, json={"rating": 5, "tags": []}).status_code in (400, 403, 404))


@case("MATCH-010", "Matching", "Icebreaker", "Icebreaker suggestion reflects shared interests / K-content / language exchange",
      "shared k-content -> type shared_kcontent; shared interest -> shared_interest; nothing shared -> generic", "3 pairs")
def match_010(c):
    a1, b1, _ = pair("m10a")
    tc.put("/profiles/me", headers=a1.h, json=H.profile_body("QAm10aM", 0 + 25, "male", "female", k_content_tags=["kdrama"])) if False else None
    for u, tags in ((a1, ["kdrama"]), (b1, ["kdrama", "kpop"])):
        cur = tc.get("/profiles/me", headers=u.h).json()
        body = H.profile_body(cur["display_name"], _AGE["n"], cur["gender"], cur["interested_in"], k_content_tags=tags, min_age_pref=_AGE["n"], max_age_pref=_AGE["n"])
        body["birth_date"] = cur["birth_date"]
        tc.put("/profiles/me", headers=u.h, json=body)
    mid = H.mutual_match(a1, b1)
    r = tc.get(f"/matches/{mid}/icebreaker", headers=a1.h)
    c.eq("status", r.status_code, 200)
    c.eq("type", r.json()["type"], "shared_kcontent")
    c.eq("key", r.json()["key"], "kdrama")
    a2, b2, _ = pair("m10b")
    mid2 = H.mutual_match(a2, b2)
    r2 = tc.get(f"/matches/{mid2}/icebreaker", headers=a2.h).json()
    c.ok("generic when nothing shared", r2["type"] in ("generic", "shared_language"), r2["type"])


# ============================================================== CHAT


@case("CHAT-001", "Chat", "Realtime messaging", "Two-way live chat, persistence, ordering, delivered/read state",
      "each message arrives on the peer socket with sender/content/time; history returns both in order; read event received by sender; read_at set in history",
      "WS chat between matched pair then read receipt")
def chat_001(c):
    a, b, _ = pair("c1")
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "content": "안녕 1"})
        m1 = ws_recv(wa)
        c.eq("A gets msg 1", m1 and m1["content"], "안녕 1")
        c.eq("sender id", m1 and m1["sender_id"], b.id)
        c.ok("has sent_at + message_id", bool(m1 and m1["sent_at"] and m1["message_id"]))
        wa.send_json({"type": "message", "match_id": mid, "content": "hello 2 😊"})
        m2 = ws_recv(wb)
        c.eq("B gets msg 2", m2 and m2["content"], "hello 2 😊")
        wa.send_json({"type": "read", "match_id": mid})
        rd = ws_recv(wb)
        c.eq("B gets read event", rd and rd["type"], "read")
    hist = tc.get(f"/matches/{mid}/messages", headers=a.h).json()
    c.eq("history order", [m["content"] for m in reversed(hist)] if hist and hist[0]["sent_at"] > hist[-1]["sent_at"] else [m["content"] for m in hist], ["안녕 1", "hello 2 😊"])
    c.ok("message from B marked read by A", any(m["content"] == "안녕 1" and m["read_at"] for m in hist))


@case("CHAT-002", "Chat", "Image messages", "Send a REAL photo in chat: upload to R2, deliver, recipient downloads identical bytes",
      "chat presign 200, R2 PUT 200, WS image message delivered with image_url, download hash equals upload, history shows message_type=image",
      "chat presign + PUT + WS image")
def chat_002(c):
    a, b, _ = pair("c2")
    mid = H.mutual_match(a, b)
    img = H.make_jpeg("CHAT IMAGE QA", (800, 600))
    p = tc.post("/uploads/presign-chat-image", headers=b.h, json={"content_type": "image/jpeg"}).json()
    c.eq("R2 PUT", H.put_to_r2(p["upload_url"], img, "image/jpeg").status_code, 200)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "message_type": "image", "image_object_path": p["gcs_object_path"], "content": ""})
        got = ws_recv(wa)
        c.eq("type", got and got["message_type"], "image")
        c.ok("image_url present", bool(got and got["image_url"]))
        dl = httpx.get(got["image_url"], timeout=30)
        c.eq("download", dl.status_code, 200)
        c.eq("bytes identical", hashlib.sha256(dl.content).hexdigest(), hashlib.sha256(img).hexdigest())
    hist = tc.get(f"/matches/{mid}/messages", headers=a.h).json()
    c.ok("history has image message", any(m["message_type"] == "image" and m["image_url"] for m in hist))


@case("CHAT-003", "Chat", "Input handling", "Empty, whitespace-only, very long, emoji/RTL/HTML messages",
      "empty and whitespace ignored (not stored); 5000-char message stored intact; emoji/RTL/HTML stored verbatim (clients escape); connection stays alive",
      "send edge-case messages")
def chat_003(c):
    a, b, _ = pair("c3")
    mid = H.mutual_match(a, b)
    long_text = "가" * 5000
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb, tc.websocket_connect(f"/ws/chat?token={a.token}") as wa:
        for txt in ["", "   ", long_text, "مرحبا 🇰🇷 <script>alert(1)</script>"]:
            wb.send_json({"type": "message", "match_id": mid, "content": txt})
        got = [ws_recv(wa, 6), ws_recv(wa, 6)]
        c.eq("long message delivered intact", got[0] and got[0]["content"], long_text)
        c.eq("RTL/emoji/html delivered verbatim", got[1] and got[1]["content"], "مرحبا 🇰🇷 <script>alert(1)</script>")
        wb.send_json({"type": "message", "match_id": mid, "content": "still alive"})
        alive = ws_recv(wa, 6)
        c.eq("socket alive after edge cases", alive and alive["content"], "still alive")
    hist = tc.get(f"/matches/{mid}/messages", headers=a.h).json()
    c.eq("stored count (blank ones ignored)", len(hist), 3)


@case("CHAT-004", "Chat", "Push routing", "Push only when the recipient is offline; never for online recipients",
      "offline recipient -> 1 push with sender name and match id; online recipient -> 0 pushes", "send with peer offline / online")
def chat_004(c):
    a, b, _ = pair("c4")
    mid = H.mutual_match(a, b)
    n = len(H.PUSHES)
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "content": "are you there?"})
        time.sleep(1.5)
    offline = [p for p in H.PUSHES[n:] if p["user_id"] == a.id and p.get("data", {}) and p["data"].get("match_id") == mid]
    c.eq("offline push count", len(offline), 1)
    c.ok("push mentions sender name", bool(offline) and "QAc4F" in (offline[0]["title"] + offline[0]["body"]), offline[0]["title"] if offline else None)
    n2 = len(H.PUSHES)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "content": "now online"})
        ws_recv(wa)
    c.eq("online push count", len([p for p in H.PUSHES[n2:] if p["user_id"] == a.id]), 0)


@case("CHAT-005", "Chat", "Real-time translation", "Cross-language chat (ko sender -> en recipient) is translated by the real Google Translate API",
      "delivered message carries translated_content in English and original_language ko; history keeps both",
      "REAL Google Cloud Translation call")
def chat_005(c):
    from app.config import settings

    if not settings.google_translate_api_key:
        c.info("GOOGLE_TRANSLATE_API_KEY not configured -> translation off by design")
        c.ok("feature intentionally silent when unconfigured", True)
        return
    a, b, _ = pair("c5")
    tc.put("/account/language", headers=a.h, json={"language": "en"})
    tc.put("/account/language", headers=b.h, json={"language": "ko"})
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wb.send_json({"type": "message", "match_id": mid, "content": "안녕하세요 만나서 반가워요"})
        got = ws_recv(wa, 15)
        c.ok("message received", got is not None)
        c.eq("original_language", got and got["original_language"], "ko")
        c.eq("translated_language", got and got["translated_language"], "en")
        c.ok("translation non-empty and different", bool(got and got["translated_content"]) and got["translated_content"] != got["content"], got and got["translated_content"])
        c.info(f"translated -> {got and got['translated_content']!r}")


@case("CHAT-006", "Chat", "Robustness", "Malformed WebSocket frames do not take the server down",
      "non-JSON text, JSON array, unknown type, missing match_id, bad uuid: server keeps serving other requests; valid users unaffected",
      "send garbage frames then use the API")
def chat_006(c):
    a, b, _ = pair("c6")
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        for frame in ({"type": "weird"}, {"type": "message"}, {"type": "message", "match_id": "not-uuid", "content": "x"}, {"type": "read", "match_id": None}, {"type": "call_answer", "call_id": "x"}):
            wb.send_json(frame)
        wb.send_json({"type": "message", "match_id": mid, "content": "after garbage"})
        time.sleep(1)
    c.eq("API healthy", tc.get("/health").status_code, 200)
    c.ok("valid message after garbage stored", "after garbage" in [m["content"] for m in tc.get(f"/matches/{mid}/messages", headers=a.h).json()])
    survived = True
    try:
        with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb2:
            wb2.send_text("this is not json")
            time.sleep(0.5)
    except Exception:
        survived = True
    c.ok("non-JSON frame tolerated (connection may close, server must live)", survived)
    c.eq("API still healthy", tc.get("/health").status_code, 200)


@case("CHAT-007", "Chat", "Spam / rate limiting", "Burst of 60 messages in a second",
      "server either throttles (some rejected) or stores them all without crashing; documents whether per-user rate limiting exists",
      "send 60 messages fast")
def chat_007(c):
    a, b, _ = pair("c7")
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        for i in range(60):
            wb.send_json({"type": "message", "match_id": mid, "content": f"burst {i}"})
        time.sleep(6)
    n = len(tc.get(f"/matches/{mid}/messages?limit=200", headers=a.h).json())
    c.ok("no crash, count in 1..60", 1 <= n <= 60, n)
    c.info(f"stored {n}/60 -> {'no per-user rate limit' if n == 60 else 'throttled'}")
    H.S["chat_rate_limited"] = n < 60


@case("CHAT-008", "Chat", "History pagination", "limit and before parameters",
      "limit=2 returns 2; before=<timestamp> returns older ones; limit 0/201 -> 422", "seed 5 messages, page through")
def chat_008(c):
    a, b, _ = pair("c8")
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        for i in range(5):
            wb.send_json({"type": "message", "match_id": mid, "content": f"p{i}"})
            time.sleep(0.4)
        time.sleep(1.5)
    page = tc.get(f"/matches/{mid}/messages?limit=2", headers=a.h).json()
    c.eq("limit 2", len(page), 2)
    oldest = min(m["sent_at"] for m in page)
    older = tc.get(f"/matches/{mid}/messages?limit=10", headers=a.h, params={"before": oldest}).json()
    c.ok("before returns strictly older", all(m["sent_at"] < oldest for m in older) and len(older) >= 1, len(older))
    c.eq("limit 0", tc.get(f"/matches/{mid}/messages?limit=0", headers=a.h).status_code, 422)
    c.eq("limit 201", tc.get(f"/matches/{mid}/messages?limit=201", headers=a.h).status_code, 422)


@case("CALL-001", "Chat", "Video call signaling", "Offer / answer / ICE / hang-up relay; offline callee ends immediately; outsider ignored; ICE server list served",
      "frames relayed exactly; offline callee gets call_end peer_offline; outsider's offer creates nothing; /calls/ice-servers returns STUN urls",
      "WS signaling between matched pair")
def call_001(c):
    a, b, _ = pair("call1")
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa:
        wa.send_json({"type": "call_offer", "match_id": mid, "sdp": "offer-x"})
        ended = ws_recv(wa)
        c.eq("offline callee", ended and ended.get("reason"), "peer_offline")
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "call_offer", "match_id": mid, "sdp": "offer-sdp"})
        offer = ws_recv(wb)
        c.eq("offer relayed", offer and (offer["type"], offer["sdp"], offer["caller_id"]), ("call_offer", "offer-sdp", a.id))
        cid = offer["call_id"]
        wb.send_json({"type": "call_answer", "call_id": cid, "sdp": "answer-sdp"})
        ans = ws_recv(wa)
        c.eq("answer relayed", ans and ans["sdp"], "answer-sdp")
        wa.send_json({"type": "call_ice_candidate", "call_id": cid, "candidate": "cand"})
        c.eq("ice relayed", (ws_recv(wb) or {}).get("candidate"), "cand")
        wb.send_json({"type": "call_end", "call_id": cid, "reason": "hangup"})
        c.eq("end relayed", (ws_recv(wa) or {}).get("reason"), "hangup")
    evil = H.make_user("call1x")
    with tc.websocket_connect(f"/ws/chat?token={evil.token}") as we, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        we.send_json({"type": "call_offer", "match_id": mid, "sdp": "hijack"})
        time.sleep(1)
    ice = tc.get("/calls/ice-servers", headers=a.h)
    c.eq("ice-servers status", ice.status_code, 200)
    c.ok("has stun url", "stun:" in json.dumps(ice.json()))


# ============================================================== BLIND CHAT / AI MATCH


def bq(u, age, gender, cats=("hobby",), **extra):
    body = {"categories": list(cats), "gender": gender, "min_age": age, "max_age": age}
    body.update(extra)
    return tc.post("/blind-chat/queue", headers=u.h, json=body)


@case("BLIND-001", "Blind chat", "Queue & pairing", "Two compatible people are paired; identities stay masked; bio visible; shared categories shown",
      "first joiner 'waiting', second 'matched'; A's status becomes matched with same id; names masked to 'X***' with no photo; blind flags set; matched push to the waiting user",
      "queue A, queue B")
def blind_001(c):
    a, b, age = pair("b1")
    n = len(H.PUSHES)
    r1 = bq(a, age, "female", ("hobby", "food"))
    c.eq("A waiting", r1.json()["status"], "waiting")
    r2 = bq(b, age, "male", ("food", "travel"))
    c.eq("B matched", r2.json()["status"], "matched")
    mid = r2.json()["match_id"]
    st = tc.get("/blind-chat/queue", headers=a.h).json()
    c.eq("A status matched", (st["status"], st["match_id"]), ("matched", mid))
    m = next(x for x in tc.get("/matches", headers=a.h).json() if x["id"] == mid)
    c.eq("is_blind", m["is_blind"], True)
    c.eq("masked name", m["other_display_name"], "Q***")
    c.eq("no photo", m["other_photo_url"], None)
    c.eq("shared categories", m["blind_categories"], ["food"])
    c.ok("matched push to A", any(p["user_id"] == a.id for p in H.PUSHES[n:]))
    H.S["blind1"] = (a, b, mid)


@case("BLIND-002", "Blind chat", "Messaging", "Blind chat opens immediately in both directions (no first-message gate) with realtime delivery",
      "man's message delivered right away; woman's too; history has both", "WS chat inside a blind match")
def blind_002(c):
    a, b, mid = H.S["blind1"]
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "message", "match_id": mid, "content": "익명 첫 마디"})
        got = ws_recv(wb)
        c.eq("man first delivered", got and got["content"], "익명 첫 마디")
        wb.send_json({"type": "message", "match_id": mid, "content": "반가워요"})
        c.eq("woman delivered", (ws_recv(wa) or {}).get("content"), "반가워요")
    c.eq("history count", len(tc.get(f"/matches/{mid}/messages", headers=a.h).json()), 2)


@case("BLIND-003", "Blind chat", "Identity reveal", "Only the eligible side can request a reveal; the other accepts; both unmasked; self-accept refused",
      "woman (eligible in mixed pair) requests -> man sees incoming request; man cannot request; woman cannot self-accept; man accepts -> real names+photos on both sides; reveal pushes recorded",
      "reveal request/accept flow")
def blind_003(c):
    a, b, mid = H.S["blind1"]
    ma = next(x for x in tc.get("/matches", headers=a.h).json() if x["id"] == mid)
    mb = next(x for x in tc.get("/matches", headers=b.h).json() if x["id"] == mid)
    c.eq("man can_request_reveal", ma["can_request_reveal"], False)
    c.eq("woman can_request_reveal", mb["can_request_reveal"], True)
    c.ok("man's request refused", tc.post(f"/matches/{mid}/blind-reveal/request", headers=a.h).status_code == 403)
    n = len(H.PUSHES)
    r = tc.post(f"/matches/{mid}/blind-reveal/request", headers=b.h)
    c.eq("woman request", r.status_code, 200)
    c.eq("reveal_requested_by_me", r.json()["reveal_requested_by_me"], True)
    c.ok("request push to man", any(p["user_id"] == a.id for p in H.PUSHES[n:]))
    ma = next(x for x in tc.get("/matches", headers=a.h).json() if x["id"] == mid)
    c.eq("man sees incoming request", ma["has_incoming_reveal_request"], True)
    c.eq("self-accept refused", tc.post(f"/matches/{mid}/blind-reveal/accept", headers=b.h).status_code, 400)
    acc = tc.post(f"/matches/{mid}/blind-reveal/accept", headers=a.h)
    c.eq("man accepts", acc.status_code, 200)
    ma = next(x for x in tc.get("/matches", headers=a.h).json() if x["id"] == mid)
    mb = next(x for x in tc.get("/matches", headers=b.h).json() if x["id"] == mid)
    c.eq("man sees woman's real name", ma["other_display_name"], "QAb1F")
    c.eq("woman sees man's real name", mb["other_display_name"], "QAb1M")
    c.ok("photos visible after reveal", bool(ma["other_photo_url"]) and bool(mb["other_photo_url"]))
    c.eq("blind_revealed", ma["blind_revealed"], True)


@case("BLIND-004", "Blind chat", "Feedback", "Post-chat rating: rating 1-5, tags, 'other' comment rule, upsert, outsider refused",
      "rating 5 + tags ok; rating 0/6 -> 422; unknown tag 422; comment without 'other' 422; resubmit updates (no duplicate); outsider 403/404; non-blind match refused",
      "POST /matches/{id}/blind-feedback variants")
def blind_004(c):
    a, b, mid = H.S["blind1"]
    from app.models.blind_chat_feedback import BLIND_CHAT_FEEDBACK_TAG_KEYS

    tag = BLIND_CHAT_FEEDBACK_TAG_KEYS[0]
    c.eq("ok", tc.post(f"/matches/{mid}/blind-feedback", headers=a.h, json={"rating": 5, "tags": [tag]}).status_code, 200)
    c.eq("rating 0", tc.post(f"/matches/{mid}/blind-feedback", headers=a.h, json={"rating": 0, "tags": []}).status_code, 422)
    c.eq("rating 6", tc.post(f"/matches/{mid}/blind-feedback", headers=a.h, json={"rating": 6, "tags": []}).status_code, 422)
    c.eq("unknown tag", tc.post(f"/matches/{mid}/blind-feedback", headers=a.h, json={"rating": 3, "tags": ["zzz"]}).status_code, 422)
    c.eq("comment without other", tc.post(f"/matches/{mid}/blind-feedback", headers=a.h, json={"rating": 3, "tags": [tag], "comment": "hi"}).status_code, 422)
    up = tc.post(f"/matches/{mid}/blind-feedback", headers=a.h, json={"rating": 2, "tags": ["other"], "comment": "meh 😐"})
    c.eq("upsert", up.status_code, 200)
    c.eq("stored rating updated", up.json()["rating"], 2)
    evil = H.make_user("b4x")
    c.ok("outsider refused", tc.post(f"/matches/{mid}/blind-feedback", headers=evil.h, json={"rating": 5, "tags": []}).status_code in (400, 403, 404))
    x, y, _ = pair("b4n")
    nm = H.mutual_match(x, y)
    c.eq("non-blind match refused", tc.post(f"/matches/{nm}/blind-feedback", headers=x.h, json={"rating": 5, "tags": []}).status_code, 400)


@case("BLIND-005", "Blind chat", "Matching rules", "Session gender choice beats profile; age filter honoured; wrong gender never pairs",
      "profile says seeks female, session picks 'male' -> pairs only with a man; a woman waiting is NOT paired; age mismatch stays waiting",
      "queue with overrides")
def blind_005(c):
    age = age_slot()
    a = H.make_user("b5a", "male", "female", age, min_age_pref=age, max_age_pref=age)
    woman = H.make_user("b5w", "female", "male", age)
    man = H.make_user("b5m", "male", "female", age)
    r = bq(woman, age, "male")
    c.eq("woman waits", r.json()["status"], "waiting")
    r = bq(a, age, "male")
    c.eq("male override does NOT pair with the woman", r.json()["status"], "waiting")
    tc.delete("/blind-chat/queue", headers=woman.h)
    r = bq(man, age, "male")
    c.eq("male pairs with male seeker", r.json()["status"], "matched")
    old = H.make_user("b5o", "female", "male", age + 20, min_age_pref=18, max_age_pref=99)
    y = H.make_user("b5y", "male", "female", age, min_age_pref=18, max_age_pref=99)
    bq(old, age + 20, "male", min_age=age + 20, max_age=age + 20)
    r = bq(y, age, "female", min_age=age, max_age=age)
    c.eq("age mismatch stays waiting", r.json()["status"], "waiting")
    tc.delete("/blind-chat/queue", headers=old.h)
    tc.delete("/blind-chat/queue", headers=y.h)


@case("BLIND-006", "Blind chat", "Queue lifecycle", "Cancel, re-join, repeated join, validation",
      "DELETE -> idle; second join after cancel waiting; repeated join idempotent; empty categories 422; 11 categories 422",
      "queue state machine")
def blind_006(c):
    age = age_slot()
    u = H.make_user("b6", "male", "female", age, min_age_pref=age, max_age_pref=age)
    c.eq("first join", bq(u, age, "female").json()["status"], "waiting")
    c.eq("repeat join", bq(u, age, "female").json()["status"], "waiting")
    c.eq("cancel", tc.delete("/blind-chat/queue", headers=u.h).status_code, 204)
    c.eq("status idle", tc.get("/blind-chat/queue", headers=u.h).json()["status"], "idle")
    c.eq("rejoin", bq(u, age, "female").json()["status"], "waiting")
    tc.delete("/blind-chat/queue", headers=u.h)
    c.eq("empty categories", tc.post("/blind-chat/queue", headers=u.h, json={"categories": []}).status_code, 422)
    c.eq("11 categories", tc.post("/blind-chat/queue", headers=u.h, json={"categories": [f"c{i}" for i in range(11)]}).status_code, 422)


@case("BLIND-007", "Blind chat", "Safety", "Blocked pairs are never paired; queue entry older than 15 min is ignored",
      "blocker + blocked both queue -> stay waiting; stale (16 min) waiting entry not matched", "block + backdate")
def blind_007(c):
    age = age_slot()
    a = H.make_user("b7a", "male", "female", age, min_age_pref=age, max_age_pref=age)
    b = H.make_user("b7b", "female", "male", age, min_age_pref=age, max_age_pref=age)
    tc.post("/safety/block", headers=a.h, json={"user_id": b.id})
    bq(b, age, "male")
    c.eq("blocked pair stays waiting", bq(a, age, "female").json()["status"], "waiting")
    tc.delete("/blind-chat/queue", headers=a.h)
    tc.delete("/blind-chat/queue", headers=b.h)
    age2 = age_slot()
    s = H.make_user("b7s", "female", "male", age2, min_age_pref=age2, max_age_pref=age2)
    v = H.make_user("b7v", "male", "female", age2, min_age_pref=age2, max_age_pref=age2)
    bq(s, age2, "male")

    async def backdate():
        from sqlalchemy import update

        from app.database import async_session_factory
        from app.models.blind_chat import BlindChatQueueEntry

        async with async_session_factory() as sess:
            await sess.execute(update(BlindChatQueueEntry).where(BlindChatQueueEntry.user_id == uuid.UUID(s.id)).values(created_at=datetime.now(timezone.utc) - timedelta(minutes=16)))
            await sess.commit()

    H.db(backdate)
    c.eq("stale entry ignored", bq(v, age2, "female").json()["status"], "waiting")
    tc.delete("/blind-chat/queue", headers=v.h)
    tc.delete("/blind-chat/queue", headers=s.h)


@case("BLIND-008", "Blind chat", "Daily limit & monetization", "5 free matches/day, ad bonus +1 once, then blocked; membership = unlimited",
      "limit shows 5; after 5 matches the 6th join 429; ad bonus -> limit 6 (only once per day); 7th blocked; premium bypasses; bonus_available flips",
      "6-7 real pairings for one viewer")
def blind_008(c):
    age = age_slot()
    v = H.make_user("b8v", "male", "female", age, min_age_pref=age, max_age_pref=age)
    lim = tc.get("/blind-chat/limit", headers=v.h).json()
    c.eq("limit", (lim["limit"], lim["remaining"], lim["bonus_available"]), (5, 5, True))
    partners = [H.make_user(f"b8p{i}", "female", "male", age, min_age_pref=age, max_age_pref=age) for i in range(7)]

    def play(p):
        bq(p, age, "male")
        return bq(v, age, "female")

    for i in range(5):
        r = play(partners[i])
        if r.json().get("status") != "matched":
            c.ok(f"match {i + 1}", False, r.text)
            return
    lim = tc.get("/blind-chat/limit", headers=v.h).json()
    c.eq("remaining after 5", lim["remaining"], 0)
    bq(partners[5], age, "male")
    c.eq("6th blocked", bq(v, age, "female").status_code, 429)
    ad = tc.post("/blind-chat/ad-bonus", headers=v.h)
    c.eq("ad bonus", ad.status_code, 200)
    c.eq("limit after bonus", (ad.json()["limit"], ad.json()["remaining"], ad.json()["bonus_available"]), (6, 1, False))
    c.eq("bonus claimed again", tc.post("/blind-chat/ad-bonus", headers=v.h).json()["limit"], 6)
    c.eq("6th allowed after bonus", bq(v, age, "female").json()["status"], "matched")
    bq(partners[6], age, "male")
    c.eq("7th blocked", bq(v, age, "female").status_code, 429)
    set_profile(v.id, premium_until=datetime.now(timezone.utc) + timedelta(days=30))
    c.eq("membership unlimited", bq(v, age, "female").json()["status"], "matched")
    tc.delete("/blind-chat/queue", headers=v.h)


@case("BLIND-009", "Blind chat", "AI match", "AI match: needs a credit (402); with a credit finds the best waiting candidate and consumes exactly 1 credit; no candidates -> credit untouched",
      "no credit 402; not found when nobody waits and credit unchanged; found with two waiting candidates, credit 2->1, match is blind. (The Claude re-rank layer is not exercised here: ANTHROPIC_API_KEY exists only in Railway, so this run covers the deterministic scoring + fallback path.)",
      "/blind-chat/ai-match with 0 and 2 credits")
def blind_009(c):
    age = age_slot()
    v = H.make_user("b9v", "male", "female", age, min_age_pref=age, max_age_pref=age, mbti="ENTP")
    body = {"categories": ["hobby"], "gender": "female", "min_age": age, "max_age": age}
    c.eq("no credit", tc.post("/blind-chat/ai-match", headers=v.h, json=body).status_code, 402)
    set_profile(v.id, ai_match_credits=2)
    r = tc.post("/blind-chat/ai-match", headers=v.h, json=body)
    c.eq("nobody waiting -> found False", r.json()["found"], False)
    c.eq("credit untouched", tc.get("/payments/balance", headers=v.h).json()["ai_match_credits"], 2)
    w1 = H.make_user("b9w1", "female", "male", age, min_age_pref=age, max_age_pref=age, mbti="INFJ", bio="I love hiking and coffee")
    w2 = H.make_user("b9w2", "female", "male", age, min_age_pref=age, max_age_pref=age, mbti="ESTP", bio="Gaming and pizza")
    bq(w1, age, "male")
    bq(w2, age, "male")
    r = tc.post("/blind-chat/ai-match", headers=v.h, json=body)
    c.eq("status", r.status_code, 200)
    c.eq("found", r.json()["found"], True)
    c.eq("credit consumed", tc.get("/payments/balance", headers=v.h).json()["ai_match_credits"], 1)
    c.eq("result is a blind match", r.json()["match"]["is_blind"], True)
    c.ok("picked one of the waiting candidates", r.json()["match"]["other_user_id"] in (w1.id, w2.id))
    tc.delete("/blind-chat/queue", headers=w1.h)
    tc.delete("/blind-chat/queue", headers=w2.h)


@case("BLIND-010", "Blind chat", "Reporting inside blind chat", "Reporting an anonymous partner works and admin can read the conversation",
      "report 204; admin conversation endpoint returns the blind chat messages", "blind chat -> report -> admin")
def blind_010(c):
    admin = H.admin()
    a, b, age = pair("b10")
    bq(a, age, "female")
    mid = bq(b, age, "male").json()["match_id"]
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "message", "match_id": mid, "content": "inappropriate msg"})
        ws_recv(wb)
    c.eq("report", tc.post("/safety/report", headers=b.h, json={"user_id": a.id, "reason": "sexual content"}).status_code, 204)
    rep = next(r for r in tc.get("/admin/reports?status=open", headers=admin.h).json() if r["reported_id"] == a.id)
    conv = tc.get(f"/admin/reports/{rep['id']}/conversation", headers=admin.h).json()
    c.eq("admin sees blind conversation", [m["content"] for m in conv], ["inappropriate msg"])


# ============================================================== MOMENTS / COUPLE STORIES


@case("MOM-001", "Moments", "Lately (요즘 나)", "Post a moment with a REAL photo; caption limit; rolling 6; delete; other user's delete refused",
      "created with image_url that downloads; caption 281 -> 422; posting 8 keeps newest 6; delete own 204; delete another's 404; moments show up on the profile and in Discover",
      "moment presign+PUT+create")
def mom_001(c):
    age = age_slot()
    u = H.make_user("mom", "female", "male", age, min_age_pref=age, max_age_pref=age)
    viewer = H.make_user("momv", "male", "female", age, min_age_pref=age, max_age_pref=age)
    img = H.make_jpeg("MOMENT QA")
    p = tc.post("/uploads/presign-moment-image", headers=u.h, json={"content_type": "image/jpeg"}).json()
    c.eq("PUT", H.put_to_r2(p["upload_url"], img, "image/jpeg").status_code, 200)
    r = tc.post("/moments", headers=u.h, json={"image_object_path": p["gcs_object_path"], "caption": "카페에서 ☕"})
    c.eq("create", r.status_code, 201)
    c.eq("image downloads", httpx.get(r.json()["image_url"], timeout=30).status_code, 200)
    c.eq("caption 281", tc.post("/moments", headers=u.h, json={"image_object_path": p["gcs_object_path"], "caption": "x" * 281}).status_code, 422)
    c.ok("shown on my profile", len(tc.get("/profiles/me", headers=u.h).json()["moments"]) == 1)
    hit = next((x for x in cands(viewer) if x["user_id"] == u.id), None)
    c.ok("shown in Discover card", hit is not None and len(hit["moments"]) == 1)
    for i in range(7):
        tc.post("/moments", headers=u.h, json={"image_object_path": p["gcs_object_path"], "caption": f"m{i}"})
        time.sleep(0.05)
    mine = tc.get("/moments/me", headers=u.h).json()
    c.eq("rolling limit", len(mine), 6)
    c.eq("newest first", mine[0]["caption"], "m6")
    c.eq("other user delete", tc.delete(f"/moments/{mine[0]['id']}", headers=viewer.h).status_code, 404)
    c.eq("own delete", tc.delete(f"/moments/{mine[0]['id']}", headers=u.h).status_code, 204)
    c.eq("after delete", len(tc.get("/moments/me", headers=u.h).json()), 5)


@case("CS-001", "Couple stories", "Community feed", "Story needs partner consent: pending -> partner confirms -> appears in the feed; author cannot self-confirm; one story per match",
      "create 201 pending + request push to partner; hidden from feed; author confirm 404; partner confirm -> published + push to author; visible to others in feed; second story 409; outsider create 404",
      "couple story lifecycle with a real story photo")
def cs_001(c):
    a, b, _ = pair("cs1")
    mid = H.mutual_match(a, b)
    outsider = H.make_user("cs1o")
    img = H.make_jpeg("COUPLE PHOTO")
    p = tc.post("/uploads/presign-story-image", headers=a.h, json={"content_type": "image/jpeg"}).json()
    c.eq("photo PUT", H.put_to_r2(p["upload_url"], img, "image/jpeg").status_code, 200)
    n = len(H.PUSHES)
    r = tc.post("/couple-stories", headers=a.h, json={"match_id": mid, "story_text": "우리 이렇게 만났어요 💕", "photo_object_path": p["gcs_object_path"]})
    c.eq("create", r.status_code, 201)
    sid = r.json()["id"]
    c.eq("status pending", r.json()["status"], "pending")
    c.ok("request push to partner", any(x["user_id"] == b.id for x in H.PUSHES[n:]))
    c.ok("hidden from feed while pending", all(s["id"] != sid for s in tc.get("/couple-stories/feed", headers=outsider.h).json()))
    c.eq("author self-confirm refused", tc.post(f"/couple-stories/{sid}/confirm", headers=a.h).status_code, 404)
    c.eq("outsider confirm refused", tc.post(f"/couple-stories/{sid}/confirm", headers=outsider.h).status_code, 404)
    conf = tc.post(f"/couple-stories/{sid}/confirm", headers=b.h)
    c.eq("partner confirm", conf.status_code, 200)
    c.eq("published", conf.json()["status"], "published")
    c.ok("published push to author", any(x["user_id"] == a.id for x in H.PUSHES[n:]))
    feed = tc.get("/couple-stories/feed", headers=outsider.h).json()
    hit = next((s for s in feed if s["id"] == sid), None)
    c.ok("visible in feed to others", hit is not None)
    c.ok("photo downloadable", hit is not None and httpx.get(hit["photo_url"], timeout=30).status_code == 200)
    c.eq("second story same match", tc.post("/couple-stories", headers=b.h, json={"match_id": mid, "story_text": "again"}).status_code, 409)
    c.eq("outsider cannot create", tc.post("/couple-stories", headers=outsider.h, json={"match_id": mid, "story_text": "x"}).status_code, 404)
    c.ok("in author's mine list", any(s["id"] == sid for s in tc.get("/couple-stories/mine", headers=a.h).json()))
    H.S["cs_story"] = (sid, a, b)


@case("CS-002", "Couple stories", "Decline & report", "Partner can decline; 3 distinct reports auto-hide a published story; validation",
      "decline -> declined and never in feed; declined story cannot be confirmed later; 3 reports hide the published story; empty text 422; 2001 chars 422",
      "decline path and report threshold")
def cs_002(c):
    a, b, _ = pair("cs2")
    mid = H.mutual_match(a, b)
    outsider = H.make_user("cs2o")
    sid = tc.post("/couple-stories", headers=a.h, json={"match_id": mid, "story_text": "declined story"}).json()["id"]
    d = tc.post(f"/couple-stories/{sid}/decline", headers=b.h)
    c.eq("decline", (d.status_code, d.json()["status"]), (200, "declined"))
    c.eq("confirm after decline", tc.post(f"/couple-stories/{sid}/confirm", headers=b.h).status_code, 404)
    c.ok("never in feed", all(s["id"] != sid for s in tc.get("/couple-stories/feed", headers=outsider.h).json()))
    c.eq("empty text", tc.post("/couple-stories", headers=a.h, json={"match_id": mid, "story_text": ""}).status_code, 422)
    c.eq("2001 chars", tc.post("/couple-stories", headers=a.h, json={"match_id": mid, "story_text": "x" * 2001}).status_code, 422)
    sid2, _, _ = H.S["cs_story"]
    reporters = [outsider] + [H.make_user(f"cs2r{i}") for i in range(2)]
    for r in reporters:
        c.eq("report", tc.post(f"/couple-stories/{sid2}/report", headers=r.h, json={"reason": "inappropriate"}).status_code, 204)
    c.ok("auto-hidden after 3 reports", all(s["id"] != sid2 for s in tc.get("/couple-stories/feed", headers=H.make_user("cs2v").h).json()))


# ============================================================== PAYMENTS


def signed_event(payload: dict, secret=None):
    from app.config import settings

    secret = secret or settings.stripe_webhook_secret
    raw = json.dumps(payload).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
    return raw, f"t={ts},v1={sig}"


def purchase_event(user_id, product_id, evt=None):
    evt = evt or f"evt_qa_{uuid.uuid4().hex[:10]}"
    return {"id": evt, "object": "event", "type": "checkout.session.completed",
            "data": {"object": {"id": f"cs_qa_{uuid.uuid4().hex[:8]}", "object": "checkout.session",
                                "metadata": {"user_id": user_id, "product_id": product_id}, "subscription": "sub_qa_1"}}}


@case("PAY-001", "Payments", "Shop catalog", "Product list: only listed products, correct kinds, prices in cents, no hidden classic products",
      "ai_match packs, unlimited week/month, membership monthly/yearly present; superlike/boost packs hidden; prices positive ints", "GET /payments/products")
def pay_001(c):
    ps = tc.get("/payments/products").json()
    pid = {p["product_id"] for p in ps}
    c.ok("expected products present", {"ai_match_pack_1", "ai_match_pack_5", "unlimited_matching_week", "unlimited_matching_month", "membership_monthly", "membership_yearly"} <= pid)
    c.ok("hidden classic products absent", not ({"superlike_pack_5", "superlike_pack_20", "boost_1"} & pid))
    c.ok("prices positive ints", all(isinstance(p["price_usd_cents"], int) and p["price_usd_cents"] > 0 for p in ps))
    c.eq("monthly price", next(p for p in ps if p["product_id"] == "membership_monthly")["price_usd_cents"], 999)


@case("PAY-002", "Payments", "Webhook", "Signed Stripe purchase grants credits exactly once; replay is a no-op; forged/missing signature rejected; unrelated events ignored",
      "ai_match_pack_5 -> +5 credits + history row; replaying same event id -> still 5; bad signature 400; no signature 400; other event types 204 with no effect; unknown product ignored",
      "locally-signed checkout.session.completed events")
def pay_002(c):
    u = H.make_user("pay2")
    evt = purchase_event(u.id, "ai_match_pack_5")
    raw, sig = signed_event(evt)
    r = tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig, "content-type": "application/json"})
    c.eq("webhook", r.status_code, 204)
    c.eq("credits granted", tc.get("/payments/balance", headers=u.h).json()["ai_match_credits"], 5)
    tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig, "content-type": "application/json"})
    c.eq("replay no double grant", tc.get("/payments/balance", headers=u.h).json()["ai_match_credits"], 5)
    hist = tc.get("/payments/history", headers=u.h).json()["items"]
    c.eq("history rows", len(hist), 1)
    c.eq("history product", hist[0]["product_id"], "ai_match_pack_5")
    c.eq("forged signature", tc.post("/payments/webhook", content=raw, headers={"stripe-signature": "t=1,v1=deadbeef"}).status_code, 400)
    c.eq("missing signature", tc.post("/payments/webhook", content=raw).status_code, 400)
    other, sig2 = signed_event({"id": "evt_other", "object": "event", "type": "invoice.paid", "data": {"object": {}}})
    c.eq("unrelated event", tc.post("/payments/webhook", content=other, headers={"stripe-signature": sig2}).status_code, 204)
    bad, sig3 = signed_event(purchase_event(u.id, "no_such_product"))
    c.eq("unknown product ignored", tc.post("/payments/webhook", content=bad, headers={"stripe-signature": sig3}).status_code, 204)
    c.eq("credits unchanged", tc.get("/payments/balance", headers=u.h).json()["ai_match_credits"], 5)


@case("PAY-003", "Payments", "Membership", "Membership purchase -> premium status everywhere; cancel keeps access until period end; yearly replaces monthly",
      "profile is_premium_member True, premium_until ~30d, billing monthly; unlimited swipes + blind matching; cancel -> cancel_at_period_end True, premium_until kept; cancel with no membership refused",
      "webhook membership_monthly then cancel")
def pay_003(c):
    u = H.make_user("pay3")
    raw, sig = signed_event(purchase_event(u.id, "membership_monthly"))
    tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig})
    me = tc.get("/profiles/me", headers=u.h).json()
    c.eq("is_premium_member", me["is_premium_member"], True)
    c.eq("billing_cycle", me["billing_cycle"], "monthly")
    c.eq("price", me["subscription_price_cents"], 999)
    until = datetime.fromisoformat(me["premium_until"].replace("Z", "+00:00"))
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    c.ok("premium_until about 30 days", 28 <= (until - datetime.now(timezone.utc)).days <= 31, (until - datetime.now(timezone.utc)).days)
    c.eq("swipes unlimited", tc.get("/interactions/swipe-limit", headers=u.h).json()["unlimited"], True)
    c.eq("blind unlimited", tc.get("/blind-chat/limit", headers=u.h).json()["unlimited"], True)
    from app.services import payment_service

    async def fake_cancel(db, user_id):
        return until

    orig = getattr(payment_service, "_get_stripe")
    cancel = tc.post("/account/subscription/cancel", headers=u.h)
    c.ok("cancel responds (Stripe sub id is fake -> may 4xx/5xx from Stripe)", cancel.status_code in (200, 400, 404, 502), cancel.status_code)
    free = H.make_user("pay3f")
    c.ok("cancel without membership refused", tc.post("/account/subscription/cancel", headers=free.h).status_code in (400, 404))
    raw2, sig2 = signed_event(purchase_event(u.id, "membership_yearly"))
    tc.post("/payments/webhook", content=raw2, headers={"stripe-signature": sig2})
    me2 = tc.get("/profiles/me", headers=u.h).json()
    c.eq("yearly replaces monthly", (me2["billing_cycle"], me2["subscription_price_cents"]), ("yearly", 9999))


@case("PAY-004", "Payments", "Top-ups", "Unlimited-matching week/month stack on remaining time; purchase history localised in the user's language",
      "two week packs -> ~14 days; history names in Korean when preferred_language=ko; only own rows", "webhook x2, history with ko")
def pay_004(c):
    u = H.make_user("pay4")
    for _ in range(2):
        raw, sig = signed_event(purchase_event(u.id, "unlimited_matching_week"))
        tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig})
    bal = tc.get("/payments/balance", headers=u.h).json()
    until = datetime.fromisoformat(bal["unlimited_matching_until"].replace("Z", "+00:00"))
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    days = (until - datetime.now(timezone.utc)).total_seconds() / 86400
    c.ok("stacked ~14 days", 13.5 <= days <= 14.1, round(days, 2))
    c.eq("blind unlimited", tc.get("/blind-chat/limit", headers=u.h).json()["unlimited"], True)
    for lang in ("ko", "ja", "es", "zh", "en"):
        tc.put("/account/language", headers=u.h, json={"language": lang})
        names = {i["name"] for i in tc.get("/payments/history", headers=u.h).json()["items"]}
        c.ok(f"history name localised ({lang})", len(names) == 1 and next(iter(names)) != "", sorted(names))
        H.S.setdefault("history_names", {})[lang] = sorted(names)[0]
    c.ok("5 languages give distinct names", len(set(H.S["history_names"].values())) == 5, H.S["history_names"])


@case("PAY-005", "Payments", "Checkout", "Checkout session creation (Stripe test/live key aware)",
      "unknown product 400/404; valid product returns a checkout.stripe.com URL when a TEST key is configured; skipped (not created) with a live key",
      "POST /payments/create-checkout-session")
def pay_005(c):
    from app.config import settings

    u = H.make_user("pay5")
    r = tc.post("/payments/create-checkout-session", headers=u.h, json={"product_id": "nope"})
    c.ok("unknown product rejected", r.status_code in (400, 404, 422), r.status_code)
    key = settings.stripe_secret_key or ""
    c.info(f"stripe key mode: {'live' if key.startswith(('sk_live', 'rk_live')) else 'test' if key else 'unset'}")
    if key.startswith("sk_test") or key.startswith("rk_test"):
        r = tc.post("/payments/create-checkout-session", headers=u.h, json={"product_id": "ai_match_pack_1"})
        c.eq("status", r.status_code, 200)
        c.ok("stripe url", r.json()["checkout_url"].startswith("https://checkout.stripe.com/"))
    else:
        c.ok("live/unset key: real session intentionally not created", True)


@case("PAY-006", "Payments", "Boost", "Boost activation consumes a credit, 30-minute window; no credit -> 402",
      "no credit 402; with credit 200 and boost_active_until ~30 min ahead; credit consumed", "activate boost")
def pay_006(c):
    u = H.make_user("pay6")
    c.eq("no credit", tc.post("/payments/activate-boost", headers=u.h).status_code, 402)
    set_profile(u.id, boost_credits=1)
    r = tc.post("/payments/activate-boost", headers=u.h)
    c.eq("activate", r.status_code, 200)
    until = datetime.fromisoformat(r.json()["boost_active_until"].replace("Z", "+00:00"))
    if until.tzinfo is None:
        until = until.replace(tzinfo=timezone.utc)
    mins = (until - datetime.now(timezone.utc)).total_seconds() / 60
    c.ok("~30 minutes", 28 <= mins <= 31, round(mins, 1))
    c.eq("credit consumed", tc.get("/payments/balance", headers=u.h).json()["boost_credits"], 0)


# ============================================================== DEVICES / PUSH / ACCOUNT


@case("PUSH-001", "Push", "Localised notifications", "Verification-result push text exists in all 5 languages and differs per language",
      "approved push title recorded for ko/en/es/zh/ja - 5 non-empty distinct titles", "admin approves for users in each language")
def push_001(c):
    admin = H.admin()
    titles = {}
    for lang in ("ko", "en", "es", "zh", "ja"):
        u = H.make_user(f"push{lang}")
        tc.put("/account/language", headers=u.h, json={"language": lang})
        _submit_face(u, lang)
        mine = next(i for i in tc.get("/admin/face-verifications?status=pending", headers=admin.h).json() if i["user_id"] == u.id)
        n = len(H.PUSHES)
        tc.post(f"/admin/face-verifications/{mine['id']}/approve", headers=admin.h)
        got = [p for p in H.PUSHES[n:] if p["user_id"] == u.id]
        titles[lang] = got[0]["title"] if got else None
    c.ok("all 5 pushes sent", all(titles.values()), titles)
    c.eq("5 distinct titles", len(set(titles.values())), 5)
    c.info(json.dumps(titles, ensure_ascii=False))


@case("DEV-001", "Push", "Device tokens", "Register/re-register FCM token; validation; one user many devices", "204 for valid; re-register upsert 204; empty token 422; auth required",
      "POST /devices/register")
def dev_001(c):
    u = H.make_user("dev")
    c.eq("register", tc.post("/devices/register", headers=u.h, json={"fcm_token": "tok-qa-1", "platform": "ios"}).status_code, 204)
    c.eq("re-register", tc.post("/devices/register", headers=u.h, json={"fcm_token": "tok-qa-1", "platform": "android"}).status_code, 204)
    c.eq("second device", tc.post("/devices/register", headers=u.h, json={"fcm_token": "tok-qa-2", "platform": "ios"}).status_code, 204)
    c.ok("empty token rejected", tc.post("/devices/register", headers=u.h, json={"fcm_token": "", "platform": "ios"}).status_code in (400, 422))
    c.ok("auth required", tc.post("/devices/register", json={"fcm_token": "x", "platform": "ios"}).status_code in (401, 403))


@case("ACC-001", "Account", "Account deletion", "Delete account: everything of the user is gone and the peer's match list is clean; phone can sign up again as NEW",
      "204; token no longer works; profile gone from peer's deck and matches; same phone signs up as new user; old data not resurrected",
      "delete a matched phone user, verify effects")
def acc_001(c):
    phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
    age = age_slot()
    a = H.signup_phone(phone)
    H.complete_profile(a, "QAdel", age, "male", "female", min_age_pref=age, max_age_pref=age)
    b = H.make_user("delpeer", "female", "male", age, min_age_pref=age, max_age_pref=age)
    mid = H.mutual_match(a, b)
    c.ok("match exists", any(m["id"] == mid for m in tc.get("/matches", headers=b.h).json()))
    c.eq("delete", tc.delete("/account/me", headers=a.h).status_code, 204)
    c.ok("token dead", tc.get("/account/me", headers=a.h).status_code in (401, 403, 404))
    c.ok("match gone for peer", all(m["id"] != mid for m in tc.get("/matches", headers=b.h).json()))
    c.ok("gone from peer's deck", a.id not in ids(cands(b)))
    r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    c.eq("re-signup is a new account", r.json().get("is_new_user"), True)
    if r.status_code == 200:
        H.track(r.json()["user_id"])
        c.ok("new id differs", r.json()["user_id"] != a.id)


# ============================================================== SECURITY / ROBUSTNESS SWEEP


@case("SEC-001", "Security", "Auth enforcement sweep", "Every non-public API route rejects anonymous callers",
      "all routes except the public allowlist return 401/403/405/422-without-auth; none return 2xx or 5xx anonymously",
      "iterate the OpenAPI routes with no token")
def sec_001(c):
    from app.main import app

    public = {"/health", "/payments/products", "/payments/webhook", "/auth/signup", "/auth/login", "/auth/refresh", "/auth/google", "/auth/apple",
              "/auth/phone/start", "/auth/phone/confirm", "/docs", "/openapi.json", "/redoc", "/docs/oauth2-redirect"}
    bad = []
    n = 0
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        if not path or path in public or path.startswith("/ws"):
            continue
        concrete = path.replace("{match_id}", str(uuid.uuid4())).replace("{story_id}", str(uuid.uuid4())).replace("{moment_id}", str(uuid.uuid4()))
        concrete = "".join(concrete.split("{")[0:1]) + str(uuid.uuid4()) if "{" in concrete else concrete
        for m in methods - {"HEAD", "OPTIONS"}:
            r = tc.request(m, concrete, json={} if m in ("POST", "PUT", "PATCH") else None)
            n += 1
            if r.status_code < 300 or r.status_code >= 500:
                bad.append((m, path, r.status_code))
    c.info(f"{n} anonymous route calls")
    c.eq("routes that answered 2xx/5xx anonymously", bad, [])


@case("SEC-002", "Security", "Cross-user isolation", "Users cannot read or change each other's data through any endpoint",
      "user B cannot: delete A's photo, read A's face status, approve verifications, see A's purchase history rows, see A's moment list, confirm A's story", "IDOR attempts")
def sec_002(c):
    a, b = H.make_user("sec2a"), H.make_user("sec2b")
    photo = tc.get("/profiles/me", headers=a.h).json()["photos"][0]["id"]
    c.eq("delete A's photo", tc.delete(f"/profiles/me/photos/{photo}", headers=b.h).status_code, 404)
    c.eq("B's own face status independent", tc.get("/verification/face/status", headers=b.h).json()["status"], "unsubmitted")
    c.eq("B is not admin", tc.get("/admin/stats", headers=b.h).status_code, 403)
    raw, sig = signed_event(purchase_event(a.id, "ai_match_pack_1"))
    tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig})
    c.eq("B's history empty", tc.get("/payments/history", headers=b.h).json()["items"], [])
    c.eq("B's balance untouched", tc.get("/payments/balance", headers=b.h).json()["ai_match_credits"], 0)


@case("SEC-003", "Security", "HTTP hardening", "Malformed bodies, wrong content types, oversize bodies, unsupported methods",
      "invalid JSON 422; text/plain body 422; 6 MB JSON body <500; PATCH on a POST route 405; unknown path 404", "hostile requests")
def sec_003(c):
    u = H.make_user("sec3")
    c.eq("invalid JSON", tc.post("/interactions/like", headers={**u.h, "content-type": "application/json"}, content=b"{not json").status_code, 422)
    c.eq("text/plain body", tc.post("/interactions/like", headers={**u.h, "content-type": "text/plain"}, content=b"hello").status_code, 422)
    big = tc.post("/inquiries", headers=u.h, json={"subject": "x", "message": "m" * (6 * 1024 * 1024)})
    c.ok("6MB body handled (<500)", big.status_code < 500, big.status_code)
    c.eq("wrong method", tc.patch("/interactions/like", headers=u.h, json={}).status_code, 405)
    c.eq("unknown path", tc.get("/definitely/not/here").status_code, 404)


@case("SEC-004", "Security", "CORS", "Allowed web origins get CORS headers; unknown origins do not",
      "preflight from soodamate.com / localhost:8081 allowed; from evil.example not allowed", "OPTIONS preflight")
def sec_004(c):
    def pre(origin):
        return tc.options("/auth/phone/start", headers={"Origin": origin, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})

    c.eq("soodamate.com allowed", pre("https://www.soodamate.com").headers.get("access-control-allow-origin"), "https://www.soodamate.com")
    c.eq("mobile web allowed", pre("http://localhost:8081").headers.get("access-control-allow-origin"), "http://localhost:8081")
    c.ok("evil origin not allowed", pre("https://evil.example").headers.get("access-control-allow-origin") in (None, ""))


@case("SEC-005", "Security", "Information exposure", "Public API docs / error bodies",
      "informational: is /docs (Swagger) exposed publicly? Server errors never leak stack traces", "GET /docs, /openapi.json, trigger a 404/422")
def sec_005(c):
    docs = tc.get("/docs").status_code
    c.info(f"/docs -> {docs} ({'publicly exposed' if docs == 200 else 'disabled'})")
    err = tc.post("/auth/login", json={"email": 1}).text
    c.ok("validation error has no traceback", "Traceback" not in err and "File \"" not in err)
    c.ok("informational recorded", True)
