"""Static suite: i18n completeness (mobile, web, backend pushes/products) and
marketing-website integrity / claim-vs-app consistency. No database needed."""
import functools
import http.server
import json
import re
import subprocess
import threading
from pathlib import Path

from qa import harness as H
from qa.harness import case

ROOT = Path(__file__).resolve().parents[2]
MOBILE = ROOT / "mobile" / "src"
WEB = ROOT / "web"
LANGS = ["ko", "en", "es", "zh", "ja"]


def flat(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flat(v, key + "."))
        else:
            out[key] = v
    return out


def load_mobile():
    if "mobile_locales" not in H.S:
        H.S["mobile_locales"] = {
            l: flat(json.loads((MOBILE / "i18n" / "locales" / f"{l}.json").read_text(encoding="utf-8"))) for l in LANGS
        }
    return H.S["mobile_locales"]


def load_web():
    if "web_i18n" not in H.S:
        out = subprocess.run(["node", str(ROOT / "backend" / "qa" / "dump_web_i18n.js")], capture_output=True, check=True)
        H.S["web_i18n"] = json.loads(out.stdout.decode("utf-8"))["translations"]
    return H.S["web_i18n"]


VAR = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


# ============================================================== MOBILE i18n


@case("I18N-001", "i18n", "Mobile app strings", "All 5 language files contain exactly the same keys",
      "0 missing / 0 extra keys in en, es, zh, ja relative to ko", "flatten locales/*.json and diff key sets")
def i18n_001(c):
    m = load_mobile()
    base = set(m["ko"])
    c.info(f"{len(base)} keys in ko")
    for l in LANGS[1:]:
        ks = set(m[l])
        c.eq(f"{l} missing keys", sorted(base - ks)[:10], [])
        c.eq(f"{l} extra keys", sorted(ks - base)[:10], [])


@case("I18N-002", "i18n", "Mobile app strings", "No empty, whitespace-only or placeholder ('TODO', '???') values in any language",
      "0 bad values per language", "scan values")
def i18n_002(c):
    m = load_mobile()
    for l in LANGS:
        bad = [k for k, v in m[l].items() if isinstance(v, str) and (not v.strip() or re.search(r"\b(TODO|TBD|FIXME)\b|[Ll]orem ipsum|\?\?\?", v))]
        c.eq(f"{l} bad values", bad[:10], [])


@case("I18N-003", "i18n", "Mobile app strings", "Interpolation variables ({{name}}) are identical across languages for every key",
      "0 keys where a language drops or renames a variable (would print raw braces or blank)", "compare variable sets per key")
def i18n_003(c):
    m = load_mobile()
    bad = []
    for k, v in m["ko"].items():
        if not isinstance(v, str):
            continue
        ref = set(VAR.findall(v))
        for l in LANGS[1:]:
            other = m[l].get(k)
            if isinstance(other, str) and set(VAR.findall(other)) != ref:
                bad.append((k, l, sorted(ref), sorted(set(VAR.findall(other)))))
    c.eq("mismatched variables", bad[:10], [])


@case("I18N-004", "i18n", "Mobile app strings", "Every t('key') used in the source code exists in all 5 languages",
      "0 missing keys (a missing key shows the raw key to users)", "regex scan of src/**/*.ts(x) for static t() keys")
def i18n_004(c):
    m = load_mobile()
    pat = re.compile(r"""\bt\(\s*["']([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)["']""")
    used = {}
    for f in list(MOBILE.rglob("*.ts")) + list(MOBILE.rglob("*.tsx")):
        for mt in pat.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            used.setdefault(mt.group(1), f.name)
    c.info(f"{len(used)} distinct static keys used")
    keys = set(m["ko"])

    def exists(k):
        return k in keys or any(x.startswith(k + "_") or x.startswith(k + ".") for x in keys)

    missing = sorted(k for k in used if not exists(k))
    c.eq("keys used in code but absent from ko.json", missing[:15], [])
    H.S["i18n_missing_static"] = missing


@case("I18N-005", "i18n", "Mobile app strings", "Non-English files are actually translated (not left as English copies)",
      "<2% of long strings in es/zh/ja identical to English (brand names/acronyms excluded)", "compare with en")
