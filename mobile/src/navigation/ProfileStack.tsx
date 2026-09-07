import { createNativeStackNavigator } from "@react-navigation/native-stack";

import MyProfileScreen from "../screens/profile/MyProfileScreen";
import EditProfileScreen from "../screens/profile/EditProfileScreen";
import TravelModeScreen from "../screens/profile/TravelModeScreen";
import VerificationScreen from "../screens/profile/VerificationScreen";
import FaceVerificationScreen from "../screens/profile/FaceVerificationScreen";
import SettingsScreen from "../screens/settings/SettingsScreen";

export type ProfileStackParamList = {
  MyProfile: undefined;
  EditProfile: undefined;
  TravelMode: undefined;
  Verification: undefined;
  FaceVerification: undefined;
  Settings: undefined;
};

const Stack = createNativeStackNavigator<ProfileStackParamList>();

// Photo management lives inline in EditProfile now (ProfilePhotosGrid) —
// there is no more standalone "PhotoManager" screen/route.
export default function ProfileStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="MyProfile" component={MyProfileScreen} options={{ headerShown: false }} />
      <Stack.Screen name="EditProfile" component={EditProfileScreen} options={{ title: "Edit Profile" }} />
      <Stack.Screen name="TravelMode" component={TravelModeScreen} options={{ title: "Travel Mode" }} />
      <Stack.Screen name="Verification" component={VerificationScreen} options={{ title: "Verification" }} />
      <Stack.Screen name="FaceVerification" component={FaceVerificationScreen} options={{ title: "Face Verification" }} />
      <Stack.Screen name="Settings" component={SettingsScreen} options={{ title: "Settings" }} />
    </Stack.Navigator>
  );
}
