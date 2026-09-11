import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import ProfileStack from "./ProfileStack";
import LikesScreen from "../screens/likes/LikesScreen";
import ChatStack from "./ChatStack";
import CustomTabBar from "./CustomTabBar";

export type MainTabsParamList = {
  Chat: undefined;
  Likes: undefined;
  Profile: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParamList>();

// Discover and the classic Like/Pass/SuperLike deck ("Matches" tab) are no
// longer bottom tabs — Blind Chat is the app's primary flow now (see
// CustomTabBar's elevated center button). That underlying deck isn't gone,
// just demoted to a secondary link from the Profile tab (ProfileStack's
// ClassicDiscover/ClassicSwipe), so superlike/boost/who-liked-me keep working.
export default function MainTabs() {
  return (
    <Tab.Navigator screenOptions={{ headerShown: false }} tabBar={(props) => <CustomTabBar {...props} />}>
      <Tab.Screen name="Chat" component={ChatStack} />
      <Tab.Screen name="Likes" component={LikesScreen} />
      <Tab.Screen name="Profile" component={ProfileStack} />
    </Tab.Navigator>
  );
}
