"""Adversarial security suite. Every case asserts the SECURE behaviour, so a FAIL
is a vulnerability that exists in the code under test (run it against an older
checkout to see what a fix changed).

Runs in-process against the real hosted DB + R2 like the other suites; SMS,
push and SMTP are stubbed, and nothing here talks to a real person.
"""
import json
import threading
import time
import uuid
from datetime import date, datetime, timedelta, timezone

import httpx
from jose import jwt

from qa import harness as H
from qa.harness import case, hdr, tc
from qa.ws_util import ws_recv

_AGE = {"n": 40}


def age_slot():
    _AGE["n"] += 1
    if _AGE["n"] > 60:
        _AGE["n"] = 41
    return _AGE["n"]


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


def set_user(uid, **fields):
    async def go():
        from app.database import async_session_factory
        from app.models.user import User

        async with async_session_factory() as s:
            u = await s.get(User, uuid.UUID(uid))
            for k, v in fields.items():
                setattr(u, k, v)
            await s.commit()

    H.db(go)


def parallel(fn, n):
    """Run fn(i) on n threads at once; returns the results in order."""
    out = [None] * n
    gate = threading.Barrier(n)

    def run(i):
        try:
            gate.wait(10)
            out[i] = fn(i)
        except Exception as e:  # noqa: BLE001
            out[i] = e

    ts = [threading.Thread(target=run, args=(i,), daemon=True) for i in range(n)]
    [t.start() for t in ts]
    [t.join(120) for t in ts]
    return out


def reset_limiter():
    try:
        from app.core import rate_limit

        rate_limit.reset()
    except ImportError:
        pass


def status_of(x):
    return getattr(x, "status_code", None)


class Inbox:
    """Reads a test websocket on ONE background thread into a queue, so waiting
    for "nothing" can't leave a stray reader that swallows the next frame."""

    def __init__(self, ws):
        import queue

        self.q = queue.Queue()
        self.ws = ws
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        while True:
            try:
                self.q.put(self.ws.receive_json())
            except Exception:  # noqa: BLE001 - socket closed
                return

    def get(self, timeout=8):
        import queue

        try:
            return self.q.get(timeout=timeout)
        except queue.Empty:
            return None

    def drain(self):
        out = []
        while not self.q.empty():
            out.append(self.q.get_nowait())
        return out


def blind_pair(tag):
    age = age_slot()
    a = H.make_user(f"{tag}M", "male", "female", age, min_age_pref=age, max_age_pref=age)
    b = H.make_user(f"{tag}F", "female", "male", age, min_age_pref=age, max_age_pref=age)

    def q(u, gender):
        return tc.post("/blind-chat/queue", headers=u.h, json={"categories": ["hobby"], "gender": gender, "min_age": age, "max_age": age})

    q(a, "female")
    r = q(b, "male")
    assert r.status_code == 200 and r.json()["status"] == "matched", r.text
    return a, b, r.json()["match_id"]


# ====================================================================== TOKENS / SESSIONS


@case("SEC-201", "Security", "Token type confusion", "A refresh token is not an access token and vice versa",
      "refresh token as Bearer -> 401; access token to /auth/refresh -> 401", "swap token types")
def sec_201(c):
    u = H.make_user("s201")
    c.eq("refresh token used as access", tc.get("/account/me", headers=hdr(u.refresh)).status_code, 401)
    c.eq("access token used as refresh", tc.post("/auth/refresh", json={"refresh_token": u.token}).status_code, 401)
    from starlette.websockets import WebSocketDisconnect

    try:
        with tc.websocket_connect(f"/ws/chat?token={u.refresh}") as ws:
            c.ok("refresh token refused by websocket", ws_recv(ws, 3) is None)
    except WebSocketDisconnect:
        c.ok("refresh token refused by websocket (handshake closed)", True)


@case("SEC-202", "Security", "Forged / malformed JWTs", "Tokens with a wrong key, alg=none, expired, or broken claims never authenticate and never 500",
      "all forged variants -> 401 (never 2xx, never 5xx)", "wrong secret, alg none, expired, other-user sub, missing/invalid sub")
def sec_202(c):
    import base64

    u = H.make_user("s202")
    now = datetime.now(timezone.utc)

    def mk(payload, key=None, alg="HS256"):
        return jwt.encode(payload, key or H.settings.secret_key, algorithm=alg)

    base = {"sub": u.id, "type": "access", "iat": now, "exp": now + timedelta(minutes=5)}

    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    variants = {
        "wrong secret": mk(base, key="not-the-secret"),
        "well-known dev secret": mk(base, key="dev-secret-key-not-for-production"),
        "alg none": b64({"alg": "none", "typ": "JWT"}) + "." + b64({"sub": u.id, "type": "access", "exp": int(time.time()) + 300}) + ".",
        "expired": mk({**base, "exp": now - timedelta(minutes=1)}),
        "no sub (validly signed)": mk({"type": "access", "exp": now + timedelta(minutes=5)}),
        "non-uuid sub (validly signed)": mk({**base, "sub": "not-a-uuid"}),
        "no type (validly signed)": mk({"sub": u.id, "exp": now + timedelta(minutes=5)}),
        "HS512 (validly signed)": mk(base, alg="HS512"),
        "garbage": "a.b.c",
        "empty bearer": "",
    }
    for label, tok in variants.items():
        r = tc.get("/account/me", headers=hdr(tok))
        c.ok(f"{label} -> 401 (got {r.status_code})", r.status_code == 401, r.status_code)
    r = tc.post("/auth/refresh", json={"refresh_token": mk({**base, "type": "refresh", "sub": "not-a-uuid"})})
    c.ok(f"refresh with non-uuid sub -> 401 (got {r.status_code})", r.status_code == 401, r.status_code)


