import type { QueryClient } from "@tanstack/react-query";

import { env } from "../config/env";
import { useAuthStore } from "../store/authStore";
import { usePurchaseStore } from "../store/purchaseStore";
import type { Profile } from "../types";
import { openExternalUrl } from "./openExternalUrl";

/** Opens the web shop with the session token in the URL, and snapshots the
 * user's current entitlements so a completed purchase can be detected (and
 * confirmed to the user) when the app returns to the foreground — see
 * usePurchaseReturnWatch. Replaces the three near-identical inline
 * openShop() functions that used to live in MyProfileScreen / LikesScreen /
 * FilterModal. */
export function openShop(queryClient: QueryClient): void {
  const token = useAuthStore.getState().accessToken ?? "";
  const profile = queryClient.getQueryData<Profile>(["myProfile"]);
  if (profile) {
    usePurchaseStore.getState().beginWatch({
      superlikeCredits: profile.superlike_credits,
      boostCredits: profile.boost_credits,
      isPremium: profile.is_premium_member,
      aiMatchCredits: profile.ai_match_credits,
      unlimitedMatchingActive: profile.is_unlimited_matching_active,
    });
  }
  openExternalUrl(`${env.marketingSiteUrl}/shop.html?token=${encodeURIComponent(token)}`);
}

/** Same shop page, but scrolled to and highlighting one product — used by a
 * "promo" push notification tap (navigationRef.ts). No queryClient/purchase-
 * watch snapshot here (unlike openShop() above): this fires from outside
 * the component tree, before any screen with a queryClient is necessarily
 * mounted. If the viewer isn't logged in, `token` is just empty and
 * shop.html's own authError message covers it — same as opening the shop
 * any other way while logged out. */
export function openShopForProduct(productId: string): void {
  const token = useAuthStore.getState().accessToken ?? "";
  openExternalUrl(
    `${env.marketingSiteUrl}/shop.html?token=${encodeURIComponent(token)}&highlight=${encodeURIComponent(productId)}`
  );
}
