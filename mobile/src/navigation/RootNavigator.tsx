import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import i18n from "../i18n";
import { useAuthStore } from "../store/authStore";
import { getMyProfile } from "../api/profiles";
import { getMe, updateLanguagePreference } from "../api/account";
import { registerForPushNotifications } from "../services/pushNotifications";
import { usePurchaseReturnWatch } from "../hooks/usePurchaseReturnWatch";
import AnimatedSplash from "../components/AnimatedSplash";
import AuthStack from "./AuthStack";
import MainTabs from "./MainTabs";
import PhoneVerificationScreen from "../screens/auth/PhoneVerificationScreen";
import ProfileSetupScreen from "../screens/auth/ProfileSetupScreen";

// Evaluated once, at module load — essentially "app launch" (App.tsx's own
// i18n-init splash, shown before this component ever mounts, is already
// covered: however long that took is still counted, since elapsed time is
// measured from here, not from this component's own mount). Keeps the
// branded splash on screen for a consistent minimum stretch rather than a
// flash-then-flicker-to-a-spinner when auth/profile resolve fast, while
// never waiting LONGER than the real readiness check needs to.
const APP_LAUNCHED_AT = Date.now();
const MIN_SPLASH_MS = 1500;

export default function RootNavigator() {
  const { hydrated, isAuthenticated, hydrate } = useAuthStore();
  const queryClient = useQueryClient();
  const [minSplashElapsed, setMinSplashElapsed] = useState(() => Date.now() - APP_LAUNCHED_AT >= MIN_SPLASH_MS);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (minSplashElapsed) return;
    const remaining = MIN_SPLASH_MS - (Date.now() - APP_LAUNCHED_AT);
    const timer = setTimeout(() => setMinSplashElapsed(true), Math.max(0, remaining));
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Checked before the profile query below — /account/me works on a bare
  // signed-up account that has no Profile row yet (unlike /profiles/me,
  // which 404s), so phone verification can gate signup *before*
  // ProfileSetupScreen, not just before MainApp.
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: isAuthenticated,
    retry: false,
  });

  const profileQuery = useQuery({
    queryKey: ["myProfile"],
    queryFn: getMyProfile,
    enabled: isAuthenticated && meQuery.data?.phone_verified === true,
    retry: false,
  });

  if (!minSplashElapsed || !hydrated || (isAuthenticated && meQuery.isLoading)) {
    return <AnimatedSplash />;
  }

  if (!isAuthenticated) {
    return <AuthStack />;
  }

  if (meQuery.data?.phone_verified !== true) {
    return (
      <PhoneVerificationScreen onVerified={() => queryClient.invalidateQueries({ queryKey: ["me"] })} />
    );
  }

  if (profileQuery.isLoading) {
    return <AnimatedSplash />;
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

  // ID + selfie verification (FaceVerificationScreen) is required to become
  // "active" (interact with other profiles via Blind Chat), but isn't a
  // hard app-wide gate — the user can still browse/edit their own profile
  // while unverified. See CustomTabBar (blocks entering Blind Chat) and
  // MyProfileScreen (status banner + tab badge) for where this is actually
  // enforced/surfaced.
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
