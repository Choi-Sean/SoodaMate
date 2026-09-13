import { createNativeStackNavigator } from "@react-navigation/native-stack";

import PhoneAuthScreen from "../screens/auth/PhoneAuthScreen";

export type AuthStackParamList = {
  PhoneAuth: undefined;
};

const Stack = createNativeStackNavigator<AuthStackParamList>();

export default function AuthStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="PhoneAuth" component={PhoneAuthScreen} />
    </Stack.Navigator>
  );
}
