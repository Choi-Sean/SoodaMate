import { Alert, Platform } from "react-native";

import { publish, type AlertButtonSpec } from "../services/alertStore";

/** Drop-in for RN's Alert.alert with the exact same signature - but
 * react-native-web's Alert.alert is a hard no-op (`static alert() {}`,
 * verified in node_modules/react-native-web/.../Alert), so every
 * confirm/delete-account/report/block dialog in the app silently did
 * nothing on web. Routes to the real native Alert on iOS/Android; on web,
 * publishes to alertStore so the single <AlertHost/> mounted in App.tsx can
 * render an actual modal. */
export function showAlert(title: string, message?: string, buttons?: AlertButtonSpec[]): void {
  if (Platform.OS !== "web") {
    Alert.alert(title, message, buttons);
    return;
  }
  publish({ title, message, buttons: buttons && buttons.length > 0 ? buttons : [{ text: "OK" }] });
}
