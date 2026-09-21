"""SooDaMate end-to-end QA harness.

Runs every case against the real app code (in-process ASGI) on top of the
real hosted database, the real R2 bucket and (for a few cases) the real
Twilio/Anthropic/Google APIs. Everything a case creates is tracked and
deleted afterwards (users, matches, R2 objects, promotions, ...).

Outbound *side effects on real people* are stubbed: push notifications (never
sent, only recorded), SMS (fake verifier), SMTP (fake sender).
"""
import io
import json
import os
import sys

try:  # results contain Korean/emoji; a redirected Windows console defaults to cp1252 and would crash the run
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass
import time
import traceback
import uuid
from datetime import date
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ["APP_ENV"] = "test"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import httpx  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services import phone_screening, push_service, storage_service  # noqa: E402

OUT = ROOT / "qa" / "out"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- case model

CASES: list[tuple] = []
RESULTS: list[dict] = []
DEFECTS: list[dict] = []


class Case:
    def __init__(self, cid, category, feature, scenario, steps, expected):
        self.cid, self.category, self.feature = cid, category, feature
        self.scenario, self.steps, self.expected = scenario, steps, expected
        self.checks: list[tuple] = []
        self.evidence: list[str] = []
        self.error: str | None = None

    def eq(self, label, got, want):
        self.checks.append((label, got, want, got == want))
        return got == want

    def ok(self, label, cond, got=None):
        self.checks.append((label, got if got is not None else bool(cond), True, bool(cond)))
        return bool(cond)

    def info(self, text):
        self.evidence.append(str(text))

    def finalize(self, seconds):
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c[3])
        if self.error:
            result = "FAIL"
            pct = round(100.0 * passed / (total + 1), 1)
        elif total == 0:
            result = "N/T"  # nothing was asserted (case skipped itself) - never report that as a pass
            pct = None
        else:
            result = "PASS" if passed == total else "FAIL"
            pct = round(100.0 * passed / total, 1)
        actual = "; ".join(
            f"{label}: {got!r}" + ("" if ok else f" (expected {want!r})") for label, got, want, ok in self.checks
        )
        if self.error:
            actual += f" | EXCEPTION: {self.error}"
        return {
            "id": self.cid,
            "category": self.category,
            "feature": self.feature,
            "scenario": self.scenario,
            "steps": self.steps,
            "expected": self.expected,
            "actual": actual,
            "evidence": " | ".join(self.evidence),
            "checks_total": total + (1 if self.error else 0),
            "checks_passed": passed,
            "match_pct": pct,
            "result": result,
            "seconds": round(seconds, 2),
        }


def case(cid, category, feature, scenario, expected, steps=""):
    def deco(fn):
        CASES.append((cid, category, feature, scenario, steps, expected, fn))
        return fn

    return deco


def skip_case(cid, category, feature, scenario, expected, reason, result="N/T"):
    """Cases that cannot be exercised for real from this environment
    (real SMS to a stranger, real card payment, physical devices...)."""
    RESULTS.append(
        {
            "id": cid, "category": category, "feature": feature, "scenario": scenario, "steps": "",
            "expected": expected, "actual": f"Not executed: {reason}", "evidence": "", "checks_total": 0,
            "checks_passed": 0, "match_pct": None, "result": result, "seconds": 0,
        }
    )


def defect(did, severity, title, detail, status="open", fix=""):
    DEFECTS.append({"id": did, "severity": severity, "title": title, "detail": detail, "status": status, "fix": fix})


# ------------------------------------------------------------------ runtime

tc: TestClient
TRACKED_USERS: list[str] = []
R2_KEYS: list[str] = []
PROMO_IDS: list[str] = []
PUSHES: list[dict] = []
SMS_STARTED: list[str] = []
EMAILS_SENT: list[tuple] = []
S: dict = {}  # shared state between cases


class FakeSms:
    def __init__(self):
        self.code = "123456"

    async def start(self, phone_number):
        SMS_STARTED.append(phone_number)

    async def check(self, phone_number, code):
        return code == self.code


class FakeEmail:
    async def send(self, to, subject, body):
        EMAILS_SENT.append((to, subject, body))


async def _record_push(db, user_id, title, body, data=None):
    PUSHES.append({"user_id": str(user_id), "title": title, "body": body, "data": data})


