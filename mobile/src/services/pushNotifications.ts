import { Platform } from "react-native";

import { apiClient } from "../api/client";
import { navigateFromNotification } from "../navigation/navigationRef";

/** @react-native-firebase/messaging has no web implementation and needs a
 * real Firebase project (google-services.json / GoogleService-Info.plist,
 * see docs/ENV_VARS.md) to even initialize — everything here is a no-op
 * until that exists, same defensive pattern as the backend's push_service.py. */
export async function registerForPushNotifications(): Promise<void> {
  if (Platform.OS === "web") return;

  let messagingModule;
  try {
    messagingModule = require("@react-native-firebase/messaging").default;
  } catch {
    return; // native module not present (no Firebase config yet)
  }

  const messaging = messagingModule();

  const authStatus = await messaging.requestPermission();
  const enabled =
    authStatus === messagingModule.AuthorizationStatus.AUTHORIZED ||
    authStatus === messagingModule.AuthorizationStatus.PROVISIONAL;
  if (!enabled) return;

  const fcmToken = await messaging.getToken();
  await apiClient.post("/devices/register", {
    fcm_token: fcmToken,
    platform: Platform.OS === "ios" ? "ios" : "android",
  });

  messaging.onMessage(async (remoteMessage: any) => {
    // Foreground messages don't show a system notification automatically;
    // a real app would surface an in-app banner here. Left as a no-op hook
    // for now — the important behavior (tap-to-open) is background/quit.
    void remoteMessage;
  });

  messaging.onNotificationOpenedApp((remoteMessage: any) => {
    navigateFromNotification(remoteMessage?.data ?? {});
  });

  const initialNotification = await messaging.getInitialNotification();
  if (initialNotification?.data) {
    navigateFromNotification(initialNotification.data);
  }
}
