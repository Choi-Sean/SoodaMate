"""Second half of the adversarial suite: races that need many parallel requests,
plus static checks of the ad / website configuration. Same rule as
suite_security: every case asserts the SECURE behaviour, so a FAIL is a finding.
"""
import json
import re
import time
import uuid
from pathlib import Path

from qa import harness as H
from qa.harness import case, tc
from qa.suite_security import _friends, age_slot, parallel, status_of
from qa.ws_util import ws_recv

_REPO = Path(__file__).resolve().parents[2]


def _read(rel):
    p = _REPO / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


# ====================================================================== RACES / RELIABILITY


@case("SEC-227", "Security", "Reconnect race", "A stale socket closing after a reconnect must not unregister the new connection",
      "connect twice as A, close the first socket, then B messages A: the second socket still receives it in real time", "double connect")
def sec_227(c):
    a, b, mid = _friends("s227")
    first = tc.websocket_connect(f"/ws/chat?token={a.token}")
    first.__enter__()
    second = tc.websocket_connect(f"/ws/chat?token={a.token}")
    ws2 = second.__enter__()
    try:
        try:
            first.__exit__(None, None, None)  # the old socket finally times out / closes
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
        with tc.websocket_connect(f"/ws/chat?token={b.token}") as wb:
            wb.send_json({"type": "message", "match_id": mid, "content": "are you there"})
            got = ws_recv(ws2, 8)
        c.eq("new connection still receives real-time messages", (got or {}).get("content"), "are you there")
    finally:
        try:
            second.__exit__(None, None, None)
        except Exception:  # noqa: BLE001
            pass


@case("SEC-261", "Security", "Swipe-limit bypass", "Free accounts can't exceed the swipe allowance by firing swipes in parallel",
      "25 parallel likes from a free account with a 20-per-6h allowance -> at most 20 succeed", "parallel swipes")
def sec_261(c):
    from app.services.match_service import SWIPE_LIMIT

    swiper = H.make_user("s261")
    targets = [H.signup_email(f"qa-s261t-{uuid.uuid4().hex[:8]}@example.com") for _ in range(SWIPE_LIMIT + 5)]
    res = parallel(lambda i: tc.post("/interactions/like", headers=swiper.h, json={"to_user_id": targets[i].id}), len(targets))
    ok = sum(1 for r in res if status_of(r) == 200)
    c.ok(f"successful swipes {ok} <= {SWIPE_LIMIT}", ok <= SWIPE_LIMIT, ok)
    c.ok("no 5xx", all(status_of(r) is not None and status_of(r) < 500 for r in res), [status_of(r) for r in res if status_of(r) and status_of(r) >= 500])


@case("SEC-262", "Security", "Double-tap queue join", "Joining the blind-chat queue several times at once never 500s or double-books",
      "8 parallel joins by one user -> no 5xx, exactly one waiting queue entry", "parallel queue joins")
def sec_262(c):
    age = age_slot()
    u = H.make_user("s262", "male", "female", age, min_age_pref=age, max_age_pref=age)
    body = {"categories": ["hobby"], "gender": "female", "min_age": age, "max_age": age}
    res = parallel(lambda i: tc.post("/blind-chat/queue", headers=u.h, json=body), 8)
    c.ok("no 5xx", all(status_of(r) is not None and status_of(r) < 500 for r in res), [status_of(r) for r in res])
    c.eq("single waiting entry", tc.get("/blind-chat/queue", headers=u.h).json()["status"], "waiting")
    tc.delete("/blind-chat/queue", headers=u.h)


