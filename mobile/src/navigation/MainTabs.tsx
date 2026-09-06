import { Text } from "react-native";
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
        tabBarStyle: { backgroundColor: colors.white, borderTopColor: colors.border },
        tabBarIcon: ({ color }: { color: string }) => (
          <Text style={{ fontSize: 20, color }}>{TAB_ICONS[route.name as keyof MainTabsParamList]}</Text>
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
