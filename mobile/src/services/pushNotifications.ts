import { Platform } from "react-native";

import { apiClient } from "../api/client";
import { navigateFromNotification } from "../navigation/navigationRef";

/** @react-native-firebase/messaging has no web implementation and needs a
 * real Firebase project (google-services.json / GoogleService-Info.plist,
 * see docs/ENV_VARS.md) to even initialize — everything here is a no-op
 * until that exists, same defensive pattern as the backend's push_service.py. */

export type PushPermissionStatus = "granted" | "denied" | "not-determined" | "unavailable";

/** Lazily require()s the native module so this file still imports cleanly on
 * web / a Firebase-less build. Returns null in either of those cases. */
function loadMessaging() {
  if (Platform.OS === "web") return null;
  try {
    const messagingModule = require("@react-native-firebase/messaging").default;
    return { messaging: messagingModule(), AuthorizationStatus: messagingModule.AuthorizationStatus };
  } catch {
    return null;
  }
}

/** Read-only: never shows the OS prompt, safe to call on every screen focus
 * (e.g. Settings, to reflect a change the user just made in the OS Settings app). */
export async function getPushPermissionStatus(): Promise<PushPermissionStatus> {
  const loaded = loadMessaging();
  if (!loaded) return "unavailable";
  try {
    const status = await loaded.messaging.hasPermission();
    if (status === loaded.AuthorizationStatus.AUTHORIZED || status === loaded.AuthorizationStatus.PROVISIONAL) {
      return "granted";
    }
    if (status === loaded.AuthorizationStatus.NOT_DETERMINED) return "not-determined";
    return "denied";
  } catch {
    return "unavailable";
  }
}

/** iOS refuses to show its own permission dialog a second time once the user has
 * answered it once (Allow or Don't Allow) — the only way to change it afterwards
 * is the OS Settings app for this app. Works on both platforms. */
export function openNotificationSettings(): void {
  if (Platform.OS === "web") return;
  const { Linking } = require("react-native");
  Linking.openSettings().catch(() => {});
}

/** Requests permission (shows the native OS prompt the first time only) and, if
 * granted, registers the device's FCM token with the backend. Safe to call
 * fire-and-forget or await; never throws. */
export async function registerForPushNotifications(): Promise<PushPermissionStatus> {
  const loaded = loadMessaging();
  if (!loaded) return "unavailable";

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
    const { messaging, AuthorizationStatus } = loaded;
    const authStatus = await messaging.requestPermission();
    const enabled = authStatus === AuthorizationStatus.AUTHORIZED || authStatus === AuthorizationStatus.PROVISIONAL;
    if (!enabled) return "denied";

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
    return "granted";
  } catch {
    // Native module not present, or present but unconfigured (no real
    // Firebase project yet — see docs/ENV_VARS.md FIREBASE_CONFIG).
    return "unavailable";
  }
}
