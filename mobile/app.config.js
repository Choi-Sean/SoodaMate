const fs = require("fs");
const path = require("path");
const { withPodfile } = require("@expo/config-plugins");

// @react-native-firebase/* is autolinked (present in package.json) even
// when its Expo config plugin is excluded below for lacking a real
// google-services.json/GoogleService-Info.plist — autolinking scans
// node_modules directly and doesn't consult the plugins array. On iOS,
// react-native-firebase resolves Firebase via Swift Package Manager by
// default, which conflicts with Expo/RN's static CocoaPods linkage
// ("SPM + static linkage is not supported... duplicate-symbol errors" —
// a real `eas build` failure, not a guess). $RNFirebaseDisableSPM is
// react-native-firebase's own documented opt-out, falling back to plain
// CocoaPods resolution instead; must be set before any Podfile target
// block, hence prepending it via a raw Podfile mod.
function withRNFirebaseDisableSPM(config) {
  return withPodfile(config, (config) => {
    if (!config.modResults.contents.includes("$RNFirebaseDisableSPM")) {
      config.modResults.contents = `$RNFirebaseDisableSPM = true\n${config.modResults.contents}`;
    }
    return config;
  });
}

// app.config.js instead of app.json so dynamic values like the AdMob app
// IDs below can come from an env var instead of being hardcoded.

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

const locationUsageDescription =
  "We use your location to show your distance to other users and find matches near you.";

// One shared string per permission across every plugin that touches it
// (expo-image-picker and the WebRTC plugin below both write
// NSCameraUsageDescription/NSMicrophoneUsageDescription) — Expo's config
// plugins overwrite, not merge, so a mismatched pair between two plugins
// would leave whichever ran last as the only real, possibly-inaccurate copy.
const cameraUsageDescription =
  "Allow SooDaMate to access your camera to take photos and make video calls.";
const microphoneUsageDescription = "Allow SooDaMate to access your microphone for video calls.";

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

// Silently building without the plist is how builds 10-12 shipped with no push at all
// (the app just no-ops). On the EAS iOS production builder, fail loudly instead.
if (process.env.EAS_BUILD_PROFILE === "production" && process.env.EAS_BUILD_PLATFORM === "ios" && !hasIosFirebase) {
  throw new Error("GoogleService-Info.plist is missing from the project archive - refusing to build iOS without push.");
}

