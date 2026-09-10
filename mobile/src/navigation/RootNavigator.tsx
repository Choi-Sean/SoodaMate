import { useEffect } from "react";
import { ActivityIndicator, View } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import i18n from "../i18n";
import { useAuthStore } from "../store/authStore";
import { getMyProfile } from "../api/profiles";
import { updateLanguagePreference } from "../api/account";
import { registerForPushNotifications } from "../services/pushNotifications";
import { usePurchaseReturnWatch } from "../hooks/usePurchaseReturnWatch";
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

  // No page is reachable until the profile is genuinely complete: a real
  // profile row (404 = none yet), the server's own is_profile_complete
  // flag, AND — belt-and-suspenders in case that flag is ever stale — at
  // least one photo plus the core identity fields present. Anything short
  // of that routes to ProfileSetupScreen and nothing else.
  const p = profileQuery.data;
  const needsProfileSetup =
    profileQuery.isError ||
    !p ||
    p.is_profile_complete === false ||
    !p.display_name ||
    !p.birth_date ||
    !p.gender ||
    (p.photos?.length ?? 0) === 0;

  if (needsProfileSetup) {
    return (
      <ProfileSetupScreen onComplete={() => queryClient.invalidateQueries({ queryKey: ["myProfile"] })} />
    );
  }

  return <MainApp />;
}

function MainApp() {
  usePurchaseReturnWatch();

  useEffect(() => {
    registerForPushNotifications();
    // Covers a language change made while logged out, or on a device that
    // never got a chance to sync (e.g. this feature shipped after the user
    // had already picked a language) — setLanguage() itself also syncs on
    // every change going forward, this is just the catch-up path.
    updateLanguagePreference(i18n.language).catch(() => {});
  }, []);

  return <MainTabs />;
}
