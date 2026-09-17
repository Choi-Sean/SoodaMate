import { createNavigationContainerRef } from "@react-navigation/native";

import { openShopForProduct } from "../utils/openShop";

// Lets code outside the component tree (push notification tap handlers)
// navigate — set as the `ref` on <NavigationContainer> in App.tsx.
export const navigationRef = createNavigationContainerRef();

export function navigateFromNotification(data: Record<string, string>) {
  // "promo" (admin-activated Promotion, see push_service.send_promo_
  // broadcast_notification) doesn't need navigationRef.isReady() at all —
  // it opens the web shop via Linking, same as the in-app "상점" button,
  // not an in-app screen. Checked first so a tap that arrives before
  // NavigationContainer mounts (cold start) still works.
  if (data.type === "promo" && data.product_id) {
    openShopForProduct(data.product_id);
    return;
  }

  if (!navigationRef.isReady()) return;

  if (data.type === "message" && data.match_id) {
    (navigationRef.navigate as (...args: unknown[]) => void)("Chat", {
      screen: "ChatRoom",
      params: {
        matchId: data.match_id,
        otherUserId: data.sender_id ?? "",
        otherDisplayName: data.sender_name ?? "",
      },
    });
  } else if (data.type === "match") {
    (navigationRef.navigate as (...args: unknown[]) => void)("Matches");
  }
}
