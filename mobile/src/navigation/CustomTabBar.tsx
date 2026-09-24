import { Image, Pressable, Text, View, StyleSheet } from "react-native";
import type { BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../api/profiles";
import { isAccountActive } from "../utils/profileCompleteness";
import { colors } from "../theme";

const REAL_TAB_ICONS: Record<string, string> = {
  Chat: "💬",
  Profile: "👤",
};
const REAL_TAB_LABEL_KEYS: Record<string, string> = {
  Chat: "tabs.chat",
  Profile: "tabs.profile",
};

/** Button-click Swipe matching is the app's primary flow again (Blind Chat
 * is demoted to a secondary entry point — see ChatListScreen's banner), so
 * it gets an Instagram/Tinder-style elevated center button instead of being
 * just another tab. Tapping it navigates straight into ProfileStack's
 * ClassicSwipe screen. MainTabs keeps exactly 2 flanking tabs (Chat, Profile)
 * so this button's center position never lands on top of a real tab's icon/
 * label/touch target. */
export default function CustomTabBar({ state, navigation }: BottomTabBarProps) {
  const { t } = useTranslation();
  const insets = useSafeAreaInsets();
  // Cached alongside every other screen's ["myProfile"] query — this never
  // triggers its own network request in the common case.
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const needsActivation = profile != null && !isAccountActive(profile);

  function handleCenterPress() {
    navigation.navigate("Profile", { screen: "ClassicSwipe" } as never);
  }

  return (
    <View style={[styles.wrap, { paddingBottom: Math.max(insets.bottom, 10) }]}>
      <View style={styles.bar}>
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          return (
            <Pressable
              key={route.key}
              style={styles.tabButton}
              onPress={() => {
                const event = navigation.emit({ type: "tabPress", target: route.key, canPreventDefault: true });
                if (event.defaultPrevented) return;
                // Chat always lands on the conversation LIST — otherwise the tab
                // resumes wherever its stack was left (e.g. the room a blind match
                // just opened) and the list is unreachable. Tapping the tab you're
                // already on also pops it back to its first screen.
                //
                // preventDefault() here is load-bearing, not decorative: without it,
                // React Navigation's own built-in tabPress handling ALSO runs (this
                // listener doesn't stop it just by not calling navigate again), and
                // it puts the Chat tab back wherever its stack's internal state
                // already pointed — the room you were just in — racing the explicit
                // navigate() below and undoing it a beat later (the reported "list
                // flashes, then jumps back to the chat" bug).
                if (route.name === "Chat") {
                  event.preventDefault();
                  navigation.navigate("Chat", { screen: "ChatList" } as never);
                } else if (focused) {
                  event.preventDefault();
                  navigation.navigate(route.name, { screen: "MyProfile" } as never);
                } else {
                  navigation.navigate(route.name);
                }
              }}
            >
              <View style={[styles.iconBubble, focused && styles.iconBubbleActive]}>
                <Text style={{ fontSize: 18 }}>{REAL_TAB_ICONS[route.name]}</Text>
                {route.name === "Profile" && needsActivation && <View style={styles.badgeDot} />}
              </View>
              <Text style={[styles.label, focused && styles.labelActive]} numberOfLines={1}>
                {t(REAL_TAB_LABEL_KEYS[route.name])}
              </Text>
            </Pressable>
          );
        })}
      </View>

      <Pressable style={styles.centerButton} onPress={handleCenterPress}>
        <Image source={require("../../assets/logo-mascot.png")} style={styles.centerButtonIcon} resizeMode="contain" />
      </Pressable>
      <Text style={styles.centerLabel} numberOfLines={1}>
        {t("tabs.matches")}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: colors.white,
    borderTopWidth: 0,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
  bar: { flexDirection: "row", height: 68, paddingTop: 10 },
  tabButton: { flex: 1, alignItems: "center", justifyContent: "center", gap: 5 },
  iconBubble: { width: 34, height: 26, borderRadius: 13, alignItems: "center", justifyContent: "center", position: "relative" },
  badgeDot: {
    position: "absolute",
    top: -1,
    right: 3,
    width: 9,
    height: 9,
    borderRadius: 5,
    backgroundColor: colors.danger,
    borderWidth: 1.5,
    borderColor: colors.white,
  },
  iconBubbleActive: { backgroundColor: colors.creamDeep },
  label: { fontSize: 11, fontWeight: "700", color: colors.muted },
  labelActive: { color: colors.accentDark },
  centerButton: {
    position: "absolute",
    alignSelf: "center",
    top: -26,
    width: 60,
    height: 60,
    borderRadius: 30,
    // White (not colors.accent) so the mascot's own orange face reads
    // clearly against it — an orange character on an orange fill blended
    // into an indistinct blob at this size.
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 4,
    borderColor: colors.white,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.25,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 10,
  },
  centerButtonIcon: { width: 44, height: 44 },
  centerLabel: {
    position: "absolute",
    top: 36,
    alignSelf: "center",
    fontSize: 10.5,
    fontWeight: "800",
    color: colors.accentDark,
  },
});
