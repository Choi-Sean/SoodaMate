import { createNativeStackNavigator } from "@react-navigation/native-stack";

import MyProfileScreen from "../screens/profile/MyProfileScreen";
import EditProfileScreen from "../screens/profile/EditProfileScreen";
import PhotoManagerScreen from "../screens/profile/PhotoManagerScreen";
import TravelModeScreen from "../screens/profile/TravelModeScreen";
import VerificationScreen from "../screens/profile/VerificationScreen";
import SettingsScreen from "../screens/settings/SettingsScreen";

export type ProfileStackParamList = {
  MyProfile: undefined;
  EditProfile: undefined;
  PhotoManager: undefined;
  TravelMode: undefined;
  Verification: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<ProfileStackParamList>();

export default function ProfileStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="MyProfile" component={MyProfileScreen} options={{ headerShown: false }} />
      <Stack.Screen name="EditProfile" component={EditProfileScreen} options={{ title: "Edit Profile" }} />
      <Stack.Screen name="PhotoManager" component={PhotoManagerScreen} options={{ title: "Photos" }} />
      <Stack.Screen name="TravelMode" component={TravelModeScreen} options={{ title: "Travel Mode" }} />
      <Stack.Screen name="Verification" component={VerificationScreen} options={{ title: "Verification" }} />
      <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: "Settings" }} />
    </Stack.Navigator>
  );
}
