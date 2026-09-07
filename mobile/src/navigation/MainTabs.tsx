import { StyleSheet, Text, View } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useTranslation } from "react-i18next";

import ProfileStack from "./ProfileStack";
import DiscoverScreen from "../screens/discover/DiscoverScreen";
import SwipeScreen from "../screens/swipe/SwipeScreen";
import LikesScreen from "../screens/likes/LikesScreen";
import ChatStack from "./ChatStack";
import { colors } from "../theme";

export type MainTabsParamList = {
  Profile: undefined;
  Discover: undefined;
  Swipe: undefined;
  Likes: undefined;
  Chat: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

// No icon library is bundled beyond @expo/vector-icons' emoji-adjacent glyph
// set isn't used here on purpose — a plain emoji glyph reads clean at
// tab-bar size and matches the mascot's warm, approachable style.
const TAB_ICONS: Record<keyof MainTabsParamList, string> = {
  Profile: "👤",
  Discover: "🧭",
  Swipe: "🔥",
  Likes: "❤️",
  Chat: "💬",
};

export default function MainTabs() {
  const { t } = useTranslation();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.accentDark,
        tabBarInactiveTintColor: colors.muted,
        tabBarStyle: styles.tabBar,
        tabBarLabelStyle: styles.tabLabel,
        // A soft cream bubble behind the active icon (instead of relying on
        // a subtle text-color shift alone) is the same "cute" affordance as
        // the icon bubbles on the profile facts card — and reads clearly at
        // a glance, where active-vs-inactive text color alone was too close
        // in tone (both warm brown/orange) to tell apart.
        tabBarIcon: ({ focused, color }: { focused: boolean; color: string }) => (
          <View style={[styles.iconBubble, focused && styles.iconBubbleActive]}>
            <Text style={{ fontSize: 18, color }}>{TAB_ICONS[route.name as keyof MainTabsParamList]}</Text>
          </View>
        ),
      })}
    >
      <Tab.Screen name="Profile" component={ProfileStack} options={{ tabBarLabel: t("tabs.profile") }} />
      <Tab.Screen name="Discover" component={DiscoverScreen} options={{ tabBarLabel: t("tabs.discover") }} />
      <Tab.Screen name="Swipe" component={SwipeScreen} options={{ tabBarLabel: t("tabs.swipe") }} />
      <Tab.Screen name="Likes" component={LikesScreen} options={{ tabBarLabel: t("tabs.likes") }} />
      <Tab.Screen name="Chat" component={ChatStack} options={{ tabBarLabel: t("tabs.chat") }} />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.white,
    borderTopWidth: 0,
    height: 62,
    paddingTop: 6,
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.08,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: -2 },
    elevation: 8,
  },
  tabLabel: { fontSize: 11, fontWeight: "700" },
  iconBubble: {
    width: 34,
    height: 26,
    borderRadius: 13,
    alignItems: "center",
    justifyContent: "center",
  },
  iconBubbleActive: { backgroundColor: colors.creamDeep },
});
