# Architecture

See the approved build plan at project inception time for the original 12-phase
rationale; Phases 13-18 (Bumble-style expansion + MSSQL migration) were added
after that plan shipped. This doc is the living reference as the system evolves.

## Components

- **backend/** — FastAPI, **MSSQL** (SQL Server, `aioodbc`/`pyodbc`), WebSocket chat, deployed to **Railway**
- **mobile/** — React Native (Expo, dev client), iOS + Android, i18n (ko/en/es/zh/ja)
- **web/** — static marketing site + Stripe-powered shop, deployed to **Vercel**, i18n (ko/en/es/zh/ja)

## Data flow (high level)

1. Mobile authenticates via Google/Kakao/email → backend issues app JWT (access + refresh)
2. Mobile fetches candidates from `/discovery/candidates`, sends Like/Pass/SuperLike to `/interactions/{action}`
3. Mutual like/superlike → backend creates a `matches` row, pushes a notification to both users. If the pair is exactly `{male, female}`, the match is **restricted**: only the female user may send the first message, within 24h, or the match lazily expires (see Bumble rule below).
4. Matched users chat over `/ws/chat` (WebSocket); messages persist to MSSQL; offline delivery falls back to FCM push
5. The same `/ws/chat` connection also carries WebRTC signaling frames (`call_offer`/`call_answer`/`call_ice_candidate`/`call_end`) for video calls — no second realtime channel
6. Photos upload directly to GCS via presigned URLs, never proxied through the API
7. Paid credits (superlike packs, boost) are bought on the **website**, not in-app — Stripe Checkout, webhook-granted, deep-linked back into the app via `sudadate://shop`

## Database schema

See `backend/app/models/` — this is the source of truth; do not duplicate the schema here as it will drift. Tables: `users`, `auth_providers`, `profiles`, `photos`, `swipes`, `matches`, `messages`, `blocks`, `reports`, `push_tokens`, `call_sessions`, `verifications`, `payment_transactions`.

All UUID columns use SQLAlchemy's portable `Uuid` type (native `UNIQUEIDENTIFIER` on MSSQL); all text columns use `Unicode`/`UnicodeText` so Korean text round-trips correctly (plain `String`/`Text` map to non-Unicode `VARCHAR` on MSSQL and would silently corrupt it).

**MSSQL FK note**: `Swipe`, `Match`, `Block`, `Report`, `CallSession` each have two FKs pointing at `users` — MSSQL rejects multiple cascade paths to the same table, so none of those FKs use `ondelete="CASCADE"`. `DELETE /account/me` (`backend/app/routers/account.py`) explicitly deletes swipes/matches/blocks/reports before deleting the user row; everything else (profile, photos, auth_providers, push_tokens, verifications, payment_transactions) still cascades automatically since it has only one FK path back to `users`.

## Auth

All four providers (Google, Kakao, Apple, email) converge on the same app-level JWT via `app/services/auth_service.py`. Adding a new provider (e.g. phone OTP later) means implementing `OAuthProviderVerifier` (`app/core/auth_provider_base.py`) and adding one router endpoint — the issuance/session logic never changes.

**Sign in with Apple** (`app/services/oauth/apple.py`) isn't optional polish — Apple App Store Review Guideline 4.8 requires any app offering a third-party login (this app offers Google) to also offer Sign in with Apple, or risk rejection at review. Unlike Kakao's opaque access token (verified via a live `kapi.kakao.com` call) or Google's SDK-verified id_token, Apple's `identityToken` is a JWT the backend verifies locally against Apple's public JWKS (`https://appleid.apple.com/auth/keys`), checking signature, issuer, expiry, and audience (the app's bundle id). Apple only includes the user's email in the token on their very first sign-in for this app — later sign-ins omit it, which `login_or_signup_with_provider` already handles generically (a missing `identity.email` is normal for pure-OAuth users). Mobile-side, `expo-apple-authentication`'s `AppleAuthenticationButton` is shown only on iOS (Android has no Apple Sign-In capability and Apple's own guideline doesn't require it there).

## Bumble-style first-message rule + 24h match expiry (Phase 14)

At match creation, `match_service.record_swipe` (via the `sp_RecordSwipe` stored procedure) snapshots `restricted_to_user_id`: if the pair is exactly `{male, female}`, the match is restricted to the female user with a `first_message_deadline` 24h out; any other gender combination (same-gender, or either profile is `other`) is unrestricted from the start, matching Bumble's real behavior. There is no scheduler — expiry is lazy: `chat_service.get_active_match_for_user` (the single choke point used by both the WS handler and `GET /matches/{id}/messages`) checks-and-flips `is_active=False` on access if the deadline passed with no first message sent, and `list_matches` does the same bulk flip-then-select so `/matches` never shows a stale-expired match. A rejected first-message attempt gets a `{"type":"error","code":"first_message_restricted"}` WS frame back.

## Video calling (Phase 15)

`CallSession` rows track caller/callee/status/timestamps. Signaling piggybacks on the existing `/ws/chat` connection (see `_handle_call_offer/_answer/_ice_candidate/_end` in `app/routers/ws_chat.py`) — gated only by "match still active" (same check as messaging), deliberately independent of the Phase 14 first-message restriction. STUN is always available (`stun:stun.l.google.com:19302`, no account needed); TURN is an external prerequisite (Twilio/coturn/etc.) surfaced via `GET /calls/ice-servers` — never hardcoded client-side. On disconnect, any of that user's active calls are ended server-side and the peer is notified with `reason: "peer_offline"`.

**Mobile status**: entirely unbuilt. This needs `react-native-webrtc` (with the same `.native.ts`/`.web.ts` platform-split treatment already forced on AdMob, since Metro bundles native-only modules into the web build even behind a runtime `Platform.OS` check), the `@config-plugins/react-native-webrtc` Expo plugin, a new native build, and — architecturally — promoting the WebSocket connection from `useChatSocket`'s current per-`ChatRoomScreen` scope to a single app-level `SocketProvider` so an incoming call can be received while the user isn't sitting in that exact chat room. None of this can be verified in a sandbox with no device/emulator.

## Verification badges (Phase 16)

`Verification` rows (user_id, kind∈{work,school}, email, domain, hashed 6-digit code, expiry, attempts). A blocklist of common personal-email domains (gmail/naver/kakao/daum/etc.) is the v1 heuristic for "is this a real work/school email." Mirrors the OAuth-provider abstraction pattern: `EmailSender` ABC (`app/core/email_sender_base.py`) with a concrete `smtplib`-via-`asyncio.to_thread` implementation. Unlike push notifications' silent no-op-when-unconfigured pattern, an unconfigured SMTP here fails loudly with a 503 — a verification code that silently never arrives is worse than an honest error.

## Paid superlike/boost via Stripe web checkout (Phase 17)

**No in-app purchase** — store commission was explicitly rejected as too expensive. Credits are bought through the marketing website's `web/shop.html` (Stripe Checkout, inline `price_data` so no pre-created Stripe product/price IDs are needed, only the secret key), and granted to the account via `POST /payments/webhook` — idempotent via `try_insert` keyed on `stripe_event_id`, so webhook redelivery never double-grants. Since the website has no login system of its own, the mobile app passes its JWT as a URL query param when it opens the shop (`Linking.openURL(...&token=...)`); the website reads it out of the URL. After a successful purchase, `web/shop-success.html` links back to `sudadate://shop`, which the app's `initDeepLinking` (`mobile/src/services/deepLinking.ts`) catches to refetch the profile and land on the profile tab. Superlike gating: 1 free per day, then consumes credits, else `402`. Boost purchase and activation are separate steps (`POST /payments/activate-boost`, 30-minute window) — a purchase shouldn't silently start burning visibility time unattended.

## Incognito + travel mode (Phase 18)

Not paywalled in this v1 scope. Incognito adds one discovery filter (`~Profile.is_incognito`) — doesn't touch existing swipe/match rows, so it doesn't retroactively hide from people who already matched/liked the user. Travel mode is a stateless `_effective_location()` check (`travel_expires_at > now()`) applied to both the viewer's and each candidate's location in the discovery haversine calc, so a traveling user is genuinely repositioned into their destination's pool for others too. No GPS-capture or geocoding UI exists in mobile, so `TravelModeScreen` uses a short preset-city list plus manual lat/lng entry.

## Deployment

- **Backend** → Railway (Dockerfile-based, `$PORT` respected). See `docs/DEPLOYMENT_RAILWAY.md`.
- **Website** → Vercel (static, no build step).
- **Database** → user-provided hosted SQL Server instance (not Docker — containers are explicitly not used anywhere in this project's workflow; tables/stored procedures are created by connecting directly, see `infra/mssql/stored_procedures.sql`).
