import { Platform } from "react-native";
import { AdEventType, RewardedAd, RewardedAdEventType, TestIds } from "react-native-google-mobile-ads";

import { env } from "../config/env";

const realUnitId = Platform.OS === "ios" ? env.admobIosRewardedUnitId : env.admobAndroidRewardedUnitId;
const rewardedUnitId = realUnitId || TestIds.REWARDED;

/** Loads + shows one rewarded ad, resolving true only if the viewer watched
 * it through to EARNED_REWARD (closing early, or a load/show failure, both
 * resolve false) — callers must treat false as "no bonus", never retry
 * automatically. Same "" -> TestIds fallback as AdCard.native.tsx / rewarded
 * unit ids are a separate AdMob inventory from the native ad card's. */
export function showRewardedAd(): Promise<boolean> {
  return new Promise((resolve) => {
    const rewarded = RewardedAd.createForAdRequest(rewardedUnitId);
    let earned = false;
    let settled = false;

    function settle(result: boolean) {
      if (settled) return;
      settled = true;
      unsubEarned();
      unsubLoaded();
      unsubError();
      unsubClosed();
      resolve(result);
    }

    const unsubEarned = rewarded.addAdEventListener(RewardedAdEventType.EARNED_REWARD, () => {
      earned = true;
    });
    const unsubLoaded = rewarded.addAdEventListener(RewardedAdEventType.LOADED, () => rewarded.show());
    const unsubError = rewarded.addAdEventListener(AdEventType.ERROR, () => settle(false));
    const unsubClosed = rewarded.addAdEventListener(AdEventType.CLOSED, () => settle(earned));

    rewarded.load();
  });
}
