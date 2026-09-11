import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import ChatListScreen from "../screens/chat/ChatListScreen";
import ChatRoomScreen from "../screens/chat/ChatRoomScreen";
import BlindChatQueueScreen from "../screens/chat/BlindChatQueueScreen";
import SubmitCoupleStoryScreen from "../screens/profile/SubmitCoupleStoryScreen";
import { colors } from "../theme";

export type ChatStackParamList = {
  ChatList: undefined;
  ChatRoom: { matchId: string; otherUserId: string; otherDisplayName: string };
  SubmitCoupleStory: { matchId: string; otherDisplayName: string };
  BlindChatQueue: { initialCategories?: string[] } | undefined;
};

const Stack = createNativeStackNavigator<ChatStackParamList>();

export default function ChatStack() {
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
      <Stack.Screen name="ChatList" component={ChatListScreen} options={{ title: "Chats", headerShown: false }} />
      <Stack.Screen
        name="ChatRoom"
        component={ChatRoomScreen}
        options={({ route }) => ({ title: route.params.otherDisplayName })}
      />
      <Stack.Screen
        name="SubmitCoupleStory"
        component={SubmitCoupleStoryScreen}
        options={{ title: t("coupleStory.writeTitle") }}
      />
      <Stack.Screen
        name="BlindChatQueue"
        component={BlindChatQueueScreen}
        options={{ title: t("blindChat.title") }}
      />
    </Stack.Navigator>
  );
}
