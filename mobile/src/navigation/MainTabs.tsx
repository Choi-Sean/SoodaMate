import { Text } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { useTranslation } from "react-i18next";

import DiscoverScreen from "../screens/discover/DiscoverScreen";
import MatchListScreen from "../screens/matches/MatchListScreen";
import ChatStack from "./ChatStack";
import ProfileStack from "./ProfileStack";
import { colors } from "../theme";

export type MainTabsParamList = {
  Discover: undefined;
  Matches: undefined;
  Chat: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

// No icon library is bundled (no new native dependency added for a
// bottom-tab polish pass) — a plain emoji glyph reads clean at tab-bar size
// and matches the mascot's warm, approachable style.
const TAB_ICONS: Record<keyof MainTabsParamList, string> = {
  Discover: "🔍",
  Matches: "💛",
  Chat: "💬",
  Profile: "👤",
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
      <Tab.Screen name="Discover" component={DiscoverScreen} options={{ tabBarLabel: t("tabs.discover") }} />
      <Tab.Screen name="Matches" component={MatchListScreen} options={{ tabBarLabel: t("tabs.matches") }} />
      <Tab.Screen name="Chat" component={ChatStack} options={{ tabBarLabel: t("tabs.chat") }} />
      <Tab.Screen name="Profile" component={ProfileStack} options={{ tabBarLabel: t("tabs.profile") }} />
    </Tab.Navigator>
  );
}
