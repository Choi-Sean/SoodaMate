import { createNativeStackNavigator } from "@react-navigation/native-stack";

import ChatListScreen from "../screens/chat/ChatListScreen";
import ChatRoomScreen from "../screens/chat/ChatRoomScreen";

export type ChatStackParamList = {
  ChatList: undefined;
  ChatRoom: { matchId: string; otherUserId: string; otherDisplayName: string };
};

const Stack = createNativeStackNavigator<ChatStackParamList>();

export default function ChatStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="ChatList" component={ChatListScreen} options={{ title: "Chats", headerShown: false }} />
      <Stack.Screen
        name="ChatRoom"
        component={ChatRoomScreen}
        options={({ route }) => ({ title: route.params.otherDisplayName })}
      />
    </Stack.Navigator>
  );
}
