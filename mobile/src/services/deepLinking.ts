import { Linking } from "react-native";
import type { QueryClient } from "@tanstack/react-query";

import { navigationRef } from "../navigation/navigationRef";

function pathFromUrl(url: string): string {
  // "sudadate://shop" -> "shop"; also tolerates a trailing query string.
  const withoutScheme = url.replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//, "");
  return withoutScheme.split("?")[0].replace(/^\/+|\/+$/g, "");
}

export function handleDeepLinkUrl(url: string | null, queryClient: QueryClient): void {
  if (!url) return;
  const path = pathFromUrl(url);
  if (path === "shop") {
    // Stripe grants credits via a webhook that can lag a beat behind the
    // redirect back into the app, so refetch rather than trust cached data.
    queryClient.invalidateQueries({ queryKey: ["myProfile"] });
    if (navigationRef.isReady()) {
      (navigationRef.navigate as (...args: unknown[]) => void)("Profile", { screen: "MyProfile" });
    }
  }
}

export function initDeepLinking(queryClient: QueryClient): () => void {
  Linking.getInitialURL().then((url) => handleDeepLinkUrl(url, queryClient));
  const subscription = Linking.addEventListener("url", ({ url }) => handleDeepLinkUrl(url, queryClient));
  return () => subscription.remove();
}
