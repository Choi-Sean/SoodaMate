# Environment variables

## backend/.env

| Var | Where to get it | Notes |
|---|---|---|
| `SECRET_KEY` | generate locally (`openssl rand -hex 32`) | JWT signing key, keep secret |
| `DATABASE_URL` | your hosted SQL Server instance | `mssql+aioodbc://user:pass@host:1433/db?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes&MARS_Connection=yes&Connection+Timeout=15` — **no Docker/local container**, connect directly to a real MSSQL instance for every environment including tests. `MARS_Connection=yes` is required or aioodbc throws "Connection is busy with results for another command." `Connection+Timeout=15` bounds how long a connection attempt can hang against a slow/unreachable shared-hosting instance — recommended after a real `pytest` run once silently hung indefinitely (no query-level timeout exists yet; this only bounds the initial connection handshake, not a stalled query on an already-open connection) |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud Console → APIs & Services → Credentials → OAuth client (type: Web application) | Used as the audience when verifying id_tokens from the mobile app |
| `APPLE_BUNDLE_ID` | — | Defaults to `com.soodalist.soodamate` (the real bundle id, already set in `mobile/app.config.js`) — only override if the bundle id ever changes. No separate Apple account/key needed beyond the paid Apple Developer Program membership App Store submission already requires; just enable the "Sign In with Apple" capability on the App ID in the developer portal |
| `R2_ACCOUNT_ID` | Cloudflare dashboard → R2 → Overview (right side, "Account ID") | Used to build the S3-compatible endpoint `https://<account_id>.r2.cloudflarestorage.com` |
| `R2_PRIVATE_BUCKET_NAME` | Cloudflare R2 → create a 2nd bucket with **public access off** | Optional. When set, face-verification selfies and ID-card photos are stored (and admin-viewed via 10-minute signed links) in this private bucket instead of the public-read main bucket, and account deletion sweeps both. The API token must be allowed to read/write it. Move existing files once with `python scripts/migrate_verifications_to_private_bucket.py --execute` (run it without `--execute` first for a dry run). Unset = single bucket, as before. |
| `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | Cloudflare dashboard → R2 → Manage R2 API Tokens → Create API Token (permission: Object Read & Write, scoped to the bucket below) | S3-style credential pair; the secret is only shown once at creation |
| `R2_BUCKET_NAME` | Cloudflare dashboard → R2 → Create bucket | Bucket for profile photos |
| `R2_PUBLIC_URL` | Cloudflare dashboard → R2 → (bucket) → Settings → Public Access → enable "R2.dev subdomain" (or attach a custom domain) | Base URL photos are served from, e.g. `https://pub-xxxxxxxx.r2.dev` — `PhotoOut.url` is built as `f"{R2_PUBLIC_URL}/{gcs_object_path}"` |
| `FIREBASE_CREDENTIALS_PATH` | Firebase Console → Project Settings → Service Accounts | Path to service account JSON for FCM push |
| `CORS_ORIGINS` | — | Comma-separated allowed origins for the mobile app / web |
| `STUN_URLS` | — | Defaults to Google's public STUN (`stun:stun.l.google.com:19302`), no account needed |
| `TURN_URL` / `TURN_USERNAME` / `TURN_CREDENTIAL` | Twilio Network Traversal Service, coturn, or similar | External prerequisite for reliable video calls across restrictive NATs — STUN-only works without it but calls may fail to connect on some networks. Empty until provisioned. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_ADDRESS` | Gmail app password, SendGrid, or similar transactional-email provider | Used to send work/school verification codes; `/verification/start` returns 503 until this is configured |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys | Powers LLM-assisted AI Match scoring (profile text + recent-chat tone). Unset means `find_ai_match` falls back to the deterministic tag-overlap score only — same "degrade, don't 503" convention as the other optional integrations above. |
| `DEV_PHONE_BYPASS_NUMBERS` / `DEV_PHONE_BYPASS_CODE` | you choose both | Comma-separated E.164 numbers that skip the real (billed) Twilio SMS send/check and accept one fixed code instead, so repeated manual testing from your own number(s) doesn't burn Twilio credits. Requires **both** set — empty `DEV_PHONE_BYPASS_CODE` (the default) disables this entirely, even for numbers listed in the other var. Every other number always goes through real Twilio Verify unchanged. Treat the code like a password. |
| `BLOCK_VOIP_PHONE_NUMBERS` | — | Defaults to `true`. Rejects internet/VoIP/virtual numbers (Google Voice, TextNow, Korean 070/050, landlines) at phone signup and when attaching a phone in `/verification/phone/start`, via Twilio Lookup Line Type Intelligence (~$0.008 per *new* number; existing accounts and `DEV_PHONE_BYPASS_NUMBERS` skip it). Uses the same `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN`; a Lookup outage or an account without Lookup access fails **open** (number allowed, error logged). Set `false` if it ever misclassifies real carriers. The free Korean rule (`+82` must be a `01x` mobile) always stays on. |
| `RATE_LIMIT_ENABLED` | — | Defaults to `true`. In-process sliding-window limits (429 + `Retry-After`) on SMS start (5 per number / 10 min, plus a global cap), SMS-code confirm and login (10 per number/email / 10 min), uploads, inquiries, reports, swipes, blind-chat queue and chat messages (30 per 10 s). Per-process, exact for the single Railway instance; move to Redis before running more than one replica. |
| `SMS_GLOBAL_PER_10MIN` | — | Defaults to `300`. App-wide ceiling on SMS Verify sends per 10 minutes — the backstop against SMS-pumping fraud however many numbers/IPs an attacker rotates through. Raise it if a real launch spike trips it. |
| `REQUIRE_VERIFIED_ACCOUNTS` | — | Defaults to `true`. Blind Chat / AI Match are refused (`403 identity verification required`) unless the account passed selfie + ID face verification — the same rule the app shows in its UI, now enforced by the server so a direct API call can't skip it. |
| `ENABLE_LEGACY_AUTH` | — | Defaults to `false`. `POST /auth/signup` (email), `/auth/google` and `/auth/apple` answer 404: the app only offers phone sign-in, and those paths created accounts that never passed phone verification or the VoIP screen. `/auth/login` and `/auth/refresh` keep working for existing accounts (the admin console uses email login). |
| `VERIFY_UPLOADED_OBJECTS` | — | Defaults to `true`. Confirming a photo / moment / story photo checks the file really exists in R2, is ≤ 20 MB (video ≤ 150 MB) and has the right magic bytes; rejected files are deleted. Only the test suites switch this off. |
| `AD_BONUS_REQUIRES_SSV` / `ADMOB_REWARDED_UNIT_IDS` | AdMob console → Apps → your app → Ad units → the **Rewarded** unit → *Server-side verification* | Defaults to `false` / empty. Set the callback URL to `https://<api-host>/ads/ssv`, put the comma-separated rewarded unit ids (`ca-app-pub-…/…`) in `ADMOB_REWARDED_UNIT_IDS`, then set `AD_BONUS_REQUIRES_SSV=true`. From then on the daily +1 Blind Chat match is granted only by Google's signed callback, never by the app saying "I watched it" (`POST /blind-chat/ad-bonus` becomes a status read). Flip it on only after the callback URL is saved in AdMob, or the bonus will never be granted. |
| `MAX_JSON_BODY_BYTES` | — | Defaults to `262144`. Larger request bodies are refused with 413 before parsing (uploads go straight to R2, so nothing legitimate is big). |
| *(production boot checks)* | — | When `APP_ENV=production` (or Railway's `RAILWAY_ENVIRONMENT*` is present) the API refuses to start if `SECRET_KEY` is missing/the dev default/shorter than 16 chars, `DATABASE_URL` is the dev default, or `CORS_ORIGINS` contains `*`, and the interactive `/docs`, `/redoc`, `/openapi.json` are switched off. |
| `STRIPE_SECRET_KEY` | Stripe Dashboard → Developers → API keys | Server-side secret key; enables `/payments/*` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard → Developers → Webhooks → your endpoint → Signing secret | Verifies `POST /payments/webhook` came from Stripe (an empty value makes the endpoint refuse everything). **The endpoint must be subscribed to three events:** `checkout.session.completed`, `invoice.paid` (membership renewals — without it Stripe charges the customer each cycle but premium lapses after the first period) and `customer.subscription.deleted`. |
| `WEB_BASE_URL` | — | The deployed marketing site's origin (Vercel URL), used to build Stripe Checkout `success_url`/`cancel_url` |

## mobile/.env (via `EXPO_PUBLIC_*` vars, see `app.config.js`)

| Var | Where to get it | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_BASE_URL` | — | Points at local backend or the deployed Railway URL |
| `EXPO_PUBLIC_MARKETING_SITE_URL` | — | The deployed Vercel URL; used to open the Stripe shop (`Linking.openURL`) and privacy/terms links |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` | same OAuth client as backend's `GOOGLE_OAUTH_CLIENT_ID` | `@react-native-google-signin/google-signin` needs the *web* client id, not an android/iOS one |
| `EXPO_PUBLIC_ADMOB_ANDROID_APP_ID` / `EXPO_PUBLIC_ADMOB_IOS_APP_ID` | AdMob console, after app registered | The *app*-level IDs (one per platform). **iOS set** (real AdMob app, `eas.json`'s three build profiles) — **Android still on Google's test ID**, no AdMob app created for it yet |
| `EXPO_PUBLIC_ADMOB_ANDROID_NATIVE_UNIT_ID` / `EXPO_PUBLIC_ADMOB_IOS_NATIVE_UNIT_ID` | AdMob console → Ad units, after creating a **Native Advanced** unit per platform (`src/components/AdCard.native.tsx`, the in-swipe-deck/blind-chat-waiting sponsored card) | **iOS set** — **Android still on Google's test unit ID** |
| `EXPO_PUBLIC_ADMOB_ANDROID_REWARDED_UNIT_ID` / `EXPO_PUBLIC_ADMOB_IOS_REWARDED_UNIT_ID` | AdMob console → Ad units, after creating a **Rewarded** unit per platform (`src/services/rewardedAd.native.ts` — Blind Chat's "watch an ad for +1 match today" bonus) | Not set yet — falls back to Google's test rewarded unit ID, same convention as the native unit ids above |
| `FIREBASE_CONFIG` | Firebase Console → Project settings → your app | google-services.json / GoogleService-Info.plist |
| `EXPO_PUBLIC_SENTRY_DSN` | sentry.io → create a free React Native project → Settings → Client Keys (DSN) | Crash/error reporting (`src/services/errorReporting.ts`); no-ops entirely (app behaves exactly as before) until this is set. A DSN is meant to be public/client-embeddable — not a secret. Set it in `eas.json`'s three build profiles once you have one; the config plugin for readable (symbolicated) native stack traces isn't wired up yet, see the comment in `app.config.js`. |

**iOS App Tracking Transparency**: `app.config.js` already declares `NSUserTrackingUsageDescription` (via the `expo-tracking-transparency` plugin) and `ads.native.ts` requests the permission before initializing AdMob — required by Apple for any app using an IDFA-capable SDK like AdMob, not optional. No env var needed; nothing to configure here beyond having a real AdMob account eventually.

The app's own custom URL scheme (`soodamate://`) is fixed in `app.config.js` (`scheme: "soodamate"`) — no env var needed. It's used for the Stripe-purchase-complete deep link back from the website (`soodamate://shop`, handled by `mobile/src/services/deepLinking.ts`).

## Deployment-platform config (not app env vars, but required)

| Where | What | Notes |
|---|---|---|
| Railway project settings | root directory = `backend/`, all vars above | Dockerfile-based build; `$PORT` is provided by Railway automatically |
| Vercel project settings | root directory = `web/` | Static site, no build step, no env vars needed |
| Apple App Store Connect | App Store Connect API key (Issuer ID, Key ID, `.p8` file) | Configured under `submit.production.ios` in `mobile/eas.json` for `eas submit` |
| Your SQL Server instance | firewall/connection allowlist for both your dev machine and Railway's egress | Not created by this repo — the user provisions and owns this instance directly (no Docker, no local container, per explicit project policy) |

None of the external accounts above (other than the user-provided MSSQL instance) exist yet by default — they're created by the user as each phase needs them.
