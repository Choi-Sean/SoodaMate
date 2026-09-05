import { useEffect, useState } from "react";
import { ActivityIndicator, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer } from "@react-navigation/native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import RootNavigator from "./src/navigation/RootNavigator";
import { navigationRef } from "./src/navigation/navigationRef";
import { initAds } from "./src/services/ads";
import { initDeepLinking } from "./src/services/deepLinking";
import { initI18n } from "./src/i18n";

const queryClient = new QueryClient();

export default function App() {
  const [i18nReady, setI18nReady] = useState(false);

  useEffect(() => {
    initAds();
    initI18n().then(() => setI18nReady(true));
    return initDeepLinking(queryClient);
  }, []);

  if (!i18nReady) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: "#FFF6EC" }}>
        <ActivityIndicator size="large" color="#E2914D" />
      </View>
    );
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
