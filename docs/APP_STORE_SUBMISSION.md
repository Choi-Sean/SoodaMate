# App Store Submission Guide

Uses **EAS Build/Submit** (Expo's cloud build service) since the app is Expo-managed with a dev client — this avoids needing a local Xcode/Android Studio install to produce signed builds. Everything here is written to be run from `mobile/`.

## 0. Manual prerequisites (the user does these — account creation + payment)

Claude cannot create accounts or make payments on your behalf; these are one-time real-world steps:

1. **Apple Developer Program** — $99/year, enroll at [developer.apple.com](https://developer.apple.com/programs/enroll/). Needed for any iOS distribution beyond a personal simulator build.
2. **Google Play Console** — $25 one-time, register at [play.google.com/console](https://play.google.com/console/). Needed for any Android distribution beyond a local debug APK.
3. **Expo/EAS account** — free, sign up at [expo.dev](https://expo.dev/), then locally:
   ```bash
   cd mobile
   npm install -g eas-cli
   eas login
   eas build:configure
   ```
   (`eas.json` already exists in this repo with `development`/`preview`/`production` build profiles — `eas build:configure` just links the project to your Expo account.)

Everything below assumes steps 1–3 are done and `mobile/.env` / `eas.json`'s env blocks point `EXPO_PUBLIC_API_BASE_URL` at your deployed Railway backend (see `docs/DEPLOYMENT_RAILWAY.md`), not `localhost`.

## 1. iOS

### 1.0 App ID capabilities (Apple Developer portal → Identifiers → your App ID)

Enable these two capabilities when creating (or editing) the `com.sudalist.sudamate` App ID:

- **Push Notifications** — required for FCM/APNs delivery of match and message alerts.
- **Sign In with Apple** — required by App Store Review Guideline 4.8: since this app offers Google Sign-In, Apple requires an equivalent "Sign in with Apple" option too, or the build risks rejection at review. The backend (`app/services/oauth/apple.py`) and mobile (`expo-apple-authentication`, iOS-only per Apple's own scope for this requirement) already implement this — enabling the capability here just grants the entitlement EAS Build needs to sign it in.

No other capability (In-App Purchase, Sign In with Apple's "server-to-server notifications", etc.) is needed — this app deliberately has no native IAP (payments are Stripe web checkout, see `docs/ARCHITECTURE.md`).

### 1.1 Build

```bash
eas build --platform ios --profile production
```

First run prompts to log into your Apple Developer account and either let EAS manage signing certificates/provisioning profiles automatically (recommended) or supply your own. This produces a signed `.ipa`.

### 1.2 Create the App Store Connect app record

In [App Store Connect](https://appstoreconnect.apple.com/) → My Apps → **+** → New App:

- Bundle ID: `com.sudalist.sudamate` (must match `mobile/app.config.js`'s `ios.bundleIdentifier`)
- Name: 수다메이트 (or the localized name you want on the store)
- Primary category: Lifestyle or Social Networking
- Age rating: complete Apple's questionnaire — this app has user-generated content and is 18+ only, mark accordingly

### 1.3 Store listing metadata

- **Privacy Policy URL**: your deployed `web/privacy-policy.html` URL (Apple requires this before submission)
- **Screenshots**: required sizes are 6.7" (iPhone 15 Pro Max class) and 6.5" — capture from a real device/simulator once the Discover/Chat/Profile screens are live; `web/index.html`'s `#screens` section still has placeholder phone frames to swap for the same real screenshots
- **App description, keywords, support URL**: support URL can point at the marketing site

### 1.4 TestFlight (internal testing first)

```bash
eas submit --platform ios --latest
```

Uploads the build to App Store Connect. In App Store Connect → TestFlight, add internal testers (up to 100, no review needed) to verify the real build before requesting App Review for public release.

### 1.5 Submit for review

Once internal testing looks good, submit the build for App Review from App Store Connect. Typical review time is 1–3 days; expect at least one rejection round on a dating app (Apple scrutinizes safety/moderation features — the block/report flow and 18+ gating in this app address the common rejection reasons).

## 2. Android

### 2.1 Build

```bash
eas build --platform android --profile production
```

Produces a signed `.aab` (Android App Bundle); EAS manages the upload keystore unless you provide your own.

### 2.2 Create the Play Console app

In [Play Console](https://play.google.com/console/) → Create app:

- Package name: `com.sudalist.sudamate` (must match `mobile/app.config.js`'s `android.package`)
- App category: Dating
- Complete the **Data safety** section — this app collects email, profile data, location, photos, messages, and device tokens; declare each honestly (see `web/privacy-policy.html` for the authoritative list) since this is a common source of Play Store rejections if it doesn't match actual behavior
- Complete the **Content rating** questionnaire (dating apps are typically rated for mature audiences)
- **Privacy Policy URL**: same deployed `web/privacy-policy.html` URL as iOS

### 2.3 Internal testing track

```bash
eas submit --platform android --latest
```

Uploads to Play Console. Assign the build to the **Internal testing** track first, add tester emails, and verify before promoting to Closed/Open testing or Production.

### 2.4 Production release

Promote the tested build to Production once ready. Google's review for a new developer account/app is typically faster than Apple's but still budget a few days.

## 3. After first submission

- Update `web/index.html`'s store badge links (currently `#download` placeholders) to the real App Store / Google Play listing URLs once both are live.
- Keep `eas.json`'s `production` profile's `EXPO_PUBLIC_API_BASE_URL` pointed at the production Railway URL, not a dev/staging one.
- Future releases: bump the version, `eas build` + `eas submit` again — no need to redo the store listing setup.
