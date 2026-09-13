import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import ProfileStack from "./ProfileStack";
import ChatStack from "./ChatStack";
import CustomTabBar from "./CustomTabBar";

export type MainTabsParamList = {
  Chat: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

// Exactly 2 flanking tabs on purpose: CustomTabBar's elevated center button
// sits dead-center of the bar, so an odd tab count (e.g. 3) puts one real
// tab directly underneath it — overlapping icon, label, and touch target.
// Discover, classic Matching, and Likes are demoted to secondary links from
// the Profile tab (ProfileStack's ClassicDiscover/ClassicSwipe/Likes) rather
// than bottom tabs; none of that underlying functionality is gone.
export default function MainTabs() {
  return (
    <Tab.Navigator
      initialRouteName="Profile"
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <CustomTabBar {...props} />}
    >
      <Tab.Screen name="Chat" component={ChatStack} />
      <Tab.Screen name="Profile" component={ProfileStack} />
    </Tab.Navigator>
  );
}