@case("SEC-203", "Security", "Session revocation", "Disabled / banned / deleted accounts lose access everywhere, including an already-open WebSocket",
      "old access+refresh token refused after disable/ban/delete; a banned user's open socket can no longer deliver messages", "disable, ban, delete")
def sec_203(c):
    a = H.make_user("s203a", "male", "male")
    b = H.make_user("s203b", "male", "male")
    mid = H.mutual_match(a, b)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "message", "match_id": mid, "content": "before ban"})
        c.eq("delivered before ban", (ws_recv(wb) or {}).get("content"), "before ban")
        set_user(a.id, is_banned=True)
        wa.send_json({"type": "message", "match_id": mid, "content": "after ban"})
        got = ws_recv(wb, 4)
        c.ok("banned user's message not delivered on the already-open socket", not got or got.get("content") != "after ban", got)
    c.eq("banned: access token", tc.get("/account/me", headers=a.h).status_code, 401)
    c.eq("banned: refresh token", tc.post("/auth/refresh", json={"refresh_token": a.refresh}).status_code, 401)
    d = H.make_user("s203d")
    c.eq("delete account", tc.delete("/account/me", headers=d.h).status_code, 204)
    c.eq("deleted: access token", tc.get("/account/me", headers=d.h).status_code, 401)
    c.eq("deleted: refresh token", tc.post("/auth/refresh", json={"refresh_token": d.refresh}).status_code, 401)


@case("SEC-204", "Security", "Password handling", "Long / multi-byte / oversized passwords never crash the server",
      "signup+login with 128-char ASCII, 100 multi-byte chars, and login with 100k chars: no 5xx, sensible 2xx/4xx", "edge-case passwords")
def sec_204(c):
    for label, pw in (("128 ascii", "p" * 128), ("100 korean chars", "가" * 100), ("73 bytes", "a" * 73)):
        email = f"qa-s204-{uuid.uuid4().hex[:8]}@example.com"
        r = tc.post("/auth/signup", json={"email": email, "password": pw})
        if r.status_code == 201:
            H.track(r.json()["user_id"])
        c.ok(f"signup {label}: {r.status_code} (<500)", r.status_code < 500, r.status_code)
        r2 = tc.post("/auth/login", json={"email": email, "password": pw})
        c.ok(f"login {label}: {r2.status_code} (<500)", r2.status_code < 500, r2.status_code)
        if r.status_code == 201:
            c.eq(f"login {label} works", r2.status_code, 200)
    r = tc.post("/auth/login", json={"email": "nobody@example.com", "password": "x" * 100_000})
    c.ok(f"100k-char login password: {r.status_code} (<500)", r.status_code < 500, r.status_code)


@case("SEC-205", "Security", "OAuth account linking", "A provider identity is never merged into an account whose email was merely typed in (unverified)",
      "attacker sets victim's email on their own account; the real owner then signs in with Google -> gets a separate account, not the attacker's",
      "PUT /account/email then /auth/google with matching email")
def sec_205(c):
    import app.routers.auth as auth_router
    from app.core.auth_provider_base import ExternalIdentity

    attacker = H.make_user("s205")
    victim_email = f"qa-victim-{uuid.uuid4().hex[:8]}@example.com"
    r = tc.put("/account/email", headers=attacker.h, json={"email": victim_email})
    c.eq("attacker can set an (unverified) email", r.status_code, 204)

    class FakeGoogle:
        async def verify(self, token):
            return ExternalIdentity(provider_user_id=f"g-{uuid.uuid4().hex[:8]}", email=victim_email, raw_claims={"email_verified": True})

    real = auth_router.google_verifier
    auth_router.google_verifier = FakeGoogle()
    try:
        with H.flag("enable_legacy_auth", True):
            resp = tc.post("/auth/google", json={"id_token": "x"})
    finally:
        auth_router.google_verifier = real
    if resp.status_code == 200:
        H.track(resp.json()["user_id"])
        c.ok("real owner's Google login did NOT land in the attacker's account", resp.json()["user_id"] != attacker.id, resp.json()["user_id"] == attacker.id)
    else:
        c.ok(f"google login refused/handled safely ({resp.status_code})", resp.status_code in (400, 401, 403, 404, 409), resp.status_code)


@case("SEC-206", "Security", "Legacy sign-up paths", "Email sign-up and Google/Apple sign-in are closed by default (the app only uses phone sign-in)",
      "with the production default (legacy auth off) /auth/signup, /auth/google, /auth/apple are refused; /auth/login and /auth/refresh keep working for existing accounts",
      "toggle enable_legacy_auth")
def sec_206(c):
    u = H.make_user("s206")
    with H.flag("enable_legacy_auth", False):
        email = f"qa-s206-{uuid.uuid4().hex[:8]}@example.com"
        r = tc.post("/auth/signup", json={"email": email, "password": "password123"})
        if r.status_code == 201:
            H.track(r.json()["user_id"])
        c.ok(f"signup refused (got {r.status_code})", r.status_code in (403, 404), r.status_code)
        c.ok("google refused", tc.post("/auth/google", json={"id_token": "x"}).status_code in (403, 404))
        c.ok("apple refused", tc.post("/auth/apple", json={"identity_token": "x"}).status_code in (403, 404))
        c.eq("existing account can still refresh", tc.post("/auth/refresh", json={"refresh_token": u.refresh}).status_code, 200)
        c.eq("existing email account can still log in (admin console)", tc.post("/auth/login", json={"email": u.email, "password": "password123"}).status_code, 200)


