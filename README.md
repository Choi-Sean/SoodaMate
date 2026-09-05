# 수다메이트 (SooDa Mate)

Dating app monorepo — part of the 수다리스트 (SooDaList) app family. Bumble-style mechanic: unlimited swipe via Like/Pass/SuperLike buttons, women-message-first with a 24h match expiry, video call, work/school verification badges, paid superlike/boost via Stripe web checkout (no in-app purchase), incognito/travel mode.

## Structure

- `backend/` — FastAPI REST + WebSocket API (Python), MSSQL (SQL Server)
- `mobile/` — React Native (Expo) app for iOS/Android, i18n (ko/en/es/zh/ja)
- `web/` — marketing/landing website + Stripe shop (plain HTML/CSS/JS), i18n (ko/en/es/zh/ja)
- `infra/mssql/` — stored procedures (`sp_RecordSwipe`, `sp_UpsertBlock`, `sp_UpsertPushToken`) for the core transactional logic
- `docs/` — architecture, API reference, env var reference, deployment and app-store submission guides

## Local development

**No Docker, no containers** — connect the backend directly to a real hosted MSSQL instance (see `docs/ENV_VARS.md` for `DATABASE_URL`). Then:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Backend API at `http://localhost:8001` (docs at `/docs`).

See each subfolder's README for component-specific setup (`backend/README.md`, `mobile/README.md`, `web/README.md`).

## Build status

**Phases 0-12** (original scope) and **13-18** (Bumble expansion + MSSQL migration) are code-complete:

- **Backend** — full schema on MSSQL, email/Google/Kakao/Apple auth (Sign in with Apple included for App Store Review Guideline 4.8 compliance), profiles/discovery/matching (with Bumble first-message rule + 24h expiry), WebSocket chat + video-call signaling, verification badges, Stripe payments, incognito/travel mode, push, safety, account deletion. All 48 tests pass against the real hosted MSSQL instance (occasionally needs a re-run on Windows — see `backend/README.md`'s note on a known intermittent test-harness crash unrelated to the app's own code).
- **Mobile** — full navigation (auth → profile setup → main tabs), Discover/Matches/Chat/Profile/Settings/Travel/Verification screens, 5-language i18n, ads, push notifications with deep-linking, Stripe shop deep link (`sudamate://shop`). Type-checks clean and bundles clean for web. **Not yet built**: video call UI (Phase 15) — needs `react-native-webrtc`, a native rebuild, and an app-level socket refactor, none of which can be verified in this sandbox (no device/emulator). **Not yet verified on a real iOS/Android device or simulator** for anything else either — see `mobile/README.md`.
- **Website** — Hinge/Bumble/Tinder-inspired marketing page, real privacy policy/terms, Stripe-powered shop, 5-language i18n, verified in-browser.
- **Deployment / store submission** — backend deploys to **Railway** (see `docs/DEPLOYMENT_RAILWAY.md`), website to **Vercel**, store submission via EAS (`docs/APP_STORE_SUBMISSION.md`). Execution is a manual step requiring your own Railway/Vercel/Apple/Google accounts.

What's left before this is a live product: create the external accounts (Google OAuth, Kakao, Firebase, AdMob, Stripe, SMTP provider, TURN provider, Apple Developer, Play Console — all listed in `docs/ENV_VARS.md`), run the deployment guide, run the store submission guide, build the Phase 15 video-call mobile UI, and do a real end-to-end pass on physical devices.