class _StripeSandbox:
    """Signed webhooks + the Stripe API calls stubbed, so membership billing can be exercised without a card."""

    SECRET = "whsec_qa_billing"

    def __init__(self):
        import stripe

        self.stripe = stripe
        self.cancelled = []
        self.modified = []

    def __enter__(self):
        self.saved = (H.settings.stripe_secret_key, H.settings.stripe_webhook_secret, self.stripe.checkout.Session.create,
                      getattr(self.stripe.Subscription, "cancel", None), getattr(self.stripe.Subscription, "modify", None))
        H.set_flag("stripe_secret_key", "sk_test_qa_billing")
        H.set_flag("stripe_webhook_secret", self.SECRET)
        self.stripe.checkout.Session.create = lambda **kw: type("S", (), {"url": "https://checkout.example/session"})()
        self.stripe.Subscription.cancel = lambda sub_id, **kw: self.cancelled.append(sub_id)
        self.stripe.Subscription.modify = lambda sub_id, **kw: self.modified.append(sub_id)
        return self

    def __exit__(self, *exc):
        key, secret, create, cancel, modify = self.saved
        H.set_flag("stripe_secret_key", key)
        H.set_flag("stripe_webhook_secret", secret)
        self.stripe.checkout.Session.create = create
        if cancel is not None:
            self.stripe.Subscription.cancel = cancel
        if modify is not None:
            self.stripe.Subscription.modify = modify

    def send(self, payload):
        import hashlib
        import hmac

        raw = json.dumps(payload).encode()
        ts = int(time.time())
        sig = f"t={ts},v1=" + hmac.new(self.SECRET.encode(), f"{ts}.".encode() + raw, hashlib.sha256).hexdigest()
        return tc.post("/payments/webhook", content=raw, headers={"stripe-signature": sig})


def _purchase(user_id, product_id, sub_id):
    return {"id": f"evt_qa_{uuid.uuid4().hex[:10]}", "object": "event", "type": "checkout.session.completed",
            "data": {"object": {"id": f"cs_qa_{uuid.uuid4().hex[:8]}", "object": "checkout.session", "subscription": sub_id,
                                "metadata": {"user_id": user_id, "product_id": product_id}}}}


def _invoice(sub_id, period_end_ts, new_api_shape=False, etype="invoice.paid"):
    invoice = {"id": f"in_qa_{uuid.uuid4().hex[:8]}", "object": "invoice", "billing_reason": "subscription_cycle",
               "lines": {"data": [{"period": {"start": int(time.time()), "end": int(period_end_ts)}}]}}
    if new_api_shape:
        invoice["parent"] = {"subscription_details": {"subscription": sub_id}}
    else:
        invoice["subscription"] = sub_id
    return {"id": f"evt_qa_{uuid.uuid4().hex[:10]}", "object": "event", "type": etype, "data": {"object": invoice}}


def _premium_until(u):
    from datetime import datetime

    raw = tc.get("/profiles/me", headers=u.h).json().get("premium_until")
    return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


@case("PAY-101", "Payments", "Membership renewals", "A membership renewal charge extends premium (Stripe bills every cycle; premium must follow)",
      "invoice.paid for the subscription (old and new Stripe payload shapes, and invoice.payment_succeeded) moves premium_until to the invoice's period end; redelivery is idempotent; unknown subscriptions are ignored; a paid renewal appears in the purchase history",
      "checkout.session.completed then invoice.paid x3")