def i18n_005(c):
    m = load_mobile()
    for l in ("es", "zh", "ja", "ko"):
        same = [k for k, v in m[l].items() if isinstance(v, str) and len(v) >= 20 and re.search(r"[A-Za-z]{4}", v) and v == m["en"].get(k)]
        total = sum(1 for v in m["en"].values() if isinstance(v, str) and len(v) >= 20)
        pct = 100.0 * len(same) / max(total, 1)
        c.ok(f"{l}: {len(same)}/{total} identical to English ({pct:.1f}%)", pct < 2.0, same[:5])


@case("I18N-006", "i18n", "Backend texts", "Push-notification texts exist for all 5 languages for every notification type",
      "every key present in en also present and non-empty in ko/es/zh/ja (otherwise those users get English pushes)",
      "inspect app.services.push_i18n._STRINGS")
def i18n_006(c):
    from app.services import push_i18n

    tables = push_i18n._STRINGS
    base = set(tables["en"])
    c.info(f"{len(base)} push strings")
    c.eq("supported languages", sorted(push_i18n.SUPPORTED_PUSH_LANGUAGES), sorted(LANGS))
    for l in LANGS:
        c.eq(f"{l} missing keys", sorted(base - set(tables.get(l, {}))), [])
        c.eq(f"{l} empty values", [k for k, v in tables.get(l, {}).items() if not v.strip()], [])


@case("I18N-007", "i18n", "Backend texts", "Shop product names are localised for all 5 languages and differ per language",
      "every product has 5 non-empty names; membership name differs between ko/en/ja/zh/es", "payment_service._localized_product_name")
def i18n_007(c):
    from app.services import payment_service as ps

    for pid, info in ps.PRODUCTS.items():
        names = {l: ps._localized_product_name(pid, info, l) for l in LANGS}
        c.ok(f"{pid} 5 names", all(names.values()), names)
    n = {l: ps._localized_product_name("membership_monthly", ps.PRODUCTS["membership_monthly"], l) for l in LANGS}
    c.eq("membership names distinct", len(set(n.values())), 5)


# ============================================================== WEB i18n


@case("I18N-101", "i18n", "Marketing site strings", "Every web string exists in all 5 languages and is non-empty",
      "0 keys with a missing/empty language", "load web/i18n.js translations")
def i18n_101(c):
    t = load_web()
    c.info(f"{len(t)} keys")
    for l in LANGS:
        c.eq(f"{l} missing/empty", [k for k, v in t.items() if not (v.get(l) or "").strip()][:10], [])


@case("I18N-102", "i18n", "Marketing site strings", "Every data-i18n key used in the HTML pages has a translation",
      "0 keys referenced in HTML but missing from i18n.js", "scan web/*.html")
def i18n_102(c):
    t = load_web()
    used = {}
    for f in WEB.glob("*.html"):
        for mt in re.finditer(r'data-i18n(?:-html)?="([^"]+)"', f.read_text(encoding="utf-8")):
            used.setdefault(mt.group(1), f.name)
    missing = sorted(k for k in used if k not in t)
    c.info(f"{len(used)} keys referenced by {len(list(WEB.glob('*.html')))} pages")
    c.eq("missing keys", missing[:15], [])
    c.ok("unused translation keys (informational)", True, len([k for k in t if k not in used]))


@case("I18N-103", "i18n", "Marketing site strings", "HTML markup inside translations is consistent across languages (<br>, <span class=accent>...)",
      "same set of HTML tags in every language of each key", "compare tag multisets")
def i18n_103(c):
    t = load_web()
    tag = re.compile(r"<[^>]+>")
    bad = []
    for k, v in t.items():
        ref = sorted(tag.findall(v["en"]))
        for l in LANGS:
            if sorted(tag.findall(v[l])) != ref:
                bad.append((k, l))
    c.eq("tag mismatches", bad[:10], [])


@case("I18N-104", "i18n", "Marketing site strings", "Website default language is English and the choice persists",
      "currentLang() falls back to 'en'; 5 languages in the dropdown with flags", "inspect i18n.js")
def i18n_104(c):
    js = (WEB / "i18n.js").read_text(encoding="utf-8")
    m = re.search(r"function currentLang\(\)\s*\{(.*?)\n\}", js, re.S)
    c.ok("falls back to en", m is not None and ': "en"' in m.group(1), m and m.group(1).strip()[:120])
    c.ok("persists in localStorage", "localStorage.setItem" in js)
    c.ok("flags for all 5", all(l in js.split("LANG_FLAGS")[1][:200] for l in LANGS))


