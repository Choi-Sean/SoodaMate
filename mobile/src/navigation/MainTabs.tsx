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
// The center button opens ClassicSwipe (button-click Like/Pass/SuperLike
// matching, the app's primary flow) via the Profile tab's own stack
// (ProfileStack's ClassicSwipe/ClassicDiscover/Likes) rather than a 3rd
// bottom tab. Blind Chat is a secondary entry point now — see
// ChatListScreen's banner.
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