def install_stubs():
    import app.routers.auth as auth_router
    import app.routers.verification as verification_router

    auth_router.sms_verifier = FakeSms()
    verification_router.sms_verifier = auth_router.sms_verifier
    verification_router.email_sender = FakeEmail()
    push_service.send_to_user = _record_push

    async def _no_lookup(_n):
        return None

    phone_screening._lookup_line_type = _no_lookup  # no billed Lookup unless a case opts in


# Switches introduced by the security hardening. The general suites run with
# them relaxed (they create email accounts without phone/face verification and
# hammer the same endpoints thousands of times); suite_security switches each one
# on for exactly the cases that test it. object.__setattr__ so this also works
# against an older checkout where the setting does not exist yet.
RELAXED_FLAGS = {"rate_limit_enabled": False, "require_verified_accounts": False, "enable_legacy_auth": True, "verify_uploaded_objects": False}


def set_flag(name, value):
    object.__setattr__(settings, name, value)


class flag:
    """with H.flag("rate_limit_enabled", True): ...   (restores the relaxed value)"""

    def __init__(self, name, value):
        self.name, self.value = name, value

    def __enter__(self):
        set_flag(self.name, self.value)
        return self

    def __exit__(self, *exc):
        set_flag(self.name, RELAXED_FLAGS.get(self.name, getattr(settings, self.name, None)))


def start():
    global tc
    for _n, _v in RELAXED_FLAGS.items():
        set_flag(_n, _v)
    install_stubs()
    tc = TestClient(app)
    tc.__enter__()
    return tc


def stop():
    tc.__exit__(None, None, None)


def db(coro_fn):
    """Run an async DB helper on the TestClient's own event loop."""
    return tc.portal.call(coro_fn)


def track(user_id):
    TRACKED_USERS.append(str(user_id))
    return str(user_id)


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------- user helpers

class U:
    """A test user: ids, token, headers."""

    def __init__(self, user_id, token, refresh=None, email=None, phone=None):
        self.id, self.token, self.refresh, self.email, self.phone = user_id, token, refresh, email, phone
        self.h = hdr(token)