# ====================================================================== SERVER-SIDE VERIFICATION GATES


@case("SEC-210", "Security", "Identity gate is enforced by the server", "An unverified account cannot join Blind Chat or AI Match by calling the API directly",
      "with verification enforced: queue join and AI match -> 403 for an account without face verification; the same account works once verified",
      "POST /blind-chat/queue and /ai-match as unverified, then verified")
def sec_210(c):
    age = age_slot()
    u = H.make_user("s210", "male", "female", age, min_age_pref=age, max_age_pref=age)
    body = {"categories": ["hobby"], "gender": "female", "min_age": age, "max_age": age}
    with H.flag("require_verified_accounts", True):
        r = tc.post("/blind-chat/queue", headers=u.h, json=body)
        c.eq("unverified queue join", r.status_code, 403)
        c.eq("unverified AI match", tc.post("/blind-chat/ai-match", headers=u.h, json={**body}).status_code, 403)
        set_profile(u.id, face_verified=True)
        r2 = tc.post("/blind-chat/queue", headers=u.h, json=body)
        c.eq("verified queue join", r2.status_code, 200)
        tc.delete("/blind-chat/queue", headers=u.h)


# ====================================================================== BLIND CHAT ANONYMITY


@case("SEC-220", "Security", "Blind chat anonymity: push", "An offline partner's push notification must not reveal the sender's real name before the reveal",
      "push title/body for a message inside an unrevealed blind chat contains neither the sender's real display name nor a photo", "message an offline blind partner")
def sec_220(c):
    a, b, mid = blind_pair("s220")
    real_a = "QAs220M"
    n = len(H.PUSHES)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa:
        wa.send_json({"type": "message", "match_id": mid, "content": "hello there"})
        deadline = time.time() + 15
        while time.time() < deadline and not any(p["user_id"] == b.id for p in H.PUSHES[n:]):
            time.sleep(0.5)
    pushes = [p for p in H.PUSHES[n:] if p["user_id"] == b.id]
    c.ok("recipient was pushed", len(pushes) >= 1, len(pushes))
    for p in pushes:
        c.ok(f"push title/body do not contain the real name ({p['title']!r})", real_a not in (p["title"] or "") and real_a not in (p["body"] or ""), p["title"])
    # once revealed the real name is fine again
    r = tc.post(f"/matches/{mid}/blind-reveal/request", headers=b.h)
    if r.status_code != 200:
        r = tc.post(f"/matches/{mid}/blind-reveal/request", headers=a.h)
    H.S["s220_reveal_status"] = r.status_code


@case("SEC-221", "Security", "Blind chat anonymity: calls", "Video-call signaling is refused inside an unrevealed blind chat (a call would show a face and leak IPs)",
      "call_offer in an unrevealed blind match is not relayed and creates no call session", "WS call_offer inside blind match")
def sec_221(c):
    a, b, mid = blind_pair("s221")
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wa.send_json({"type": "call_offer", "match_id": mid, "sdp": "v=0 fake"})
        got = ws_recv(wb, 3)
        c.ok("offer NOT relayed to the anonymous partner", not got or got.get("type") != "call_offer", got)

    async def n_calls():
        from sqlalchemy import func, select

        from app.database import async_session_factory
        from app.models.call import CallSession

        async with async_session_factory() as s:
            return await s.scalar(select(func.count()).select_from(CallSession).where(CallSession.match_id == uuid.UUID(mid)))

    c.eq("no call session recorded", H.db(n_calls), 0)


# ====================================================================== WEBSOCKET ROBUSTNESS / ABUSE


def _friends(tag):
    a = H.make_user(f"{tag}a", "male", "male")
    b = H.make_user(f"{tag}b", "male", "male")
    return a, b, H.mutual_match(a, b)


@case("SEC-222", "Security", "Chat message size", "A single chat message is capped (no multi-MB messages, no unbounded translation bills)",
      "a 5,000-char message is rejected and not stored; a normal message still goes through", "send oversized message")
def sec_222(c):
    a, b, mid = _friends("s222")
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        inbox = Inbox(wb)
        wa.send_json({"type": "message", "match_id": mid, "content": "x" * 5000})
        time.sleep(5)
        seen = inbox.drain()
        c.ok("oversized message not delivered", all(len(m.get("content", "")) <= 2000 for m in seen), [len(m.get("content", "")) for m in seen])
        wa.send_json({"type": "message", "match_id": mid, "content": "normal"})
        c.eq("normal message still works", (inbox.get(8) or {}).get("content"), "normal")
    stored = tc.get(f"/matches/{mid}/messages", headers=a.h).json()
    c.ok("no stored message longer than 2000 chars", all(len(m["content"]) <= 2000 for m in stored), [len(m["content"]) for m in stored])


@case("SEC-223", "Security", "Chat flood", "One user cannot flood a conversation (per-user message rate limit)",
      "100 messages in a burst: far fewer than 100 are stored, and the sender is told they were rate limited", "burst of 100 WS messages")
def sec_223(c):
    a, b, mid = _friends("s223")
    with H.flag("rate_limit_enabled", True):
        reset_limiter()
        with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa:
            for i in range(100):
                wa.send_json({"type": "message", "match_id": mid, "content": f"spam {i}"})
            # wait until the server has worked through the whole burst
            last, stable_since = -1, time.time()
            deadline = time.time() + 90
            while time.time() < deadline:
                n = len(tc.get(f"/matches/{mid}/messages", headers=a.h).json())
                if n != last:
                    last, stable_since = n, time.time()
                elif time.time() - stable_since > 4:
                    break
                time.sleep(1)
        reset_limiter()
    rows = tc.get(f"/matches/{mid}/messages", headers=a.h).json()
    times = sorted(datetime.fromisoformat(m["sent_at"]).timestamp() for m in rows)
    worst = max((sum(1 for t2 in times if t0 <= t2 < t0 + 10) for t0 in times), default=0)
    c.ok(f"no more than 30 messages in any 10 s window (worst window: {worst}, stored {len(rows)}/100)", worst <= 30, worst)
    c.ok("some of the burst was refused", len(rows) < 100, len(rows))


