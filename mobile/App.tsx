import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import RootNavigator from "./src/navigation/RootNavigator";
import { navigationRef } from "./src/navigation/navigationRef";
import AnimatedSplash from "./src/components/AnimatedSplash";
import { initAds } from "./src/services/ads";
import { initDeepLinking } from "./src/services/deepLinking";
import { initI18n } from "./src/i18n";

const queryClient = new QueryClient();

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
        <NavigationContainer ref={navigationRef}>
          <RootNavigator />
          <StatusBar style="auto" />
        </NavigationContainer>
      </SafeAreaProvider>
    </QueryClientProvider>
  );
}
