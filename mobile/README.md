# mobile — SooDa Mate

React Native app built with Expo (dev client, not Expo Go — Google/Kakao
login and AdMob need native modules Expo Go doesn't include).

## Local setup

```bash
npm install
cp .env.example .env
```

Point `EXPO_PUBLIC_API_BASE_URL` in `.env` at your running backend
(`../backend`, defaults to `http://localhost:8001`).

```bash
npx expo start
```

- `a` / `i` in the Expo CLI to open on a connected Android/iOS device or
  simulator — requires Android Studio / Xcode installed locally, neither of
  which is available in this dev environment, so on-device verification
  happens on your own machine.
- `w` to run in a browser via react-native-web — useful for a quick sanity
  check of screens/navigation, but Google Sign-In and Kakao Login throw on
  web (native-only, see `src/services/googleAuth.ts` /
  `src/services/kakaoAuth.ts`).
- `npx tsc --noEmit` type-checks the whole app without running anything.

## Native auth setup (one-time, per platform)

Neither Google nor Kakao accounts exist yet — until they do, the Google/Kakao
buttons on the login screen will fail; email/password auth works
immediately once the backend is running.

- **Google**: create an OAuth client in Google Cloud Console (type: Web
  application) and set its client ID as both `GOOGLE_OAUTH_CLIENT_ID` in
  `backend/.env` and `EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID` here — same value,
  both places, because the backend verifies the id_token's audience against
  it. Android additionally needs your debug/release SHA-1 fingerprint
  registered in the same Google Cloud project.
- **Kakao**: create an app in Kakao Developers, set `EXPO_PUBLIC_KAKAO_NATIVE_APP_KEY`
  here (the config plugin in `app.config.js` wires it into the native
  `AndroidManifest.xml` / `Info.plist` URL scheme automatically on prebuild)
  and `KAKAO_REST_API_KEY` in `backend/.env`.

## Structure

- `src/navigation/` — `RootNavigator` gates Auth → ProfileSetup → MainTabs based on `useAuthStore` + a `myProfile` query
- `src/screens/` — one folder per feature area; includes Travel Mode and Verification (Profile stack) alongside the core Discover/Matches/Chat/Profile/Settings screens
- `src/api/` — thin axios wrappers per backend resource, `client.ts` handles the JWT header + refresh-on-401
- `src/store/authStore.ts` — Zustand; tokens persisted via `expo-secure-store` on native, `localStorage` on web (`src/services/secureStorage.ts`)
- `src/services/` — native SDK wrappers (Google/Kakao sign-in); guarded to throw cleanly on web instead of crashing the bundle
- `src/services/deepLinking.ts` — handles `soodamate://shop`, the redirect back from the website's Stripe checkout (see `web/shop-success.html`)
- `src/theme.ts` — shared color tokens (warm cream/orange/navy, matches the SooDaList family look, not a generic pink dating-app palette)
- `src/i18n/` — i18next setup + `locales/{ko,en,es,zh,ja}.json`; `SettingsScreen` has the language switcher

## Not yet built

Video call UI (WebRTC) — the backend signaling (Phase 15) is done and tested, but the mobile side needs `react-native-webrtc`, a new native build, and promoting the chat WebSocket from its current per-screen scope to an app-level provider so incoming calls can be received outside the chat room. None of that can be verified in a sandbox without a device/emulator — see `docs/ARCHITECTURE.md`.