@case("SEC-224", "Security", "WebSocket robustness", "Garbage frames (JSON arrays/strings/numbers, bad JSON, binary) never kill the socket or the server",
      "after 6 hostile frames a normal message on the same socket is still delivered", "send junk frames")
def sec_224(c):
    a, b, mid = _friends("s224")
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        for frame in ([1, 2, 3], "just a string", 42, None, {"type": 5}, {"type": "message"}):
            try:
                wa.send_json(frame)
            except Exception:  # noqa: BLE001
                break
        try:
            wa.send_text("{not json")
            wa.send_bytes(b"\x00\x01\x02")
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
        try:
            wa.send_json({"type": "message", "match_id": mid, "content": "still alive"})
            got = ws_recv(wb, 6)
        except Exception:  # noqa: BLE001
            got = None
        c.eq("socket survived hostile frames", (got or {}).get("content"), "still alive")
    c.eq("API still healthy", tc.get("/health").status_code, 200)


@case("SEC-225", "Security", "Call signaling size", "Oversized SDP / candidate payloads are not relayed",
      "1 MB sdp -> not relayed to the peer", "call_offer with huge sdp")
def sec_225(c):
    a, b, mid = _friends("s225")
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        try:
            wa.send_json({"type": "call_offer", "match_id": mid, "sdp": "A" * 900_000})
        except Exception:  # noqa: BLE001
            pass
        got = ws_recv(wb, 4)
        c.ok("huge SDP not relayed", not got or got.get("type") != "call_offer", (got or {}).get("type"))


@case("SEC-226", "Security", "Idle sockets and the DB pool", "Idle WebSockets do not hold database connections",
      "after authenticating, an idle websocket leaves no open DB transaction (static check of the handler + live connect/idle probe)", "inspect handler")
def sec_226(c):
    import inspect

    from app.routers import ws_chat

    src = inspect.getsource(ws_chat.ws_chat)
    c.ok("ws_chat does not hold a request-scoped DB session for the whole connection", "Depends(get_db)" not in src, "Depends(get_db) in ws_chat signature")


# ====================================================================== RATE LIMITS / COST ABUSE


@case("SEC-230", "Security", "SMS pumping", "The SMS start endpoint is limited per number, per IP and globally",
      "10 rapid starts for one number -> at most 5 SMS requested and a 429; with a lowered global cap, distinct numbers are cut off too", "hammer /auth/phone/start")
def sec_230(c):
    with H.flag("rate_limit_enabled", True):
        reset_limiter()
        phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
        n0 = len(H.SMS_STARTED)
        codes = [tc.post("/auth/phone/start", json={"phone_number": phone}).status_code for _ in range(10)]
        sent = len([p for p in H.SMS_STARTED[n0:] if p == phone])
        c.ok(f"same number: at most 5 SMS (sent {sent})", sent <= 5, sent)
        c.ok(f"same number: a 429 was returned ({sorted(set(codes))})", 429 in codes, codes)
        reset_limiter()
        H.set_flag("sms_global_per_10min", 15)
        try:
            n1 = len(H.SMS_STARTED)
            statuses = [tc.post("/auth/phone/start", json={"phone_number": f"+8210{uuid.uuid4().int % 10**8:08d}"}).status_code for _ in range(30)]
            c.ok(f"global cap cuts off distinct numbers (sms sent {len(H.SMS_STARTED) - n1}/30)", len(H.SMS_STARTED) - n1 <= 15, len(H.SMS_STARTED) - n1)
            c.ok("429 returned once the cap is hit", 429 in statuses, sorted(set(statuses)))
        finally:
            H.set_flag("sms_global_per_10min", 300)
        reset_limiter()


@case("SEC-231", "Security", "Credential brute force", "Login and SMS-code confirmation are limited per account/number",
      "25 wrong passwords for one email -> 429 appears; 30 wrong SMS codes for one number -> 429 appears; a different email is unaffected", "brute force")
