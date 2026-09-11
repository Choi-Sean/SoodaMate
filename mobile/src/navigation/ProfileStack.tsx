import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import MyProfileScreen from "../screens/profile/MyProfileScreen";
import EditProfileScreen from "../screens/profile/EditProfileScreen";
import TravelModeScreen from "../screens/profile/TravelModeScreen";
import VerificationScreen from "../screens/profile/VerificationScreen";
import FaceVerificationScreen from "../screens/profile/FaceVerificationScreen";
import CoupleStoriesFeedScreen from "../screens/profile/CoupleStoriesFeedScreen";
import MyCoupleStoriesScreen from "../screens/profile/MyCoupleStoriesScreen";
import SettingsScreen from "../screens/settings/SettingsScreen";
import DiscoverScreen from "../screens/discover/DiscoverScreen";
import SwipeScreen from "../screens/swipe/SwipeScreen";
import { colors } from "../theme";

export type ProfileStackParamList = {
  MyProfile: undefined;
  EditProfile: undefined;
  TravelMode: undefined;
  Verification: undefined;
  FaceVerification: undefined;
  CoupleStoriesFeed: undefined;
  MyCoupleStories: undefined;
  Settings: undefined;
  // Discover/classic swipe matching are no longer bottom tabs (Blind Chat is
  // the app's primary flow now — see MainTabs) but the underlying
  // like/pass/superlike/boost system isn't gone, just demoted to a secondary
  // link from MyProfileScreen, so existing monetization (superlike/boost/
  // who-liked-me) keeps working.
  ClassicDiscover: undefined;
  ClassicSwipe: undefined;
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
      <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: t("settings.title") }} />
      <Stack.Screen name="ClassicDiscover" component={DiscoverScreen} options={{ title: t("tabs.discover") }} />
      <Stack.Screen name="ClassicSwipe" component={SwipeScreen} options={{ title: t("tabs.matches") }} />
    </Stack.Navigator>
  );
}