def pay_101(c):
    from datetime import datetime, timedelta, timezone

    u = H.make_user("p101")
    sub_r1 = f"sub_qa_r1_{uuid.uuid4().hex[:8]}"
    with _StripeSandbox() as sb:
        c.eq("first purchase accepted", sb.send(_purchase(u.id, "membership_monthly", sub_r1)).status_code, 204)
        first = _premium_until(u)
        c.ok("premium after the first period (~30 days)", first is not None and timedelta(days=28) < first - datetime.now(timezone.utc) < timedelta(days=31), first)

        month2 = time.time() + 60 * 24 * 3600
        renewal = _invoice(sub_r1, month2)
        c.eq("renewal event accepted", sb.send(renewal).status_code, 204)
        second = _premium_until(u)
        c.ok("renewal extended premium to the invoice's period end (~60 days)", second is not None and second - datetime.now(timezone.utc) > timedelta(days=58), second)
        sb.send(renewal)
        c.eq("redelivery of the same event changes nothing", _premium_until(u), second)

        month3 = time.time() + 90 * 24 * 3600
        sb.send(_invoice(sub_r1, month3, new_api_shape=True, etype="invoice.payment_succeeded"))
        third = _premium_until(u)
        c.ok("new-API payload shape (parent.subscription_details) also extends (~90 days)", third is not None and third - datetime.now(timezone.utc) > timedelta(days=88), third)

        c.eq("invoice for an unknown subscription is ignored (no error)", sb.send(_invoice("sub_qa_nobody", month3)).status_code, 204)
        hist = tc.get("/payments/history", headers=u.h).json()["items"]
        c.ok(f"renewals show up in purchase history ({len(hist)} items)", len(hist) >= 3, len(hist))

        c.eq("subscription deleted event accepted", sb.send({"id": f"evt_qa_{uuid.uuid4().hex[:10]}", "object": "event", "type": "customer.subscription.deleted", "data": {"object": {"id": sub_r1}}}).status_code, 204)
        c.eq("after deletion there is nothing left to cancel", tc.post("/account/subscription/cancel", headers=u.h).status_code, 400)
        c.ok("paid-for time is kept after the subscription ends", _premium_until(u) is not None and _premium_until(u) > datetime.now(timezone.utc))


@case("PAY-102", "Payments", "Double subscription", "Buying the same plan twice is refused, and switching plans cancels the superseded subscription (no orphaned billing)",
      "second monthly checkout -> 409; a yearly purchase while monthly is active cancels the monthly subscription in Stripe; cancel-at-period-end users can re-subscribe",
      "checkout x2, plan switch")
def pay_102(c):
    u = H.make_user("p102")
    sub_m1, sub_y1 = f"sub_qa_m1_{uuid.uuid4().hex[:8]}", f"sub_qa_y1_{uuid.uuid4().hex[:8]}"
    with _StripeSandbox() as sb:
        c.eq("first monthly checkout allowed", tc.post("/payments/create-checkout-session", headers=u.h, json={"product_id": "membership_monthly"}).status_code, 200)
        sb.send(_purchase(u.id, "membership_monthly", sub_m1))
        c.eq("same plan again while active -> 409", tc.post("/payments/create-checkout-session", headers=u.h, json={"product_id": "membership_monthly"}).status_code, 409)
        c.eq("a different plan is still purchasable", tc.post("/payments/create-checkout-session", headers=u.h, json={"product_id": "membership_yearly"}).status_code, 200)
        c.eq("one-time products are unaffected", tc.post("/payments/create-checkout-session", headers=u.h, json={"product_id": "ai_match_pack_1"}).status_code, 200)
        sb.send(_purchase(u.id, "membership_yearly", sub_y1))
        c.eq("switching to yearly cancelled the superseded monthly subscription", sb.cancelled, [sub_m1])
        c.eq("cancel-at-period-end works", tc.post("/account/subscription/cancel", headers=u.h).status_code, 200)
        c.eq("the cancel button targets the NEW subscription", sb.modified, [sub_y1])


@case("SEC-283", "Security", "Malformed ids", "A garbage id in a URL is a 422, never a 500 (admin routes and photo delete)",
      "admin approve/reject/read/resolve/action/deactivate/conversation with 'not-a-uuid' and DELETE /profiles/me/photos/not-a-uuid -> 422", "garbage path ids")
