import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
  StyleSheet,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import ChatBubble from "../../components/ChatBubble";
import { getMessageHistory } from "../../api/messages";
import { blockUser, reportUser } from "../../api/safety";
import { useChatSocket, type ChatSocketError } from "../../hooks/useChatSocket";
import { useMatches } from "../../hooks/useMatches";
import { useAuthStore } from "../../store/authStore";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import type { ChatMessage } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "ChatRoom">;

export default function ChatRoomScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { matchId, otherUserId, otherDisplayName } = route.params;
  const userId = useAuthStore((s) => s.userId);
  const { data: history } = useQuery({
    queryKey: ["messages", matchId],
    queryFn: () => getMessageHistory(matchId),
  });

  // Phase 14: Bumble first-message restriction state comes from /matches
  // (already recomputed server-side on every fetch, including lazy expiry) —
  // no separate single-match endpoint exists, and react-query caches this
  // list cheaply since ChatListScreen already fetches it too.
  const { data: matches } = useMatches();
  const match = useMemo(() => matches?.find((m) => m.id === matchId), [matches, matchId]);
  const mustWaitForPeer = match?.is_message_restricted && !match?.can_send_first_message;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");

  useEffect(() => {
    if (history) setMessages(history);
  }, [history]);

  const handleIncoming = useCallback((msg: ChatMessage) => {
    setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
  }, []);

  const handleSocketError = useCallback(
    (err: ChatSocketError) => {
      if (err.code === "first_message_restricted") {
        // Roll back the optimistic local echo of whatever we just tried to send.
        setMessages((prev) => prev.filter((m) => !m.id.startsWith("local-")));
        Alert.alert(t("common.somethingWentWrong"), t("chat.firstMessageRestricted"));
      }
    },
    [t]
  );

  const { sendMessage, markRead } = useChatSocket(matchId, handleIncoming, handleSocketError);

  useEffect(() => {
    markRead();
  }, [markRead]);

  async function submitReport(reason: string) {
    try {
      await reportUser(otherUserId, reason);
      Alert.alert(t("chat.reported"), t("chat.reportedBody"));
    } catch {
      Alert.alert(t("common.somethingWentWrong"), t("chat.errorGeneric"));
    }
  }

  function openReportReasons() {
    Alert.alert(t("chat.reportReasonTitle"), undefined, [
      { text: t("chat.reasonHarassment"), onPress: () => submitReport("harassment") },
      { text: t("chat.reasonInappropriate"), onPress: () => submitReport("inappropriate_content") },
      { text: t("chat.reasonFakeProfile"), onPress: () => submitReport("fake_profile") },
      { text: t("chat.cancel"), style: "cancel" },
    ]);
  }

  async function doBlock() {
    try {
      await blockUser(otherUserId);
      navigation.goBack();
    } catch {
      Alert.alert(t("common.somethingWentWrong"), t("chat.errorGeneric"));
    }
  }

  function confirmBlock() {
    Alert.alert(t("chat.blockConfirmTitle"), t("chat.blockConfirmBody"), [
      { text: t("chat.cancel"), style: "cancel" },
      { text: t("chat.blockConfirm"), style: "destructive", onPress: doBlock },
    ]);
  }

  function openMenu() {
    Alert.alert(otherDisplayName, undefined, [
      { text: t("chat.report"), onPress: openReportReasons },
      { text: t("chat.block"), style: "destructive", onPress: confirmBlock },
      { text: t("chat.cancel"), style: "cancel" },
    ]);
  }

  useLayoutEffect(() => {
    navigation.setOptions({
      headerRight: () => (
        <Pressable onPress={openMenu} hitSlop={12} style={styles.menuButton}>
          <Text style={styles.menuButtonText}>⋯</Text>
        </Pressable>
      ),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigation, otherUserId, otherDisplayName]);

  function handleSend() {
    const content = input.trim();
    if (!content || mustWaitForPeer) return;

    sendMessage(content);
    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        match_id: matchId,
        sender_id: userId ?? "",
        content,
        sent_at: new Date().toISOString(),
        delivered_at: null,
        read_at: null,
      },
    ]);
    setInput("");
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <FlatList
        data={messages}
        keyExtractor={(m) => m.id}
        renderItem={({ item }) => <ChatBubble content={item.content} isMine={item.sender_id === userId} />}
        contentContainerStyle={styles.list}
      />
      {mustWaitForPeer && (
        <View style={styles.restrictedBanner}>
          <Text style={styles.restrictedBannerText}>{t("chat.restrictedBanner")}</Text>
        </View>
      )}
      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder={t("chat.messagePlaceholder")}
          multiline
          editable={!mustWaitForPeer}
        />
        <Pressable style={[styles.sendButton, mustWaitForPeer && styles.sendButtonDisabled]} onPress={handleSend} disabled={mustWaitForPeer}>
          <Text style={styles.sendButtonText}>{t("chat.send")}</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  list: { paddingVertical: 12, flexGrow: 1 },
  menuButton: { paddingHorizontal: 8 },
  menuButtonText: { fontSize: 22, color: colors.ink },
  restrictedBanner: {
    backgroundColor: colors.accentSoft,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  restrictedBannerText: { fontSize: 12.5, color: colors.accentDark, textAlign: "center" },
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 8,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxHeight: 100,
    fontSize: 15,
  },
  sendButton: { backgroundColor: colors.accent, borderRadius: 20, paddingHorizontal: 18, paddingVertical: 12 },
  sendButtonDisabled: { backgroundColor: colors.border },
  sendButtonText: { color: "#fff", fontWeight: "600" },
});