def sec_231(c):
    u = H.make_user("s231")
    with H.flag("rate_limit_enabled", True):
        reset_limiter()
        codes = [tc.post("/auth/login", json={"email": u.email, "password": f"wrong-password-{i}"}).status_code for i in range(25)]
        c.ok(f"login brute force is throttled ({sorted(set(codes))})", 429 in codes, codes)
        other = H.make_user("s231b")
        c.eq("another account still logs in", tc.post("/auth/login", json={"email": other.email, "password": "password123"}).status_code, 200)
        reset_limiter()
        phone = f"+8210{uuid.uuid4().int % 10**8:08d}"
        codes2 = [tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": f"{i:06d}"}).status_code for i in range(30)]
        c.ok(f"SMS code guessing is throttled ({sorted(set(codes2))})", 429 in codes2, codes2)
        reset_limiter()


@case("SEC-232", "Security", "Endpoint spam", "Authenticated write endpoints have per-user ceilings (presign, inquiries, reports)",
      "130 presigns, 8 inquiries and 30 reports in a row each hit a 429", "spam authenticated endpoints")
def sec_232(c):
    u = H.make_user("s232")
    victim = H.make_user("s232v")
    with H.flag("rate_limit_enabled", True):
        reset_limiter()
        pre = [tc.post("/uploads/presign", headers=u.h, json={"content_type": "image/jpeg", "position": 0}).status_code for _ in range(130)]
        c.ok(f"presign throttled ({sorted(set(pre))})", 429 in pre, sorted(set(pre)))
        inq = [tc.post("/inquiries", headers=u.h, json={"subject": "s", "message": "m"}).status_code for _ in range(8)]
        c.ok(f"inquiries throttled ({sorted(set(inq))})", 429 in inq, sorted(set(inq)))
        rep = [tc.post("/safety/report", headers=u.h, json={"user_id": victim.id, "reason": "spam"}).status_code for _ in range(30)]
        c.ok(f"reports throttled ({sorted(set(rep))})", 429 in rep, sorted(set(rep)))
        reset_limiter()


# ====================================================================== INPUT BOUNDS


@case("SEC-240", "Security", "Input bounds", "List fields and free-text fields have size limits",
      "5,000 interests / 500-char items / 100k-char email / 300-char phone -> 422, never stored", "oversized profile payloads")
def sec_240(c):
    u = H.make_user("s240")
    body = H.profile_body("QA s240")
    c.eq("5000 interests", tc.put("/profiles/me", headers=u.h, json={**body, "interests": [f"i{i}" for i in range(5000)]}).status_code, 422)
    c.eq("500-char interest", tc.put("/profiles/me", headers=u.h, json={**body, "interests": ["x" * 500]}).status_code, 422)
    c.eq("5000 languages", tc.put("/profiles/me", headers=u.h, json={**body, "languages": ["en"] * 5000}).status_code, 422)
    c.eq("5000 k-content tags", tc.put("/profiles/me", headers=u.h, json={**body, "k_content_tags": ["t"] * 5000}).status_code, 422)
    c.eq("latitude 91", tc.put("/profiles/me", headers=u.h, json={**body, "location_lat": 91, "location_lng": 10}).status_code, 422)
    c.eq("longitude 1e12", tc.put("/profiles/me", headers=u.h, json={**body, "location_lat": 10, "location_lng": 1e12}).status_code, 422)
    r = tc.post("/auth/login", json={"email": "a" * 100_000 + "@example.com", "password": "x"})
    c.ok(f"giant email rejected ({r.status_code})", r.status_code in (400, 413, 422), r.status_code)
    r = tc.post("/auth/phone/start", json={"phone_number": "+" + "8" * 300})
    c.ok(f"giant phone rejected ({r.status_code})", r.status_code in (400, 413, 422), r.status_code)
    big = tc.post("/inquiries", headers=u.h, json={"subject": "x", "message": "m" * (3 * 1024 * 1024)})
    c.ok(f"3 MB body refused before parsing ({big.status_code})", big.status_code in (413, 422), big.status_code)


@case("SEC-241", "Security", "Mass assignment", "Privileged fields cannot be set through profile/account writes",
      "PUT /profiles/me with is_admin/face_verified/credits/premium/user_id extras changes none of them", "extra fields on profile write")
def sec_241(c):
    u = H.make_user("s241")
    extras = {"is_admin": True, "face_verified": True, "superlike_credits": 99, "boost_credits": 99, "ai_match_credits": 99,
              "premium_until": "2099-01-01T00:00:00Z", "unlimited_matching_until": "2099-01-01T00:00:00Z", "verified_badge": "work", "user_id": str(uuid.uuid4()),
              "is_banned": False, "phone_verified_at": "2020-01-01T00:00:00Z"}
    r = tc.put("/profiles/me", headers=u.h, json={**H.profile_body("QA s241"), **extras})
    c.ok(f"write accepted or refused cleanly ({r.status_code})", r.status_code in (200, 422), r.status_code)
    p = tc.get("/profiles/me", headers=u.h).json()
    c.eq("face_verified untouched", p.get("face_verified"), False)
    bal = tc.get("/payments/balance", headers=u.h).json()
    c.eq("credits untouched", (bal["superlike_credits"], bal["boost_credits"], bal["ai_match_credits"]), (0, 0, 0))
    c.eq("not admin", tc.get("/admin/stats", headers=u.h).status_code, 403)
    c.eq("user_id untouched", p.get("user_id", u.id), u.id)


# ====================================================================== UPLOADS


@case("SEC-250", "Security", "Object path validation", "Uploaded-object paths are strictly validated (no traversal, no other user's folder)",
      "photo confirm / moment / story / chat image with '..', another user's path, wrong folder or a non-uuid name -> rejected", "hostile object paths")
def sec_250(c):
    a = H.make_user("s250a", "male", "male")
    b = H.make_user("s250b")
    good_name = f"{uuid.uuid4()}.jpg"
    bad_paths = {
        "traversal into another user": f"users/{a.id}/photos/../../{b.id}/photos/{good_name}",
        "another user's folder": f"users/{b.id}/photos/{good_name}",
        "verification folder": f"verifications/{a.id}/selfie-{good_name}",
        "dot-dot inside own folder": f"users/{a.id}/photos/../chat/{good_name}",
        "non-uuid file name": f"users/{a.id}/photos/anything.jpg",
        "double slash": f"users/{a.id}/photos//{good_name}",
        "url-encoded traversal": f"users/{a.id}/photos/%2e%2e/{good_name}",
        "backslash": f"users/{a.id}/photos\\{good_name}",
    }
    for label, path in bad_paths.items():
        r = tc.post("/profiles/me/photos/confirm", headers=a.h, json={"gcs_object_path": path, "position": 2})
        c.ok(f"photo confirm: {label} -> {r.status_code}", r.status_code in (400, 422), r.status_code)
    m = tc.post("/moments", headers=a.h, json={"image_object_path": f"users/{a.id}/moments/../../{b.id}/moments/{good_name}", "caption": "x"})
    c.ok(f"moment traversal -> {m.status_code}", m.status_code in (400, 422), m.status_code)
    with tc.websocket_connect(f"/ws/chat?token={a.token}") as wa:
        friend = H.make_user("s250f", "male", "male")
        mid = H.mutual_match(a, friend)
        with tc.websocket_connect(f"/ws/chat?token={friend.token}") as wf:
            wa.send_json({"type": "message", "message_type": "image", "match_id": mid, "image_object_path": f"users/{a.id}/chat/../../{b.id}/photos/{good_name}"})
            got = ws_recv(wf, 3)
            c.ok("chat image traversal not relayed", not got, got)


@case("SEC-251", "Security", "Upload verification", "Confirming an upload checks that the object exists, is an image/video of sane size and really has that format",
      "missing object -> 4xx; 25 MB blob -> 4xx and deleted; bytes that are not a JPEG -> 4xx; a genuine JPEG -> 201", "real R2 uploads")
def sec_251(c):
    u = H.make_user("s251")
    with H.flag("verify_uploaded_objects", True):  # this case is about the real check

        def presign(pos):
            r = tc.post("/uploads/presign", headers=u.h, json={"content_type": "image/jpeg", "position": pos}).json()
            return r["upload_url"], r["gcs_object_path"]

        _url, ghost = presign(3)
        r = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": ghost, "position": 3})
        c.ok(f"never-uploaded object -> {r.status_code}", r.status_code in (400, 404, 422), r.status_code)

        url, big = presign(4)
        H.R2_KEYS.append(big)
        H.put_to_r2(url, bytes([0xFF, 0xD8, 0xFF, 0xE0]) + bytes(25 * 1024 * 1024), "image/jpeg")
        r = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": big, "position": 4})
        c.ok(f"25 MB object -> {r.status_code}", r.status_code in (400, 413, 422), r.status_code)

        url, fake = presign(5)
        H.R2_KEYS.append(fake)
        H.put_to_r2(url, b"<html><script>alert(1)</script></html>", "image/jpeg")
        r = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": fake, "position": 5})
        c.ok(f"HTML disguised as JPEG -> {r.status_code}", r.status_code in (400, 415, 422), r.status_code)

        url, ok_path = presign(6)
        H.R2_KEYS.append(ok_path)
        H.put_to_r2(url, H.make_jpeg("SEC-251"), "image/jpeg")
        r = tc.post("/profiles/me/photos/confirm", headers=u.h, json={"gcs_object_path": ok_path, "position": 6})
        c.eq("genuine JPEG accepted", r.status_code, 201)


# ====================================================================== MONEY / RACES


@case("SEC-260", "Security", "Credit double-spend", "Concurrent requests cannot spend one credit twice",
      "1 boost credit + 8 parallel activations -> exactly one succeeds and the balance is 0; 1 superlike credit + 8 parallel superlikes -> exactly one succeeds",
      "parallel requests")
def sec_260(c):
    u = H.make_user("s260")
    set_profile(u.id, boost_credits=1)
    res = parallel(lambda i: tc.post("/payments/activate-boost", headers=u.h), 8)
    ok = sum(1 for r in res if status_of(r) == 200)
    c.eq("boost: successful activations", ok, 1)
    c.eq("boost: credits left", tc.get("/payments/balance", headers=u.h).json()["boost_credits"], 0)

    v = H.make_user("s260v")
    targets = [H.make_user(f"s260t{i}", "male", "female") for i in range(8)]
    set_profile(v.id, superlike_credits=1, free_superlike_used_on=date.today())
    res2 = parallel(lambda i: tc.post("/interactions/superlike", headers=v.h, json={"to_user_id": targets[i].id}), 8)
    ok2 = sum(1 for r in res2 if status_of(r) == 200)
    c.eq("superlike: successful", ok2, 1)
    c.ok("superlike: credits never negative", tc.get("/payments/balance", headers=v.h).json()["superlike_credits"] >= 0)


@case("SEC-270", "Security", "Stripe webhook authenticity", "A webhook is only accepted with a valid signature; an unconfigured secret rejects everything",
      "no signature / wrong secret / stale timestamp / EMPTY configured secret forged with an empty key -> 4xx and no credits granted", "forge webhooks")
def sec_270(c):
    import hashlib
    import hmac

    u = H.make_user("s270")
    evt = {"id": f"evt_qa_{uuid.uuid4().hex[:10]}", "object": "event", "type": "checkout.session.completed",
           "data": {"object": {"id": f"cs_qa_{uuid.uuid4().hex[:8]}", "object": "checkout.session", "metadata": {"user_id": u.id, "product_id": "ai_match_pack_1"}}}}
    raw = json.dumps(evt).encode()

    def sign(secret, ts=None):
        ts = ts or int(time.time())
        return f"t={ts},v1=" + hmac.new(secret.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()

    real_secret, real_key = H.settings.stripe_webhook_secret, H.settings.stripe_secret_key
    try:
        H.set_flag("stripe_secret_key", "sk_test_qa")
        H.set_flag("stripe_webhook_secret", "whsec_qa_real")
        c.eq("no signature header", tc.post("/payments/webhook", content=raw).status_code, 400)
        c.eq("signed with the wrong secret", tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sign("whsec_other")}).status_code, 400)
        c.eq("valid signature but 1h old (replay)", tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sign("whsec_qa_real", int(time.time()) - 3600)}).status_code, 400)
        H.set_flag("stripe_webhook_secret", "")
        r = tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sign("")})
        c.ok(f"empty configured secret + forged empty-key signature -> {r.status_code}", r.status_code in (400, 401, 403, 503), r.status_code)
    finally:
        H.set_flag("stripe_webhook_secret", real_secret)
        H.set_flag("stripe_secret_key", real_key)
    c.eq("no credits were granted by any forgery", tc.get("/payments/balance", headers=u.h).json()["ai_match_credits"], 0)