def sec_283(c):
    admin = H.admin()
    for method, path in (
        ("POST", "/admin/face-verifications/not-a-uuid/approve"),
        ("POST", "/admin/face-verifications/not-a-uuid/reject"),
        ("POST", "/admin/reports/not-a-uuid/action"),
        ("GET", "/admin/reports/not-a-uuid/conversation"),
        ("POST", "/admin/inquiries/not-a-uuid/read"),
        ("POST", "/admin/inquiries/not-a-uuid/resolve"),
        ("POST", "/admin/promotions/not-a-uuid/deactivate"),
    ):
        r = tc.request(method, path, headers=admin.h, json={} if method == "POST" else None)
        c.ok(f"{method} {path} -> {r.status_code}", r.status_code == 422, r.status_code)
    u = H.make_user("s283")
    r = tc.delete("/profiles/me/photos/not-a-uuid", headers=u.h)
    c.ok(f"DELETE /profiles/me/photos/not-a-uuid -> {r.status_code}", r.status_code == 422, r.status_code)


@case("SEC-290", "Security", "Location privacy (trilateration)", "Nobody can pin down another user's exact location by measuring distance from points they choose",
      "the profile-update location is attacker-controlled: from 3 self-chosen points the reported distances must NOT let you locate the target to within 0.8 km, and distances are whole km",
      "move own location to 3 points, read the target's distance each time, solve for the position")
def sec_290(c):
    import math

    age = age_slot()
    true_lat, true_lng = 37.5695, 126.9705  # deliberately off Seoul's coarse grid
    target = H.make_user("s290t", "female", "male", age, min_age_pref=age, max_age_pref=age, location_lat=true_lat, location_lng=true_lng)
    viewer = H.make_user("s290v", "male", "female", age, min_age_pref=age, max_age_pref=age)

    def km(a_lat, a_lng, b_lat, b_lng):
        p1, p2 = math.radians(a_lat), math.radians(b_lat)
        dl = math.radians(b_lng - a_lng)
        h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 6371.0 * 2 * math.asin(math.sqrt(h))

    probes = [(true_lat + 0.09, true_lng), (true_lat - 0.05, true_lng + 0.10), (true_lat - 0.05, true_lng - 0.10)]
    readings = []
    for lat, lng in probes:
        r = tc.put("/profiles/me", headers=viewer.h, json=H.profile_body("QAs290v", age, "male", "female", min_age_pref=age, max_age_pref=age, location_lat=lat, location_lng=lng))
        assert r.status_code == 200, r.text
        cands = tc.get("/discovery/candidates", headers=viewer.h).json()
        hit = next((x for x in cands if x["user_id"] == target.id), None)
        assert hit is not None and hit.get("distance_km") is not None, "target not visible in discovery"
        readings.append(hit["distance_km"])
    c.info(f"readings from the 3 probe points: {readings}")
    c.ok("distances are whole kilometres", all(float(d).is_integer() for d in readings), readings)

    best, best_err = None, 1e18
    lat = true_lat - 0.12
    while lat <= true_lat + 0.12:
        lng = true_lng - 0.12
        while lng <= true_lng + 0.12:
            err = sum((km(lat, lng, pl, pg) - d) ** 2 for (pl, pg), d in zip(probes, readings))
            if err < best_err:
                best, best_err = (lat, lng), err
            lng += 0.0005
        lat += 0.0005
    miss = km(best[0], best[1], true_lat, true_lng)
    c.ok(f"best trilateration estimate is {miss:.2f} km from the real spot (needs >= 0.8)", miss >= 0.8, round(miss, 3))


# ====================================================================== ADS + WEBSITE (static)


@case("ADS-001", "Ads", "app-ads.txt", "The website publishes app-ads.txt naming our AdMob publisher (AdMob limits apps without it)",
      "web/app-ads.txt exists with 'google.com, pub-<our id>, DIRECT, f08c47fec0942fa0' and the id matches the unit ids in eas.json", "static check")
