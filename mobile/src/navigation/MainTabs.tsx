import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import DiscoverScreen from "../screens/discover/DiscoverScreen";
import MatchListScreen from "../screens/matches/MatchListScreen";
import ChatStack from "./ChatStack";
import ProfileStack from "./ProfileStack";

export type MainTabsParamList = {
  Discover: undefined;
  Matches: undefined;
  Chat: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

export default function MainTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }}>
      <Tab.Screen name="Discover" component={DiscoverScreen} />
      <Tab.Screen name="Matches" component={MatchListScreen} />
      <Tab.Screen name="Chat" component={ChatStack} />
      <Tab.Screen name="Profile" component={ProfileStack} />
    </Tab.Navigator>
  );
}