module.exports = {
  expo: {
    name: "SooDaMate",
    // Stuck as "suda-mate" — this is the EAS project's server-side slug
    // (tied to extra.eas.projectId below), and eas build hard-errors on any
    // mismatch between this field and that. Renaming it would mean deleting
    // and recreating the whole EAS project, losing the Android/iOS build
    // credentials already set up. Purely internal — never shown to users,
    // only appears in the expo.dev dashboard URL.
    slug: "suda-mate",
    scheme: "soodamate",
    // Translated iOS permission prompts (ATT / location / photos / camera) — the
    // English defaults live in the plugin config below; each file only overrides
    // them for that language. Needs a native build (they end up in Info.plist).
    locales: {
      ko: "./locales/ko.json",
      es: "./locales/es.json",
      "zh-Hans": "./locales/zh-Hans.json",
      ja: "./locales/ja.json",
    },
    version: "1.0.0",
    orientation: "portrait",
    icon: "./assets/icon.png",
    userInterfaceStyle: "light",
    ios: {
      supportsTablet: true,
      bundleIdentifier: "com.soodalist.soodamate",
      // Required alongside Google Sign-In per App Store Review Guideline
      // 4.8 — see docs/APP_STORE_SUBMISSION.md. Also enable the "Sign In
      // with Apple" capability on the App ID in the developer portal.
      usesAppleSignIn: true,
      // Remote push (Firebase Cloud Messaging over APNs). @react-native-firebase/messaging's
      // config plugin does nothing on iOS, so without this entitlement (and the background
      // mode below) getToken() never yields a token and the app can't be woken by a push.
      // "development" only for dev-client builds; every store/ad-hoc build talks to the
      // production APNs environment. EAS syncs the Push Notifications capability on the App ID.
      entitlements: {
        "aps-environment": process.env.EAS_BUILD_PROFILE === "development" ? "development" : "production",
      },
      infoPlist: {
        // Lets the translated permission prompts in ./locales/*.json (see
        // `locales` below) be used instead of always showing English.
        CFBundleAllowMixedLocalizations: true,
        // The app only uses standard HTTPS/TLS (no custom/proprietary
        // encryption) — declaring this avoids App Store Connect's export
        // compliance question blocking every single build submission.
        ITSAppUsesNonExemptEncryption: false,
        // Lets a push wake the app in the background (silent/data delivery, token refresh).
        UIBackgroundModes: ["remote-notification"],
      },
      ...(hasIosFirebase ? { googleServicesFile: googleServiceInfoPlistPath } : {}),
    },
    android: {
      // Matches ios.bundleIdentifier below. The Play Console app record
      // that previously forced a different value here (com.soodamate.myapp)
      // was deleted and recreated fresh, so nothing external constrains
      // this anymore — unify with iOS instead of keeping them different.
      package: "com.soodalist.soodamate",
      adaptiveIcon: {
        backgroundColor: "#FCEBDD",
        foregroundImage: "./assets/android-icon-foreground.png",
        backgroundImage: "./assets/android-icon-background.png",
        monochromeImage: "./assets/android-icon-monochrome.png",
      },
      predictiveBackGestureEnabled: false,
      // VIBRATE isn't a "dangerous" permission (no runtime prompt) but also isn't
      // auto-added by any installed package — needed for the incoming-call ring
      // (services/CallContext.tsx uses React Native core's Vibration API directly,
      // not a plugin that would merge this into the manifest on its own).
      permissions: ["VIBRATE"],
      ...(hasAndroidFirebase ? { googleServicesFile: googleServicesJsonPath } : {}),
    },
    web: {
      favicon: "./assets/favicon.png",
    },
    plugins: [
      "expo-secure-store",
      "expo-localization",
      "expo-video",
      "expo-font",
      [
        "expo-splash-screen",
        {
          image: "./assets/splash-icon.png",
          imageWidth: 320,
          resizeMode: "contain",
          backgroundColor: "#FFF6EC",
        },
      ],
      "@react-native-google-signin/google-signin",
      "expo-apple-authentication",
      [
        "react-native-google-mobile-ads",
        {
          androidAppId: admobAndroidAppId,
          iosAppId: admobIosAppId,
          userTrackingUsageDescription,
          // Best practice per Google's own docs: don't start collecting
          // measurement data before the user has answered the ATT prompt.
          delayAppMeasurementInit: true,
          // SKAdNetwork ids of every ad buyer that bids through Google (iOS 14+
          // install attribution). Advertisers whose id is missing can't attribute
          // installs to this app, so they bid less — Google's docs say to list all of
          // them. Copied from https://developers.google.com/admob/ios/quick-start
          // ("Update your Info.plist"); re-sync when Google updates the list.
          skAdNetworkItems: require("./skadnetwork-ids.json"),
        },
      ],
      [
        "expo-tracking-transparency",
        { userTrackingPermission: userTrackingUsageDescription },
      ],
      [
        "expo-location",
        {
          locationAlwaysAndWhenInUsePermission: locationUsageDescription,
          locationWhenInUsePermission: locationUsageDescription,
        },
      ],
      [
        "expo-image-picker",
        {
          photosPermission: "Allow SooDaMate to access your photos so you can add them to your profile.",
          cameraPermission: cameraUsageDescription,
          // Was `false` (opted out) before video calls existed — image
          // picking itself still never touches the mic.
          microphonePermission: microphoneUsageDescription,
        },
      ],
      [
        "@config-plugins/react-native-webrtc",
        { cameraPermission: cameraUsageDescription, microphonePermission: microphoneUsageDescription },
      ],
      ...(hasAndroidFirebase || hasIosFirebase
        ? ["@react-native-firebase/app", "@react-native-firebase/messaging"]
        : []),
      // Unconditional (unlike the plugins above) — autolinking still pulls
      // in the Firebase native pods on iOS regardless of whether the
      // config plugin ran, so the Podfile fix is needed either way.
      withRNFirebaseDisableSPM,
      // @sentry/react-native's own config plugin ("@sentry/react-native" in
      // this array) is deliberately NOT added yet — it edits the Xcode
      // build phases / Gradle to upload source maps via sentry-cli, and
      // that's unverified against a real Sentry project/auth token in this
      // repo (none exists yet — EXPO_PUBLIC_SENTRY_DSN is blank). Runtime
      // crash/error capture already works without it (see
      // src/services/errorReporting.ts); add the plugin once a real Sentry
      // project exists and there's a build to spend confirming it doesn't
      // break, for readable (symbolicated) native stack traces.
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
