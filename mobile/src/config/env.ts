// Expo exposes env vars prefixed EXPO_PUBLIC_ to client code at build time.
// None of these have real values yet (no GCP/Google/Kakao accounts exist) —
// see docs/ENV_VARS.md at the repo root for where each one comes from.
export const env = {
  apiBaseUrl: process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8001",
  googleWebClientId: process.env.EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID ?? "",
  kakaoNativeAppKey: process.env.EXPO_PUBLIC_KAKAO_NATIVE_APP_KEY ?? "",
  // Placeholder until web/ (Phase 9) is deployed and has a real URL.
  marketingSiteUrl: process.env.EXPO_PUBLIC_MARKETING_SITE_URL ?? "https://sudadate.example.com",
};
