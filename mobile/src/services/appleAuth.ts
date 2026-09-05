import { Platform } from "react-native";

/** Returns an Apple identityToken the backend can verify locally against
 * Apple's public JWKS, or null if the user cancelled. iOS-only — Android has
 * no Apple Sign-In capability, and Apple's own App Store Review Guideline
 * 4.8 (the reason this exists alongside Google Sign-In) only applies there. */
export async function signInWithApple(): Promise<string | null> {
  if (Platform.OS !== "ios") {
    throw new Error("Sign in with Apple is only available on iOS");
  }

  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const AppleAuthentication = require("expo-apple-authentication");

  try {
    const credential = await AppleAuthentication.signInAsync({
      requestedScopes: [
        AppleAuthentication.AppleAuthenticationScope.FULL_NAME,
        AppleAuthentication.AppleAuthenticationScope.EMAIL,
      ],
    });
    if (!credential.identityToken) throw new Error("Apple sign-in did not return an identityToken");
    return credential.identityToken;
  } catch (e: any) {
    if (e?.code === "ERR_REQUEST_CANCELED") return null;
    throw e;
  }
}