def ads_001(c):
    eas = _read("mobile/eas.json")
    ids = set(re.findall(r"ca-app-pub-(\d{16})", eas))
    c.ok(f"exactly one AdMob publisher id in eas.json ({sorted(ids)})", len(ids) == 1, sorted(ids))
    txt = _read("web/app-ads.txt")
    c.ok("web/app-ads.txt exists", bool(txt.strip()))
    if ids:
        pub = next(iter(ids))
        c.ok("declares our publisher as DIRECT", f"google.com, pub-{pub}, DIRECT, f08c47fec0942fa0" in txt, txt[:120])


@case("ADS-002", "Ads", "Production ad units", "Every ad format the app shows has a real (non-test) unit id in the production build profile",
      "eas.json production env defines iOS+Android app ids, native unit ids AND rewarded unit ids, none of them Google's test ids", "static check")
def ads_002(c):
    prod = json.loads(_read("mobile/eas.json"))["build"]["production"]["env"]
    for key in ("EXPO_PUBLIC_ADMOB_IOS_APP_ID", "EXPO_PUBLIC_ADMOB_ANDROID_APP_ID", "EXPO_PUBLIC_ADMOB_IOS_NATIVE_UNIT_ID", "EXPO_PUBLIC_ADMOB_ANDROID_NATIVE_UNIT_ID",
                "EXPO_PUBLIC_ADMOB_IOS_REWARDED_UNIT_ID", "EXPO_PUBLIC_ADMOB_ANDROID_REWARDED_UNIT_ID"):
        val = prod.get(key, "")
        c.ok(f"{key} is a real id", bool(val) and "3940256099942544" not in val, val or "MISSING - the app silently falls back to Google's TEST ad unit")


@case("ADS-003", "Ads", "Ad safety configuration", "Ads are configured for an adults-only dating app",
      "request configuration sets maxAdContentRating, tagForChildDirectedTreatment=false and tagForUnderAgeOfConsent=false before the SDK starts", "static check of ads.native.ts")
def ads_003(c):
    src = _read("mobile/src/services/ads.native.ts")
    c.ok("maxAdContentRating set", "maxAdContentRating" in src)
    c.ok("child-directed treatment explicitly off", "tagForChildDirectedTreatment: false" in src)
    c.ok("under-age-of-consent explicitly off", "tagForUnderAgeOfConsent: false" in src)
    c.ok("configuration applied before initialize()", 0 <= src.find("setRequestConfiguration") < src.find("initialize()"))


@case("ADS-004", "Ads", "Tracking consent", "ATT prompt runs before the ad SDK starts, and the prompt text is localized",
      "requestTrackingPermissions before mobileAds().initialize(); iOS permission strings are localized for ko/es/zh/ja", "static check")
def ads_004(c):
    src = _read("mobile/src/services/ads.native.ts")
    c.ok("ATT before SDK init", 0 <= src.find("requestTrackingPermissionsAsync") < src.find("initialize()"))
    cfg = _read("mobile/app.config.js")
    c.ok("app.config.js declares localized iOS permission strings (locales)", "locales" in cfg and all(l in cfg for l in ("ko", "es", "zh", "ja")), "no `locales` block")


@case("ADS-005", "Ads", "SKAdNetwork", "iOS ad attribution lists Google's full buyer set, not just one id",
      "at least 30 SKAdNetworkIdentifier entries (Google's recommended list is ~50)", "static check of app.config.js")
def ads_005(c):
    n = len(re.findall(r"[a-z0-9]{10}\.skadnetwork", _read("mobile/app.config.js") + _read("mobile/skadnetwork-ids.json")))
    c.ok(f"SKAdNetwork ids configured: {n}", n >= 30, n)


@case("ADS-006", "Ads", "Rewarded ad verification (client)", "The rewarded ad is requested with server-side-verification options carrying the user id",
      "RewardedAd.createForAdRequest receives serverSideVerificationOptions.userId", "static check")
def ads_006(c):
    src = _read("mobile/src/services/rewardedAd.native.ts")
    c.ok("serverSideVerificationOptions with userId", "serverSideVerificationOptions" in src and "userId" in src)


