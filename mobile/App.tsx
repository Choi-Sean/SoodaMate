import { useEffect, useState } from "react";
import { StatusBar } from "expo-status-bar";
import * as SplashScreen from "expo-splash-screen";
import { NavigationContainer } from "@react-navigation/native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import RootNavigator from "./src/navigation/RootNavigator";
import { navigationRef } from "./src/navigation/navigationRef";
import AnimatedSplash from "./src/components/AnimatedSplash";
import { initAds } from "./src/services/ads";
import { initDeepLinking } from "./src/services/deepLinking";
import { initI18n } from "./src/i18n";

// Keeps the native (static) splash on screen until we explicitly hide it
// below, right as AnimatedSplash mounts — otherwise Expo hides the native
// splash the instant the first JS frame commits, which would flash blank
// before our own splash view ever appears.
SplashScreen.preventAutoHideAsync().catch(() => {});

const queryClient = new QueryClient();

export default function App() {
  const [i18nReady, setI18nReady] = useState(false);

  useEffect(() => {
    initAds();
    initI18n().then(() => setI18nReady(true));
    return initDeepLinking(queryClient);
  }, []);

  if (!i18nReady) {
    return <AnimatedSplash onReady={() => SplashScreen.hideAsync().catch(() => {})} />;
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
