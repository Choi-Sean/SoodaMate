import { Platform } from "react-native";

import { env } from "../config/env";

let configured = false;

function ensureConfigured() {
  if (configured) return;
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { GoogleSignin } = require("@react-native-google-signin/google-signin");
  GoogleSignin.configure({ webClientId: env.googleWebClientId });
  configured = true;
}

/** Returns a Google id_token the backend can verify, or null if the user
 * cancelled the flow. Native-only — GoogleSignin has no web implementation,
 * so this throws on web (web verification of this app only needs to bundle,
 * not actually run Google sign-in). */
export async function signInWithGoogle(): Promise<string | null> {
  if (Platform.OS === "web") {
    throw new Error("Google Sign-In is not available on web; test on a native build");
  }

  ensureConfigured();
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { GoogleSignin } = require("@react-native-google-signin/google-signin");

  await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
  const response = await GoogleSignin.signIn();

  if (response.type === "cancelled") return null;
  const idToken = response.data?.idToken;
  if (!idToken) throw new Error("Google sign-in did not return an id_token");
  return idToken;
}
