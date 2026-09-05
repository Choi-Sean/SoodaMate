# Environment variables

## backend/.env

| Var | Where to get it | Notes |
|---|---|---|
| `SECRET_KEY` | generate locally (`openssl rand -hex 32`) | JWT signing key, keep secret |
| `DATABASE_URL` | your hosted SQL Server instance | `mssql+aioodbc://user:pass@host:1433/db?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes&TrustServerCertificate=yes&MARS_Connection=yes&Connection+Timeout=15` — **no Docker/local container**, connect directly to a real MSSQL instance for every environment including tests. `MARS_Connection=yes` is required or aioodbc throws "Connection is busy with results for another command." `Connection+Timeout=15` bounds how long a connection attempt can hang against a slow/unreachable shared-hosting instance — recommended after a real `pytest` run once silently hung indefinitely (no query-level timeout exists yet; this only bounds the initial connection handshake, not a stalled query on an already-open connection) |
| `GOOGLE_OAUTH_CLIENT_ID` | Google Cloud Console → APIs & Services → Credentials → OAuth client (type: Web application) | Used as the audience when verifying id_tokens from the mobile app |
| `KAKAO_REST_API_KEY` | Kakao Developers → App → App Keys | REST API key |
| `APPLE_BUNDLE_ID` | — | Defaults to `com.soodalist.soodamate` (the real bundle id, already set in `mobile/app.config.js`) — only override if the bundle id ever changes. No separate Apple account/key needed beyond the paid Apple Developer Program membership App Store submission already requires; just enable the "Sign In with Apple" capability on the App ID in the developer portal |
| `GCS_BUCKET_NAME` | GCP Console → Cloud Storage | Bucket for profile photos |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCP Console → IAM → Service Accounts → Keys | Path to service account JSON, needs Storage Object Admin on the bucket |
| `FIREBASE_CREDENTIALS_PATH` | Firebase Console → Project Settings → Service Accounts | Path to service account JSON for FCM push |
| `CORS_ORIGINS` | — | Comma-separated allowed origins for the mobile app / web |
| `STUN_URLS` | — | Defaults to Google's public STUN (`stun:stun.l.google.com:19302`), no account needed |
| `TURN_URL` / `TURN_USERNAME` / `TURN_CREDENTIAL` | Twilio Network Traversal Service, coturn, or similar | External prerequisite for reliable video calls across restrictive NATs — STUN-only works without it but calls may fail to connect on some networks. Empty until provisioned. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM_ADDRESS` | Gmail app password, SendGrid, or similar transactional-email provider | Used to send work/school verification codes; `/verification/start` returns 503 until this is configured |
| `STRIPE_SECRET_KEY` | Stripe Dashboard → Developers → API keys | Server-side secret key; enables `/payments/*` |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard → Developers → Webhooks → your endpoint → Signing secret | Verifies `POST /payments/webhook` came from Stripe |
| `WEB_BASE_URL` | — | The deployed marketing site's origin (Vercel URL), used to build Stripe Checkout `success_url`/`cancel_url` |

## mobile/.env (via `EXPO_PUBLIC_*` vars, see `app.config.js`)

| Var | Where to get it | Notes |
|---|---|---|
| `EXPO_PUBLIC_API_BASE_URL` | — | Points at local backend or the deployed Railway URL |
| `EXPO_PUBLIC_MARKETING_SITE_URL` | — | The deployed Vercel URL; used to open the Stripe shop (`Linking.openURL`) and privacy/terms links |
| `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` | same OAuth client as backend's `GOOGLE_OAUTH_CLIENT_ID` | `@react-native-google-signin/google-signin` needs the *web* client id, not an android/iOS one |
| `EXPO_PUBLIC_KAKAO_NATIVE_APP_KEY` | Kakao Developers → App → App Keys | Native app key, plus URL scheme registration in iOS/Android native config |
| `EXPO_PUBLIC_ADMOB_ANDROID_APP_ID` / `EXPO_PUBLIC_ADMOB_IOS_APP_ID` | AdMob console, after app registered | The *app*-level IDs (one per platform); falls back to Google's test IDs until set |
| `EXPO_PUBLIC_ADMOB_ANDROID_BANNER_UNIT_ID` / `EXPO_PUBLIC_ADMOB_IOS_BANNER_UNIT_ID` | AdMob console → Ad units, after creating a Banner unit per platform | Falls back to Google's test banner unit ID until set (`src/components/AdSlot.native.tsx`) |
| `EXPO_PUBLIC_ADMOB_ANDROID_INTERSTITIAL_UNIT_ID` / `EXPO_PUBLIC_ADMOB_IOS_INTERSTITIAL_UNIT_ID` | AdMob console → Ad units, after creating an Interstitial unit per platform | Falls back to Google's test interstitial unit ID until set (`src/services/ads.native.ts`) |
| `FIREBASE_CONFIG` | Firebase Console → Project settings → your app | google-services.json / GoogleService-Info.plist |

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
