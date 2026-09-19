// react-native-google-mobile-ads has no web build at all (same reason
// AdCard.web.tsx is a static placeholder) — resolving false tells the
// caller "no ad available" so it can show the same message as a real
// load failure on native, rather than a platform-specific dead end.
export function showRewardedAd(): Promise<boolean> {
  return Promise.resolve(false);
}