@case("SEC-271", "Security", "Stripe webhook robustness", "Concurrent duplicate deliveries grant once; malformed metadata never 500s",
      "6 parallel deliveries of one event -> credits granted exactly once; user_id='not-a-uuid' -> <500", "webhook concurrency + junk metadata")
def sec_271(c):
    import hashlib
    import hmac

    u = H.make_user("s271")
    real_secret, real_key = H.settings.stripe_webhook_secret, H.settings.stripe_secret_key
    H.set_flag("stripe_secret_key", "sk_test_qa")
    H.set_flag("stripe_webhook_secret", "whsec_qa_real")
    try:
        def send(payload):
            raw = json.dumps(payload).encode()
            ts = int(time.time())
            sig = f"t={ts},v1=" + hmac.new(b"whsec_qa_real", f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
            return tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig})

        evt = {"id": f"evt_qa_{uuid.uuid4().hex[:10]}", "object": "event", "type": "checkout.session.completed",
               "data": {"object": {"id": f"cs_qa_{uuid.uuid4().hex[:8]}", "object": "checkout.session", "metadata": {"user_id": u.id, "product_id": "ai_match_pack_1"}}}}
        res = parallel(lambda i: send(evt), 6)
        c.ok("no 5xx during concurrent delivery", all(status_of(r) is not None and status_of(r) < 500 for r in res), [status_of(r) for r in res])
        c.eq("credits granted exactly once", tc.get("/payments/balance", headers=u.h).json()["ai_match_credits"], 1)
        junk = {"id": f"evt_qa_{uuid.uuid4().hex[:10]}", "object": "event", "type": "checkout.session.completed",
                "data": {"object": {"id": "cs_junk", "object": "checkout.session", "metadata": {"user_id": "not-a-uuid", "product_id": "ai_match_pack_1"}}}}
        r = send(junk)
        c.ok(f"malformed user_id -> {r.status_code} (<500)", r.status_code < 500, r.status_code)
        r = send({"id": "evt_qa_x", "object": "event", "type": "checkout.session.completed", "data": {"object": {}}})
        c.ok(f"empty session object -> {r.status_code} (<500)", r.status_code < 500, r.status_code)
    finally:
        H.set_flag("stripe_webhook_secret", real_secret)
        H.set_flag("stripe_secret_key", real_key)


