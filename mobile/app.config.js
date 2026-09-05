const fs = require("fs");
const path = require("path");

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

// Apple requires this exact prompt (App Tracking Transparency) before any
// SDK that touches IDFA — AdMob does — can request personalized ads on iOS.
// Requested at runtime via expo-tracking-transparency (see ads.native.ts)
// before mobileAds().initialize(); omitting this is an App Review rejection,
// not just a degraded-ads issue.
const userTrackingUsageDescription =
  "We use this to show you more relevant ads and support the free features of the app.";

// The @react-native-firebase/* config plugins hard-fail prebuild (not just
// a runtime no-op, unlike this app's other "no real account yet" defaults)
// if expo.android.googleServicesFile / expo.ios.googleServicesFile aren't
// set to a real file — this broke `eas build` outright before a Firebase
// project existed. Only wire Firebase in once the real config files are
// actually present, matching every other external-account default in this
// file; drop these two JSON/plist files in mobile/ once a Firebase project
// exists and the plugins + googleServicesFile activate automatically.
const googleServicesJsonPath = path.join(__dirname, "google-services.json");
const googleServiceInfoPlistPath = path.join(__dirname, "GoogleService-Info.plist");
const hasAndroidFirebase = fs.existsSync(googleServicesJsonPath);
const hasIosFirebase = fs.existsSync(googleServiceInfoPlistPath);

module.exports = {
  expo: {
    name: "SuDa Mate",
    slug: "suda-mate",
    scheme: "sudamate",
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.sudalist.sudamate",
      // Required alongside Google Sign-In per App Store Review Guideline
      // 4.8 — see docs/APP_STORE_SUBMISSION.md. Also enable the "Sign In
      // with Apple" capability on the App ID in the developer portal.
      usesAppleSignIn: true,
      infoPlist: {
        // The app only uses standard HTTPS/TLS (no custom/proprietary
        // encryption) — declaring this avoids App Store Connect's export
        // compliance question blocking every single build submission.
        ITSAppUsesNonExemptEncryption: false,
      },
      ...(hasIosFirebase ? { googleServicesFile: googleServiceInfoPlistPath } : {}),
    },
    android: {
      package: "com.sudalist.sudamate",
      adaptiveIcon: {
        backgroundColor: "#FCEBDD",
        foregroundImage: "./assets/android-icon-foreground.png",
        backgroundImage: "./assets/android-icon-background.png",
        monochromeImage: "./assets/android-icon-monochrome.png",
      },
      predictiveBackGestureEnabled: false,
      ...(hasAndroidFirebase ? { googleServicesFile: googleServicesJsonPath } : {}),
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
          userTrackingUsageDescription,
          // Best practice per Google's own docs: don't start collecting
          // measurement data before the user has answered the ATT prompt.
          delayAppMeasurementInit: true,
          // Google's own AdMob SKAdNetwork identifier (iOS 14+ ad
          // attribution) — the full recommended list (50+ entries, mostly
          // other mediation networks this app doesn't use) is at
          // https://developers.google.com/admob/ios/ios14#skadnetwork;
          // add more here only if real mediation partners are added later.
          skAdNetworkItems: ["cstr6suwn9.skadnetwork"],
        },
      ],
      [
        "expo-tracking-transparency",
        { userTrackingPermission: userTrackingUsageDescription },
      ],
      [
        "expo-image-picker",
        {
          photosPermission: "Allow SuDa Mate to access your photos so you can add them to your profile.",
          cameraPermission: "Allow SuDa Mate to access your camera so you can take a profile photo.",
          microphonePermission: false,
        },
      ],
      ...(hasAndroidFirebase || hasIosFirebase
        ? ["@react-native-firebase/app", "@react-native-firebase/messaging"]
        : []),
    ],
    // EAS Update isn't actually wired up (no OTA update flow built) — this
    // just satisfies `eas build`'s own check, since eas.json's build
    // profiles already declare a "channel", which EAS expects update
    // config to exist alongside. runtimeVersion "appVersion" means an OTA
    // update (if one is ever pushed) only targets clients on the exact
    // same app.config.js `version`, never crossing a native-rebuild
    // boundary.
    updates: {
      url: "https://u.expo.dev/24ed66e3-d709-4bde-aa7e-417d576ca56d",
    },
    runtimeVersion: {
      policy: "appVersion",
    },
    extra: {
      eas: {
        // Created via `eas init --force` — https://expo.dev/accounts/seanchoi1991/projects/suda-mate
        projectId: "24ed66e3-d709-4bde-aa7e-417d576ca56d",
      },
    },
  },
};
