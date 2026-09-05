import mobileAds, { AdEventType, InterstitialAd, TestIds } from "react-native-google-mobile-ads";

// This file only ever gets bundled for ios/android (Metro's platform
// extension resolution) — react-native-google-mobile-ads has no web build
// at all, so ads.web.ts is a plain no-op instead of a Platform.OS branch
// inside a shared file (that still pulled the native-only module into the
// web bundle and broke it, since Metro resolves imports statically).
let initialized = false;
let lastInterstitialAt = 0;
const INTERSTITIAL_MIN_INTERVAL_MS = 1000 * 60 * 5; // at most once per 5 minutes

export async function initAds(): Promise<void> {
  if (initialized) return;
  await mobileAds().initialize();
  initialized = true;
}

/** Shows an interstitial at most once per INTERSTITIAL_MIN_INTERVAL_MS —
 * called on cold app open; not on every swipe, to keep it from feeling
 * punishing. */
export async function maybeShowInterstitial(): Promise<void> {
  const now = Date.now();
  if (now - lastInterstitialAt < INTERSTITIAL_MIN_INTERVAL_MS) return;

  const interstitial = InterstitialAd.createForAdRequest(TestIds.INTERSTITIAL);

  await new Promise<void>((resolve) => {
    const unsubscribeLoaded = interstitial.addAdEventListener(AdEventType.LOADED, () => {
      lastInterstitialAt = Date.now();
      interstitial.show();
    });
    const unsubscribeClosed = interstitial.addAdEventListener(AdEventType.CLOSED, () => {
      unsubscribeLoaded();
      unsubscribeClosed();
      resolve();
    });
    const unsubscribeError = interstitial.addAdEventListener(AdEventType.ERROR, () => {
      unsubscribeLoaded();
      unsubscribeClosed();
      unsubscribeError();
      resolve();
    });
    interstitial.load();
  });
}