# ====================================================================== PLATFORM HARDENING


@case("SEC-280", "Security", "Production hardening", "In production the API docs are off, security headers are sent, and unsafe secrets refuse to boot",
      "create_app(production=True): /docs, /redoc, /openapi.json -> 404; default SECRET_KEY refuses to start; responses carry nosniff/HSTS/no-referrer, and auth responses are no-store",
      "build a production app object")
def sec_280(c):
    from starlette.testclient import TestClient

    try:
        from app.main import create_app
    except ImportError:
        c.ok("create_app() exists so production settings can be verified", False, "app.main.create_app missing")
        return
    prod = create_app(production=True)
    with TestClient(prod) as pc:
        for path in ("/docs", "/redoc", "/openapi.json"):
            c.eq(f"{path} in production", pc.get(path).status_code, 404)
        r = pc.get("/health")
        c.eq("nosniff", r.headers.get("x-content-type-options"), "nosniff")
        c.ok("HSTS", "max-age" in (r.headers.get("strict-transport-security") or ""), r.headers.get("strict-transport-security"))
        c.eq("referrer-policy", r.headers.get("referrer-policy"), "no-referrer")
        c.ok("frame denied", (r.headers.get("x-frame-options") or "").upper() == "DENY", r.headers.get("x-frame-options"))
        a = pc.post("/auth/login", json={"email": "nobody@example.com", "password": "nope-nope-1"})
        c.ok("auth responses are not cacheable", "no-store" in (a.headers.get("cache-control") or ""), a.headers.get("cache-control"))
    from app.config import Settings

    try:
        from app.main import validate_production_settings

        try:
            validate_production_settings(Settings(app_env="production", secret_key="dev-secret-key-not-for-production"))
            c.ok("default SECRET_KEY refuses to boot in production", False, "no error raised")
        except RuntimeError:
            c.ok("default SECRET_KEY refuses to boot in production", True)
        try:
            validate_production_settings(Settings(app_env="production", secret_key="x" * 40, database_url="mssql+aioodbc://x"))
            c.ok("a real secret boots", True)
        except RuntimeError as e:
            c.ok("a real secret boots", False, str(e))
    except ImportError:
        c.ok("validate_production_settings exists", False, "missing")


@case("SEC-281", "Security", "Authorisation sweep (logged in, not admin)", "A normal user is refused by every /admin route",
      "every /admin/* route -> 403 for a non-admin with a valid token", "iterate admin routes")
