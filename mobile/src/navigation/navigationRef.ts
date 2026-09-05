import { createNavigationContainerRef } from "@react-navigation/native";

// Lets code outside the component tree (push notification tap handlers)
// navigate — set as the `ref` on <NavigationContainer> in App.tsx.
export const navigationRef = createNavigationContainerRef();

export function navigateFromNotification(data: Record<string, string>) {
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