@case("ADS-007", "Ads", "Sponsored label", "Ad cards are clearly labelled in every language",
      "swipe.sponsored exists (non-empty) in ko/en/es/zh/ja", "static check of locales")
def ads_007(c):
    for lang in ("ko", "en", "es", "zh", "ja"):
        data = json.loads(_read(f"mobile/src/i18n/locales/{lang}.json"))
        c.ok(f"{lang}: swipe.sponsored", bool((data.get("swipe") or {}).get("sponsored")), (data.get("swipe") or {}).get("sponsored"))


@case("ADS-008", "Ads", "Ad placement safety", "An ad card can't be accidentally liked/passed: the action buttons are replaced while an ad is showing",
      "SwipeScreen swaps ActionButtons for a Continue button while showAd is true", "static check")
def ads_008(c):
    src = _read("mobile/src/screens/swipe/SwipeScreen.tsx")
    c.ok("ActionButtons hidden while showAd", "showAd ? (" in src and "swipe.continue" in src)


@case("ADS-009", "Ads", "Privacy disclosure", "The privacy policy discloses AdMob / advertising ID in all five languages",
      "privacy.s4.li4 (AdMob) present with ko/en/es/zh/ja text", "static check of web/i18n.js")
def ads_009(c):
    js = _read("web/i18n.js")
    i = js.find('"privacy.s4.li4"')
    seg = js[i:i + 2400]
    for lang in ("ko", "en", "es", "zh", "ja"):
        c.ok(f"{lang} disclosure present", re.search(rf"\b{lang}:\s*\"[^\"]*AdMob", seg) is not None)


@case("ADS-010", "Ads", "Website scripts", "The website loads no third-party ad/tracker scripts",
      "no <script src=http...> in any web/*.html", "static check")
def ads_010(c):
    bad = []
    for f in (_REPO / "web").glob("*.html"):
        for src in re.findall(r"<script[^>]+src=[\"']([^\"']+)", f.read_text(encoding="utf-8")):
            if src.startswith("http"):
                bad.append((f.name, src))
    c.eq("external scripts on the website", bad, [])


@case("WEB-001", "Security", "Website security headers", "The website is served with clickjacking / content-type / referrer protections and a CSP",
      "vercel.json sets X-Frame-Options or frame-ancestors, nosniff, referrer policy, Content-Security-Policy and Permissions-Policy (the admin pages have approve/reject buttons)", "static check of web/vercel.json")
def web_001(c):
    cfg = json.loads(_read("web/vercel.json"))
    keys = {h["key"].lower(): h["value"] for rule in cfg.get("headers", []) for h in rule["headers"]}
    c.ok("nosniff", keys.get("x-content-type-options") == "nosniff")
    c.ok("referrer-policy", "referrer-policy" in keys)
    csp = keys.get("content-security-policy", "")
    c.ok("frame-ancestors 'none' (clickjacking)", "frame-ancestors 'none'" in csp or keys.get("x-frame-options", "").upper() == "DENY", csp or keys.get("x-frame-options"))
    c.ok("Content-Security-Policy present", "default-src" in csp, csp[:80])
    c.ok("Permissions-Policy present", "permissions-policy" in keys)


@case("WEB-002", "Security", "Third-party scripts on the admin console", "Every external script on a page that handles an admin token is pinned with Subresource Integrity",
      "admin/index.html loads Chart.js with integrity=sha512-... and crossorigin", "static check")
def web_002(c):
    bad = []
    for f in list((_REPO / "web").glob("*.html")) + list((_REPO / "web" / "admin").glob("*.html")):
        for tag in re.findall(r"<script[^>]+src=[\"'](?:https?:)?//[^>]+>", f.read_text(encoding="utf-8")):
            if "integrity=" not in tag or "crossorigin" not in tag:
                bad.append((f.name, tag[:90]))
    c.eq("external scripts without SRI", bad, [])