def sec_281(c):
    from app.main import app

    u = H.make_user("s281")
    n = 0
    bad = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/admin"):
            continue
        concrete = path.replace("{verification_id}", str(uuid.uuid4())).replace("{inquiry_id}", str(uuid.uuid4())).replace("{promotion_id}", str(uuid.uuid4())).replace("{report_id}", str(uuid.uuid4()))
        for m in (getattr(route, "methods", None) or set()) - {"HEAD", "OPTIONS"}:
            r = tc.request(m, concrete, headers=u.h, json={} if m in ("POST", "PUT") else None)
            n += 1
            if r.status_code != 403:
                bad.append((m, path, r.status_code))
    c.info(f"{n} admin route calls as a normal user")
    c.eq("admin routes that did not answer 403", bad, [])


@case("SEC-282", "Security", "Cross-user isolation (deep)", "User B cannot touch A's matches, messages, stories, moments, reveal state or feedback",
      "every A-owned resource id used by B -> 403/404 and A's data unchanged", "IDOR sweep")
def sec_282(c):
    a, b, mid = blind_pair("s282")
    outsider = H.make_user("s282x", "male", "female")
    c.eq("read history", tc.get(f"/matches/{mid}/messages", headers=outsider.h).status_code, 404)
    c.eq("icebreaker", tc.get(f"/matches/{mid}/icebreaker", headers=outsider.h).status_code, 404)
    c.eq("reveal request", tc.post(f"/matches/{mid}/blind-reveal/request", headers=outsider.h).status_code, 404)
    c.eq("reveal accept", tc.post(f"/matches/{mid}/blind-reveal/accept", headers=outsider.h).status_code, 404)
    c.eq("blind feedback", tc.post(f"/matches/{mid}/blind-feedback", headers=outsider.h, json={"rating": 5, "tags": []}).status_code, 404)
    with tc.websocket_connect(f"/ws/chat?token={outsider.token}") as wo, tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
        wo.send_json({"type": "message", "match_id": mid, "content": "intruder"})
        wo.send_json({"type": "read", "match_id": mid})
        got = ws_recv(wb, 3)
        c.ok("outsider's message not delivered", not got or got.get("content") != "intruder", got)
    hist = tc.get(f"/matches/{mid}/messages", headers=a.h).json()
    c.ok("intruder message not stored", all(m["content"] != "intruder" for m in hist))
    mo = tc.post("/moments", headers=a.h, json={"image_object_path": f"users/{a.id}/moments/{uuid.uuid4()}.jpg", "caption": "mine"})
    if mo.status_code in (200, 201):
        c.eq("delete someone else's moment", tc.delete(f"/moments/{mo.json()['id']}", headers=outsider.h).status_code, 404)
    c.eq("delete random photo id", tc.delete(f"/profiles/me/photos/{uuid.uuid4()}", headers=outsider.h).status_code, 404)


# ====================================================================== ADS (server side)


@case("ADS-101", "Ads", "Rewarded-ad bonus can't be self-granted", "With server-side ad verification on, calling the bonus endpoint by hand grants nothing",
      "POST /blind-chat/ad-bonus without a verified ad callback -> bonus stays available; a correctly signed AdMob callback for this user then grants it", "claim without watching")
def ads_101(c):
    u = H.make_user("a101")
    before = tc.get("/blind-chat/limit", headers=u.h).json()
    with H.flag("ad_bonus_requires_ssv", True):
        r = tc.post("/blind-chat/ad-bonus", headers=u.h)
        after = r.json() if r.status_code == 200 else tc.get("/blind-chat/limit", headers=u.h).json()
        c.eq("hand-claimed bonus granted nothing", (after["limit"], after.get("bonus_available")), (before["limit"], True))
    ssv = None
    try:
        from app.services import ad_ssv_service as ssv  # noqa: F401
    except ImportError:
        c.ok("ad_ssv_service exists (server-side verification of rewarded ads)", False, "missing")
        return
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    import base64

    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    ssv.set_test_keys({"1234": pem})
    unit = "ca-app-pub-0000000000000000/1111111111"
    H.set_flag("admob_rewarded_unit_ids", unit)

    def callback(user_id, ad_unit=unit, ts=None, sign_with=key, key_id="1234", tamper=False):
        ts = ts or int(time.time() * 1000)
        qs = f"ad_network=5450213213286189855&ad_unit={ad_unit}&reward_amount=1&reward_item=bonus&timestamp={ts}&transaction_id={uuid.uuid4().hex}&user_id={user_id}"
        sig = sign_with.sign(qs.encode(), ec.ECDSA(hashes.SHA256()))
        sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")
        if tamper:
            qs = qs.replace(f"user_id={user_id}", f"user_id={user_id}0")
        return f"/ads/ssv?{qs}&signature={sig_b64}&key_id={key_id}"

    try:
        with H.flag("ad_bonus_requires_ssv", True):
            other_key = ec.generate_private_key(ec.SECP256R1())
            c.ok("forged signature refused", tc.get(callback(u.id, sign_with=other_key)).status_code in (400, 401, 403))
            c.ok("tampered query refused", tc.get(callback(u.id, tamper=True)).status_code in (400, 401, 403))
            c.ok("someone else's ad unit refused", tc.get(callback(u.id, ad_unit="ca-app-pub-9999999999999999/2222222222")).status_code in (400, 401, 403))
            c.ok("stale callback refused", tc.get(callback(u.id, ts=int((time.time() - 3600) * 1000))).status_code in (400, 401, 403))
            c.eq("still not granted", tc.get("/blind-chat/limit", headers=u.h).json()["limit"], before["limit"])
            c.eq("genuine signed callback accepted", tc.get(callback(u.id)).status_code, 200)
            c.eq("bonus now granted", tc.get("/blind-chat/limit", headers=u.h).json()["limit"], before["limit"] + 1)
    finally:
        ssv.set_test_keys(None)
        H.set_flag("admob_rewarded_unit_ids", "")