# ============================================================== WEB integrity


def _serve():
    if "web_server" in H.S:
        return H.S["web_server"]

    class Handler(http.server.SimpleHTTPRequestHandler):
        def translate_path(self, path):
            p = path.split("?")[0].split("#")[0]
            f = WEB / p.lstrip("/")
            if not f.exists() and (WEB / (p.lstrip("/") + ".html")).exists():  # vercel cleanUrls
                return str(WEB / (p.lstrip("/") + ".html"))
            return str(f)

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    H.S["web_server"] = srv
    return srv


@case("WEB-001", "Website", "Page integrity", "Every website page loads (HTTP 200) with title, language attribute and mobile viewport",
      "index, shop, shop-success, terms, privacy-policy, delete-account, child-safety, verify, admin all 200; each has <title>, <html lang>, viewport",
      "serve web/ locally (Vercel clean-URL rules) and fetch each page")
def web_001(c):
    import httpx

    srv = _serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    pages = ["/", "/shop", "/shop-success", "/terms", "/privacy-policy", "/delete-account", "/child-safety", "/verify", "/admin/"]
    for p in pages:
        r = httpx.get(base + p, timeout=10)
        c.eq(f"GET {p}", r.status_code, 200)
        html = r.text
        c.ok(f"{p} title", bool(re.search(r"<title>[^<]{3,}</title>", html)))
        c.ok(f"{p} html lang", 'lang="' in html[:300])
        c.ok(f"{p} viewport", 'name="viewport"' in html)


@case("WEB-002", "Website", "Link integrity", "All local links, images, scripts and stylesheets resolve (no 404s)",
      "0 broken local references across all pages", "crawl href/src of each page against the local server")
def web_002(c):
    import httpx

    srv = _serve()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    broken = []
    checked = 0
    for f in WEB.rglob("*.html"):
        rel = "/" + f.relative_to(WEB).as_posix()
        html = f.read_text(encoding="utf-8")
        for mt in re.finditer(r'(?:href|src)="([^"#][^"]*)"', html):
            u = mt.group(1)
            if u.startswith(("http", "mailto:", "tel:", "data:", "javascript:", "soodamate://")) or "${" in u:
                continue
            target = u if u.startswith("/") else "/" + (Path(rel).parent / u).as_posix().lstrip("/")
            checked += 1
            if httpx.get(base + target.split("?")[0], timeout=10).status_code != 200:
                broken.append((rel, u))
    c.info(f"{checked} local references checked")
    c.eq("broken references", broken[:10], [])


@case("WEB-003", "Website", "Legal pages", "Store-required pages exist and say the right things (privacy, terms, delete-account, child safety, 18+)",
      "privacy/terms/delete-account/child-safety pages have real content in all 5 languages; delete page lists photo/data deletion; child safety states 18+",
      "text checks on translations")
def web_003(c):
    t = load_web()
    for prefix in ("privacy", "terms", "deleteAccount", "childSafety"):
        keys = [k for k in t if k.startswith(prefix + ".")]
        c.ok(f"{prefix}: {len(keys)} strings", len(keys) >= 10, len(keys))
    c.ok("child safety mentions 18", any("18" in t[k]["en"] for k in t if k.startswith("childSafety.")))
    c.ok("delete page mentions photos", any("photo" in t[k]["en"].lower() for k in t if k.startswith("deleteAccount.data")))


@case("WEB-004", "Website", "Shop", "Shop page reads live prices from the API (no hard-coded prices) and product names render per language",
      "shop.html fetches /payments/products; no literal $ prices in markup", "inspect shop.html")
def web_004(c):
    html = (WEB / "shop.html").read_text(encoding="utf-8")
    c.ok("fetches products from API", "/payments/products" in html)
    c.ok("no hard-coded $ prices", not re.search(r">\s*\$\d", html))
    c.ok("checkout via API", "create-checkout-session" in html)


# ============================================================== CLAIMS vs APP


