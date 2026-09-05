import { useEffect } from "react";
import { ActivityIndicator, View } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuthStore } from "../store/authStore";
import { getMyProfile } from "../api/profiles";
import { registerForPushNotifications } from "../services/pushNotifications";
import { maybeShowInterstitial } from "../services/ads";
import { colors } from "../theme";
import AuthStack from "./AuthStack";
import MainTabs from "./MainTabs";
import ProfileSetupScreen from "../screens/auth/ProfileSetupScreen";

export default function RootNavigator() {
  const { hydrated, isAuthenticated, hydrate } = useAuthStore();
  const queryClient = useQueryClient();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const profileQuery = useQuery({
    queryKey: ["myProfile"],
    queryFn: getMyProfile,
    enabled: isAuthenticated,
    retry: false,
  });

  if (!hydrated || (isAuthenticated && profileQuery.isLoading)) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  if (!isAuthenticated) {
    return <AuthStack />;
  }

  // 404 means no profile row yet; anything else with is_profile_complete
  // false also routes back to setup (e.g. profile exists but has no photo).
  const needsProfileSetup = profileQuery.isError || profileQuery.data?.is_profile_complete === false;

  if (needsProfileSetup) {
    return (
      <ProfileSetupScreen onComplete={() => queryClient.invalidateQueries({ queryKey: ["myProfile"] })} />
    );
  }

  return <MainApp />;
}

function MainApp() {
  useEffect(() => {
    registerForPushNotifications();
    maybeShowInterstitial();
  }, []);

  return <MainTabs />;
}
