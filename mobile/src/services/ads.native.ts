import { Platform } from "react-native";
import { getTrackingPermissionsAsync, requestTrackingPermissionsAsync, PermissionStatus } from "expo-tracking-transparency";
import mobileAds from "react-native-google-mobile-ads";

// This file only ever gets bundled for ios/android (Metro's platform
// extension resolution) — react-native-google-mobile-ads has no web build
// at all, so ads.web.ts is a plain no-op instead of a Platform.OS branch
// inside a shared file (that still pulled the native-only module into the
// web bundle and broke it, since Metro resolves imports statically).
//
// No interstitial here on purpose — always-full-screen ads were a
// deliberate product decision to drop. The only ad surface left is the
// in-swipe-deck sponsored card (see components/AdCard.native.tsx),
// matching how Tinder/Bumble/Hinge do it.
let initialized = false;

export async function initAds(): Promise<void> {
  if (initialized) return;

  // App Tracking Transparency: required on iOS before requesting the IDFA
  // for personalized ads (Apple rejects apps that skip this). No-op on
  // Android. delayAppMeasurementInit in app.config.js keeps AdMob's own
  // measurement SDK idle until this resolves.
  if (Platform.OS === "ios") {
    const current = await getTrackingPermissionsAsync();
    if (current.status === PermissionStatus.UNDETERMINED) {
      await requestTrackingPermissionsAsync();
    }
  }

  await mobileAds().initialize();
  initialized = true;
}
