import { useEffect, useState } from "react";
import { AppState, type AppStateStatus, Platform } from "react-native";
import { StatusBar } from "expo-status-bar";
import { DefaultTheme, NavigationContainer, type Theme } from "@react-navigation/native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { focusManager, QueryClient, QueryClientProvider } from "@tanstack/react-query";

import RootNavigator from "./src/navigation/RootNavigator";
import { navigationRef } from "./src/navigation/navigationRef";
import AnimatedSplash from "./src/components/AnimatedSplash";
import AlertHost from "./src/components/AlertHost";
import { initAds } from "./src/services/ads";
import { initDeepLinking } from "./src/services/deepLinking";
import { initI18n } from "./src/i18n";
import { colors } from "./src/theme";

const queryClient = new QueryClient();

// react-query's refetch-on-focus is a browser-`window` concept; on native
// it does nothing unless focusManager is fed the app's foreground state.
// Wiring it here means every screen's data (profile, credits, matches, ...)
// refreshes the moment the user returns to the app — notably right after a
// trip out to the web shop to make a purchase.
if (Platform.OS !== "web") {
  AppState.addEventListener("change", (status: AppStateStatus) => {
    focusManager.setFocused(status === "active");
  });
}

// React Navigation's own DefaultTheme colors (a cool gray #f2f2f2 background,
// iOS-blue primary/tint) have nothing to do with the brand palette — any
// screen that forgot to set its own backgroundColor was quietly falling back
// to that gray instead of the app's warm cream, and every screen using a
// native-stack default header (Edit Profile, Settings, Chat room, ...) got a
// mismatched blue back-button/tint. Setting it here once means every screen
// and every header is on-brand by default, with no per-screen override needed.
const navTheme: Theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.accentDark,
    background: colors.cream,
    card: colors.white,
    text: colors.ink,
    border: colors.border,
    notification: colors.heart,
  },
};

export default function App() {
  const [i18nReady, setI18nReady] = useState(false);

  useEffect(() => {
    initAds();
    // .catch() so a broken i18n init (bad locale data, storage error, etc.)
    // can never leave the app stuck on the loading screen forever — worst
    // case is untranslated keys, not a permanently blocked splash.
    initI18n()
      .then(() => setI18nReady(true))
      .catch(() => setI18nReady(true));
    return initDeepLinking(queryClient);
  }, []);

  // Expo's own default splash-screen auto-hide (proven across every build
  // so far) already handles the native splash; this is purely the in-JS
  // loading placeholder shown after that, replacing a plain spinner with
  // the bouncing mascot. Deliberately NOT wired to
  // SplashScreen.preventAutoHideAsync()/hideAsync() — that native-lifecycle
  // handoff can't be exercised in this sandbox (no emulator/device), so it
  // isn't worth the risk of a real device getting stuck waiting on a hide
  // call that never fires.
  if (!i18nReady) {
    return <AnimatedSplash />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaProvider>
        <NavigationContainer ref={navigationRef} theme={navTheme}>
          <RootNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
        <AlertHost />
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
