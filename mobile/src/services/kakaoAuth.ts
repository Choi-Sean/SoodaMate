import { Platform } from "react-native";

/** Returns a Kakao access_token the backend can verify against
 * kapi.kakao.com. Native-only, same reasoning as googleAuth.ts. */
export async function signInWithKakao(): Promise<string> {
  if (Platform.OS === "web") {
    throw new Error("Kakao Login is not available on web; test on a native build");
  }

  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { login } = require("@react-native-seoul/kakao-login");
  const token = await login();
  return token.accessToken;
}