@case("APP-001", "Security", "Token hand-off to the shop page", "The access token is not put in a URL query string (server logs / history) when opening the shop",
      "mobile opens shop.html#token=... (fragment); shop.html reads the fragment and scrubs the address bar", "static check of openShop.ts and shop.html")
def app_001(c):
    src = _read("mobile/src/utils/openShop.ts")
    c.ok("no ?token= in the app's shop URLs", "?token=" not in src and "&token=" not in src)
    c.ok("token travels in the fragment", "#token=" in src)
    page = _read("web/shop.html")
    c.ok("shop.html reads location.hash", "location.hash" in page)
    c.ok("shop.html scrubs the token from the URL", "history.replaceState" in page)


@case("APP-002", "Security", "Crash reports don't carry credentials", "Failed API calls are reported to Sentry without the request headers/body (bearer token, phone numbers, SMS codes)",
      "reportApiError sends a plain Error + safe fields, not the AxiosError; Sentry beforeSend redacts Authorization", "static check")
def app_002(c):
    client = _read("mobile/src/api/client.ts")
    start = client.find("function reportApiError")
    body = client[start:start + 900]
    c.ok("the raw AxiosError is not passed to reportError", "reportError(\n    error," not in body and "reportError(error," not in body.replace("\r", ""))
    rep = _read("mobile/src/services/errorReporting.ts")
    c.ok("beforeSend scrubs credentials", "beforeSend" in rep and "authorization" in rep.lower())


@case("APP-003", "Security", "Location dataset integrity", "Every Korean region in the bundled location list has coordinates inside Korea (a wrong pair silently moves users to the US)",
      "all KR states/cities within lat 33-39, lng 124-132; every US state within the US", "static check of locationsData.ts")
def app_003(c):
    raw = next(line.strip().rstrip(",;") for line in _read("mobile/src/data/locationsData.ts").splitlines() if line.strip().startswith('"{'))
    data = json.loads(json.loads(raw))
    bad_kr = [(s["name"], s["latitude"], s["longitude"]) for s in data["states"] + data["cities"]
              if s["countryCode"] == "KR" and not (33 <= float(s["latitude"]) <= 39 and 124 <= float(s["longitude"]) <= 132)]
    c.eq("Korean regions outside Korea", bad_kr, [])
    bad_us = [(s["name"], s["latitude"], s["longitude"]) for s in data["states"]
              if s["countryCode"] == "US" and float(s["longitude"]) > 0 and s["name"] not in ("Guam", "Northern Mariana Islands", "United States Minor Outlying Islands", "Wake Island")]
    c.eq("US regions with a positive (eastern-hemisphere) longitude", bad_us, [])


@case("SEC-291", "Security", "Secrets in logs", "Access tokens sent as ?token= (the chat WebSocket) are redacted from server logs",
      "a log line containing /ws/chat?token=<jwt> is written with [redacted]", "emit uvicorn-style log records")
def sec_291(c):
    import io
    import logging

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    names = ("uvicorn.access", "uvicorn.error")
    for n in names:
        logging.getLogger(n).addHandler(handler)
        logging.getLogger(n).setLevel(logging.INFO)
    try:
        secret = "eyJSECRETSECRET.PAYLOAD.SIG"
        logging.getLogger("uvicorn.error").info('%s - "WebSocket %s" [accepted]', "1.2.3.4:5", f"/ws/chat?token={secret}")
        logging.getLogger("uvicorn.access").info('%s - "%s %s HTTP/%s" %d', "1.2.3.4:5", "GET", f"/x?a=1&token={secret}&b=2", "1.1", 200)
        out = stream.getvalue()
    finally:
        for n in names:
            logging.getLogger(n).removeHandler(handler)
    c.ok("token value is not in the log output", "SECRETSECRET" not in out, out[:200])
    c.ok("redaction marker present", "[redacted]" in out)
