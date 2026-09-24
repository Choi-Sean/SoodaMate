import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import MyProfileScreen from "../screens/profile/MyProfileScreen";
import EditProfileScreen from "../screens/profile/EditProfileScreen";
import TravelModeScreen from "../screens/profile/TravelModeScreen";
import VerificationScreen from "../screens/profile/VerificationScreen";
import FaceVerificationScreen from "../screens/profile/FaceVerificationScreen";
import CoupleStoriesFeedScreen from "../screens/profile/CoupleStoriesFeedScreen";
import MyCoupleStoriesScreen from "../screens/profile/MyCoupleStoriesScreen";
import PurchaseHistoryScreen from "../screens/profile/PurchaseHistoryScreen";
import SettingsScreen from "../screens/settings/SettingsScreen";
import DiscoverScreen from "../screens/discover/DiscoverScreen";
import SwipeScreen from "../screens/swipe/SwipeScreen";
import LikesScreen from "../screens/likes/LikesScreen";
import { colors } from "../theme";

export type ProfileStackParamList = {
  MyProfile: undefined;
  EditProfile: undefined;
  TravelMode: undefined;
  Verification: undefined;
  FaceVerification: undefined;
  CoupleStoriesFeed: undefined;
  MyCoupleStories: undefined;
  PurchaseHistory: undefined;
  Settings: undefined;
  // ClassicSwipe (button-click Like/Pass/SuperLike) is the app's primary
  // flow again, reached via MainTabs/CustomTabBar's elevated center button
  // rather than as a 3rd bottom tab (which would sit dead-center under that
  // button and collide with it). ClassicDiscover (grid browse) and Likes
  // (who-liked-me) are one tap away from ClassicSwipe's own header icons.
  // Blind Chat is the demoted one now — see ChatListScreen's banner.
  ClassicDiscover: undefined;
  ClassicSwipe: undefined;
  Likes: undefined;
};

const Stack = createNativeStackNavigator<ProfileStackParamList>();

// Photo management lives inline in EditProfile now (ProfilePhotosGrid) —
// there is no more standalone "PhotoManager" screen/route.
export default function ProfileStack() {
  const { t } = useTranslation();

  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: colors.white },
        headerShadowVisible: false,
        headerTintColor: colors.accentDark,
        headerTitleStyle: { color: colors.navy, fontWeight: "800" },
      }}
    >
      <Stack.Screen name="MyProfile" component={MyProfileScreen} options={{ headerShown: false }} />
      <Stack.Screen name="EditProfile" component={EditProfileScreen} options={{ title: t("profile.editProfile") }} />
      <Stack.Screen name="TravelMode" component={TravelModeScreen} options={{ title: t("settings.travelMode") }} />
      <Stack.Screen name="Verification" component={VerificationScreen} options={{ title: t("settings.verification") }} />
      <Stack.Screen name="FaceVerification" component={FaceVerificationScreen} options={{ title: t("faceVerification.title") }} />
      <Stack.Screen name="CoupleStoriesFeed" component={CoupleStoriesFeedScreen} options={{ title: t("coupleStory.feedTitle") }} />
      <Stack.Screen name="MyCoupleStories" component={MyCoupleStoriesScreen} options={{ title: t("coupleStory.myStoriesTitle") }} />
      <Stack.Screen
        name="PurchaseHistory"
        component={PurchaseHistoryScreen}
        options={{ title: t("purchaseHistory.title") }}
      />
      <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: t("settings.title") }} />
      {/* Discover/Likes render their own big ScreenHeader title in-body (see
          components/ScreenHeader.tsx) — the native header here is kept only
          for its back chevron (empty title so it doesn't duplicate that). */}
      <Stack.Screen name="ClassicDiscover" component={DiscoverScreen} options={{ title: "", headerBackTitle: "" }} />
      <Stack.Screen name="ClassicSwipe" component={SwipeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="Likes" component={LikesScreen} options={{ title: "", headerBackTitle: "" }} />
    </Stack.Navigator>
  );
}
