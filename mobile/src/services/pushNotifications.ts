import { Platform } from "react-native";

import { apiClient } from "../api/client";
import { navigateFromNotification } from "../navigation/navigationRef";

/** @react-native-firebase/messaging has no web implementation and needs a
 * real Firebase project (google-services.json / GoogleService-Info.plist,
 * see docs/ENV_VARS.md) to even initialize — everything here is a no-op
 * until that exists, same defensive pattern as the backend's push_service.py. */
export async function registerForPushNotifications(): Promise<void> {
  if (Platform.OS === "web") return;

  // A real prod crash (Sentry, 2026-09-18): require() succeeding was never
  // the only failure mode — autolinking pulls the native module in even
  // without a real Firebase project (see app.config.js's own comment on
  // this), so require() doesn't throw, but calling into an unconfigured
  // Firebase App does, as a plain TypeError from deeper inside the module.
  // That threw past this try/catch (it only wrapped the require line) as
  // an unhandled rejection, since this fn is called fire-and-forget from
  // RootNavigator with no .catch(). Wrapping the whole body is the actual
  // no-op-until-configured guarantee this function's own docstring above
  // already promises.
  try {
    const messagingModule = require("@react-native-firebase/messaging").default;
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
  } catch {
    // Native module not present, or present but unconfigured (no real
    // Firebase project yet — see docs/ENV_VARS.md FIREBASE_CONFIG).
  }
}
