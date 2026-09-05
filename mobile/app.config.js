// app.config.js instead of app.json so the Kakao native app key (needed for
// the URL scheme the OAuth redirect lands on) can come from an env var
// instead of being hardcoded — no Kakao app exists yet, so this is empty
// until the user creates one (see docs/ENV_VARS.md at the repo root).
const kakaoNativeAppKey = process.env.EXPO_PUBLIC_KAKAO_NATIVE_APP_KEY ?? "";

// Google's official test AdMob app IDs — safe to ship as the default since
// no real AdMob account exists yet; swap via env once one does.
const admobAndroidAppId =
  process.env.EXPO_PUBLIC_ADMOB_ANDROID_APP_ID ?? "ca-app-pub-3940256099942544~3347511713";
const admobIosAppId =
  process.env.EXPO_PUBLIC_ADMOB_IOS_APP_ID ?? "ca-app-pub-3940256099942544~1458002511";

module.exports = {
  expo: {
    name: "SuDa Date",
    slug: "suda-date",
    scheme: "sudadate",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.sudalist.sudadate",
      // Required alongside Google Sign-In per App Store Review Guideline
      // 4.8 — see docs/APP_STORE_SUBMISSION.md. Also enable the "Sign In
      // with Apple" capability on the App ID in the developer portal.
      usesAppleSignIn: true,
    },
    android: {
      package: "com.sudalist.sudadate",
      adaptiveIcon: {
        backgroundColor: "#FCEBDD",
        foregroundImage: "./assets/android-icon-foreground.png",
        backgroundImage: "./assets/android-icon-background.png",
        monochromeImage: "./assets/android-icon-monochrome.png",
      },
      predictiveBackGestureEnabled: false,
    },
    web: {
      favicon: "./assets/favicon.png",
    },
    plugins: [
      "expo-secure-store",
      "expo-localization",
      [
        "expo-splash-screen",
        {
          image: "./assets/splash-icon.png",
          imageWidth: 220,
          resizeMode: "contain",
          backgroundColor: "#FCEBDD",
        },
      ],
      "@react-native-google-signin/google-signin",
      "expo-apple-authentication",
      [
        "@react-native-seoul/kakao-login",
        {
          kakaoAppKey: kakaoNativeAppKey,
        },
      ],
      [
        "react-native-google-mobile-ads",
        {
          androidAppId: admobAndroidAppId,
          iosAppId: admobIosAppId,
        },
      ],
      "@react-native-firebase/app",
      "@react-native-firebase/messaging",
    ],
  },
};