def signup_email(email, password="password123") -> U:
    r = tc.post("/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    j = r.json()
    track(j["user_id"])
    return U(j["user_id"], j["access_token"], j["refresh_token"], email=email)


def signup_phone(phone) -> U:
    r = tc.post("/auth/phone/confirm", json={"phone_number": phone, "code": "123456"})
    assert r.status_code == 200, r.text
    j = r.json()
    track(j["user_id"])
    return U(j["user_id"], j["access_token"], j["refresh_token"], phone=phone)


def profile_body(name="QA User", age=25, gender="male", interested_in="female", **kw):
    body = {
        "display_name": name,
        "legal_first_name": name,
        "birth_date": f"{date.today().year - age}-01-01",
        "gender": gender,
        "interested_in": interested_in,
        "min_age_pref": 18,
        "max_age_pref": 99,
    }
    body.update(kw)
    return body


def complete_profile(u: U, name="QA User", age=25, gender="male", interested_in="female", photo=True, **kw):
    r = tc.put("/profiles/me", headers=u.h, json=profile_body(name, age, gender, interested_in, **kw))
    assert r.status_code == 200, r.text
    if photo:
        p = tc.post(
            "/profiles/me/photos/confirm",
            headers=u.h,
            json={"gcs_object_path": f"users/{u.id}/photos/{uuid.uuid4()}.jpg", "position": 0},
        )
        assert p.status_code == 201, p.text
    return r.json()


def make_user(tag, gender="male", interested_in="female", age=25, **kw) -> U:
    u = signup_email(f"qa-{tag}-{uuid.uuid4().hex[:6]}@example.com")
    complete_profile(u, name=f"QA{tag}", age=age, gender=gender, interested_in=interested_in, **kw)
    return u


def mutual_match(a: U, b: U):
    """a likes b, b likes a -> match_id."""
    tc.post("/interactions/like", headers=a.h, json={"to_user_id": b.id})
    r = tc.post("/interactions/like", headers=b.h, json={"to_user_id": a.id})
    assert r.json()["matched"], r.text
    return r.json()["match_id"]


def make_admin(tag="admin") -> U:
    u = signup_email(f"qa-{tag}-{uuid.uuid4().hex[:6]}@example.com")
    complete_profile(u, name="QAAdmin")

    async def _flip():
        from app.database import async_session_factory
        from app.models.user import User

        async with async_session_factory() as s:
            row = await s.get(User, uuid.UUID(u.id))
            row.is_admin = True
            await s.commit()

    db(_flip)
    return u


# ------------------------------------------------------------- R2 / images

def make_jpeg(text, size=(640, 640), color=(255, 182, 193)):
    img = Image.new("RGB", size, color)
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, size[0] - 20, size[1] - 20], outline=(40, 40, 40), width=6)
    d.text((40, size[1] // 2), text, fill=(20, 20, 20))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def make_png(text, size=(480, 480), color=(173, 216, 230)):
    img = Image.new("RGB", size, color)
    ImageDraw.Draw(img).text((30, size[1] // 2), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def make_webp(text, size=(480, 480), color=(152, 251, 152)):
    img = Image.new("RGB", size, color)
    ImageDraw.Draw(img).text((30, size[1] // 2), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, "WEBP")
    return buf.getvalue()


def put_to_r2(upload_url, data: bytes, content_type: str):
    return httpx.put(upload_url, content=data, headers={"Content-Type": content_type}, timeout=30)


def r2_delete_all():
    client = storage_service._get_client()
    prefixes = []
    for uid in TRACKED_USERS:
        prefixes += [f"users/{uid}/", f"verifications/{uid}/"]
    deleted = 0
    for p in prefixes:
        try:
            resp = client.list_objects_v2(Bucket=settings.r2_bucket_name, Prefix=p)
            for obj in resp.get("Contents", []) or []:
                client.delete_object(Bucket=settings.r2_bucket_name, Key=obj["Key"])
                deleted += 1
        except Exception:
            pass
    for k in R2_KEYS:
        try:
            client.delete_object(Bucket=settings.r2_bucket_name, Key=k)
            deleted += 1
        except Exception:
            pass
    return deleted


def cleanup():
    from sqlalchemy import delete

    from app.database import async_session_factory
    from app.models.promotion import Promotion

    r2_deleted = r2_delete_all()

    async def _clean():
        from tests.helpers import _tracked_user_ids, cleanup_tracked_test_users

        if PROMO_IDS:
            async with async_session_factory() as s:
                await s.execute(delete(Promotion).where(Promotion.id.in_([uuid.UUID(p) for p in PROMO_IDS])))
                await s.commit()
        _tracked_user_ids.extend(TRACKED_USERS)
        await cleanup_tracked_test_users()

    db(_clean)
    return {"users": len(set(TRACKED_USERS)), "r2_objects": r2_deleted, "promotions": len(PROMO_IDS)}


# ------------------------------------------------------------------- runner

def run_all(only_prefix=None):
    for cid, category, feature, scenario, steps, expected, fn in CASES:
        if only_prefix and not any(cid.startswith(p) for p in only_prefix.split(",")):
            continue
        c = Case(cid, category, feature, scenario, steps, expected)
        t0 = time.time()
        try:
            fn(c)
        except AssertionError as e:
            c.error = f"AssertionError: {e}"
        except Exception as e:  # noqa: BLE001
            c.error = f"{type(e).__name__}: {e} | {traceback.format_exc()[-500:]}"
        res = c.finalize(time.time() - t0)
        RESULTS.append(res)
        flag = "OK " if res["result"] == "PASS" else ("N/T" if res["result"] == "N/T" else "BAD")
        print(f"[{flag}] {cid:10s} {str(res['match_pct']):>5}%  {scenario[:70]}", flush=True)
        if res["result"] != "PASS":
            print(f"      -> {res['actual'][:900]}", flush=True)
        if PARTIAL_NAME:
            save(PARTIAL_NAME)


PARTIAL_NAME = None


def admin():
    """Shared admin account, created on first use."""
    if "admin" not in S:
        S["admin"] = make_admin("shared")
    return S["admin"]


def save(name):
    (OUT / f"{name}.json").write_text(
        json.dumps({"results": RESULTS, "defects": DEFECTS, "pushes_recorded": len(PUSHES)}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