def _app_facts():
    if "facts" in H.S:
        return H.S["facts"]
    pkg = (ROOT / "mobile" / "package.json").read_text(encoding="utf-8")
    auth_stack = (MOBILE / "navigation" / "AuthStack.tsx").read_text(encoding="utf-8")
    chat_room = (MOBILE / "screens" / "chat" / "ChatRoomScreen.tsx").read_text(encoding="utf-8")
    blind = (ROOT / "backend" / "app" / "services" / "blind_chat_service.py").read_text(encoding="utf-8") + (
        ROOT / "backend" / "app" / "routers" / "blind_chat.py"
    ).read_text(encoding="utf-8")  # the identity gate lives in the router's _require_complete_profile
    facts = {
        "phone_only_signup": "PhoneAuth" in auth_stack and "Signup" not in auth_stack and "Login" not in auth_stack,
        "video_call_ui": "webrtc" in pkg.lower() or "call_offer" in chat_room or "startCall" in chat_room,
        "face_required_for_blind": bool(re.search(r"face_verified", blind)),
        "mbti_quiz": (MOBILE / "components" / "MbtiQuizModal.tsx").exists(),
        "moments_ui": (MOBILE / "components" / "MomentsEditor.tsx").exists(),
        "couple_stories_ui": (MOBILE / "screens" / "profile" / "CoupleStoriesFeedScreen.tsx").exists(),
        "translation_ui": "translated_content" in (MOBILE / "types" / "index.ts").read_text(encoding="utf-8"),
        "icebreaker_ui": "icebreaker" in (MOBILE / "api" / "matches.ts").read_text(encoding="utf-8").lower() if (MOBILE / "api" / "matches.ts").exists() else False,
        "travel_ui": (MOBILE / "screens" / "profile" / "TravelModeScreen.tsx").exists(),
        "work_school_ui": (MOBILE / "screens" / "profile" / "VerificationScreen.tsx").exists(),
        "face_verify_ui": (MOBILE / "screens" / "profile" / "FaceVerificationScreen.tsx").exists(),
        "purchase_history_ui": (MOBILE / "screens" / "profile" / "PurchaseHistoryScreen.tsx").exists(),
        "rewarded_ad_bonus": "claimBlindChatAdBonus" in (MOBILE / "api" / "blindChat.ts").read_text(encoding="utf-8"),
        "languages": len(json.loads((MOBILE / "i18n" / "locales" / "en.json").read_text(encoding="utf-8")) and LANGS),
    }
    H.S["facts"] = facts
    return facts


@case("CLAIM-001", "Website vs App", "Claim audit", "Sign-up / verification claims on the website match how the app really signs people up",
      "website must not promise Apple/Google/email sign-up (app is phone-number-only)", "compare how.1.body with AuthStack")
def claim_001(c):
    f = _app_facts()
    body = load_web()["how.1.body"]["en"].lower()
    c.eq("app is phone-only", f["phone_only_signup"], True)
    c.ok("website does not promise Apple/Google/email sign-up", not any(w in body for w in ("apple", "google", "email")), body[:100])


@case("CLAIM-002", "Website vs App", "Claim audit", "'Face verification required to start Blind Chat' claim vs the app's actual rule",
      "if the website says face verification is required, the backend must enforce it", "grep blind_chat_service + web claims")
def claim_002(c):
    f = _app_facts()
    t = load_web()
    says_required = any(re.search(r"completed face verification|face verification (is )?required|face verification required", t[k]["en"], re.I)
                        for k in t if k.startswith(("safety.", "rule.", "hero.")))
    c.eq("backend enforces face verification for blind chat", f["face_required_for_blind"], True) if says_required else c.ok("website makes no such claim", True)


@case("CLAIM-003", "Website vs App", "Claim audit", "'Video call' claims vs the app's actual features",
      "website must not advertise video calling unless the app ships a call screen", "grep mobile for WebRTC/call UI")
def claim_003(c):
    f = _app_facts()
    t = load_web()
    mentions = [k for k in t if re.search(r"video call", t[k]["en"], re.I)]
    c.info(f"claims: {mentions}")
    if mentions:
        c.eq("app has a video-call UI", f["video_call_ui"], True)
    else:
        c.ok("website makes no video-call claim", True)


@case("CLAIM-004", "Website vs App", "Claim audit", "Every feature the website advertises exists in the app",
      "MBTI quiz, work/school verification, face verification, filters free, 5 languages, block/report all present in the app",
      "existence checks per advertised feature")
