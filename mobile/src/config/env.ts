// Expo exposes env vars prefixed EXPO_PUBLIC_ to client code at build time.
// None of these have real values yet (no GCP/Google/Kakao accounts exist) —
// see docs/ENV_VARS.md at the repo root for where each one comes from.
export const env = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8001",
  googleWebClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? "",
  kakaoNativeAppKey: process.env.EXPO_PUBLIC_KAKAO_NATIVE_APP_KEY ?? "",
  // Placeholder until web/ (Phase 9) is deployed and has a real URL.
  marketingSiteUrl: process.env.EXPO_PUBLIC_MARKETING_SITE_URL ?? "https://soodamate.example.com",
  // Ad unit ID (distinct from the AdMob *app* ID in app.config.js) is
  // per-platform in AdMob's console. Empty until a real AdMob account
  // exists; AdCard.native.tsx falls back to Google's TestIds when unset,
  // so the app is fully functional either way. No banner or interstitial
  // unit id — the in-swipe-deck native ad card is the only ad surface
  // (matches Tinder/Bumble/Hinge; no always-full-screen ads).
  admobAndroidNativeUnitId: process.env.EXPO_PUBLIC_ADMOB_ANDROID_NATIVE_UNIT_ID ?? "",
  admobIosNativeUnitId: process.env.EXPO_PUBLIC_ADMOB_IOS_NATIVE_UNIT_ID ?? "",
};
