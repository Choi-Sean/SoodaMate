// Expo exposes env vars prefixed EXPO_PUBLIC_ to client code at build time.
// None of these have real values yet (no GCP/Google/Kakao accounts exist) —
// see docs/ENV_VARS.md at the repo root for where each one comes from.
export const env = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8001",
  googleWebClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? "",
  kakaoNativeAppKey: process.env.EXPO_PUBLIC_KAKAO_NATIVE_APP_KEY ?? "",
  // Placeholder until web/ (Phase 9) is deployed and has a real URL.
  marketingSiteUrl: process.env.EXPO_PUBLIC_MARKETING_SITE_URL ?? "https://sudamate.example.com",
  // Ad unit IDs (distinct from the AdMob *app* IDs in app.config.js) are
  // per-platform per-ad-format in AdMob's console. Empty until a real AdMob
  // account exists; ads.native.ts/AdSlot.native.tsx fall back to Google's
  // TestIds when these are unset, so the app is fully functional either way.
  admobAndroidBannerUnitId: process.env.EXPO_PUBLIC_ADMOB_ANDROID_BANNER_UNIT_ID ?? "",
  admobIosBannerUnitId: process.env.EXPO_PUBLIC_ADMOB_IOS_BANNER_UNIT_ID ?? "",
  admobAndroidInterstitialUnitId: process.env.EXPO_PUBLIC_ADMOB_ANDROID_INTERSTITIAL_UNIT_ID ?? "",
  admobIosInterstitialUnitId: process.env.EXPO_PUBLIC_ADMOB_IOS_INTERSTITIAL_UNIT_ID ?? "",
};
