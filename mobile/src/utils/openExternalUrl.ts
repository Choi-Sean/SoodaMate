import { Linking, Platform } from "react-native";

/** Opens an external URL (marketing site shop/privacy/terms pages) in a
 * new tab/the system browser. On native this is just Linking.openURL. On
 * web, Linking.openURL calls window.open(url, "_blank") under the hood
 * (see react-native-web's own Linking implementation) — plenty of
 * browsers and ad/popup-blocker extensions silently swallow a scripted
 * window.open() even when it's triggered synchronously from a real click,
 * and openURL never checks whether it actually returned a window, so the
 * button just looks like it does nothing. A real `<a target="_blank">`
 * click is exempt from that blocking (a browser can't tell it apart from
 * the user directly clicking a link), so on web this builds one, clicks
 * it, and removes it instead of going through Linking at all. */
export function openExternalUrl(url: string): void {
  if (Platform.OS === "web") {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    return;
  }
  Linking.openURL(url);
}