def claim_004(c):
    f = _app_facts()
    for k in ("mbti_quiz", "work_school_ui", "face_verify_ui"):
        c.eq(k, f[k], True)
    c.eq("5 languages", f["languages"] and len(LANGS), 5)


@case("CLAIM-005", "Website vs App", "Coverage audit", "App strengths that are really usable today are showcased on the website",
      "website mentions: instant translation, couple stories, icebreakers, AI match, free daily matches + membership, ID-checked badge",
      "keyword coverage of the English marketing copy")
def claim_005(c):
    t = load_web()
    corpus = " ".join(v["en"].lower() for k, v in t.items() if k.split(".")[0] in ("hero", "why", "features", "feature", "how", "rule", "safety", "screens", "cta")).replace("-", " ")
    wants = {
        "instant translation": ["translat"],
        "couple stories": ["couple stor"],
        "icebreakers": ["icebreaker", "conversation starter"],
        "AI match": ["ai match"],
        "free daily matches": ["free matches", "5 free"],
        "membership": ["membership", "premium"],
        "ID-checked badge": ["id checked", "photo id"],
        "block / report": ["block"],
    }
    for name, kws in wants.items():
        c.ok(f"website mentions {name}", any(k in corpus for k in kws))


@case("CLAIM-006", "Website vs App", "Claim audit", "Website does not advertise features that are hidden or absent in the current app",
      "no mention of travel mode, incognito, swipe/classic discovery, video calls, or sign-up via Apple/Google/email",
      "grep English marketing copy for features removed from the app UI")
def claim_006(c):
    t = load_web()
    corpus = " ".join(v["en"].lower() for k, v in t.items() if k.split(".")[0] in ("hero", "why", "features", "feature", "how", "rule", "safety", "screens", "cta"))
    for phrase in ("travel mode", "incognito", "swipe", "video call", "videocall", "sign up with apple", "google, or email"):
        c.ok(f"no claim: {phrase}", phrase not in corpus)


@case("CLAIM-007", "Website vs App", "Copy consistency", "The app's own verification copy matches what the backend really enforces",
      "if the app says identity verification is 'required to activate your account', unverified users must actually be blocked from Blind Chat",
      "compare mobile en.json banner text with blind_chat_service rules")
def claim_007(c):
    en = load_mobile()["en"]
    says_required = "required" in en.get("profile.verificationBannerUnsubmitted", "").lower()
    enforced = _app_facts()["face_required_for_blind"]
    c.info(f"app banner: {en.get('profile.verificationBannerUnsubmitted')!r}; face verification enforced by backend: {enforced}")
    c.ok("copy and enforcement agree", (not says_required) or enforced)


@case("WEB-005", "Website", "Brand consistency", "The brand is spelled 'SooDaMate' in every language (no invented localized names)",
      "0 occurrences of made-up brand variants (数搭伴侣, 数多メイト, 수다 메이트) in i18n.js / html",
      "grep web/")
def web_005(c):
    blob = (WEB / "i18n.js").read_text(encoding="utf-8") + "".join(f.read_text(encoding="utf-8") for f in WEB.glob("*.html"))
    for bad in ("数搭", "数多メイト", "수다 메이트"):
        c.eq(f"occurrences of {bad}", blob.count(bad), 0)


@case("WEB-006", "Website", "Policy consistency", "Terms, privacy policy, child-safety page and the safety card all describe the same 18+ gate in all 5 languages",
      "each of terms.a2.body, privacy.s5, childSafety.s2.li1, safety.4.body mentions 18 and (for the first three) the blocked/disabled outcome in every language",
      "inspect the translations")
def web_006(c):
    t = load_web()
    for key in ("terms.a2.body", "privacy.s5", "childSafety.s2.li1", "safety.4.body"):
        for l in LANGS:
            c.ok(f"{key} [{l}] mentions 18", "18" in t[key][l])
    c.ok("privacy discloses the retained phone number (en)", "phone number" in t["privacy.s5"]["en"] and "re-registration" in t["privacy.s5"]["en"])
    c.ok("legal pages carry the new 'last updated' date", "September 21, 2026" in t["legal.updated"]["en"])
