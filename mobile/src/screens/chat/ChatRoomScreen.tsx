import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  Text,
  TextInput,
  View,
  StyleSheet,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import ChatBubble from "../../components/ChatBubble";
import { getMessageHistory } from "../../api/messages";
import { getIcebreaker } from "../../api/matches";
import { presignChatImage, uploadToPresignedUrl } from "../../api/uploads";
import { blockUser, reportUser } from "../../api/safety";
import { showAlert } from "../../utils/alert";
import { useChatSocket, type ChatSocketError } from "../../hooks/useChatSocket";
import { useMatches } from "../../hooks/useMatches";
import { useAuthStore } from "../../store/authStore";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import type { ChatMessage, Icebreaker } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "ChatRoom">;

export default function ChatRoomScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { matchId, otherUserId, otherDisplayName } = route.params;
  const userId = useAuthStore((s) => s.userId);
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["messages", matchId],
    queryFn: () => getMessageHistory(matchId),
  });

  // Phase 14: Bumble first-message restriction state comes from /matches
  // (already recomputed server-side on every fetch, including lazy expiry) —
  // no separate single-match endpoint exists, and react-query caches this
  // list cheaply since ChatListScreen already fetches it too.
  const { data: matches } = useMatches();
  const match = useMemo(() => matches?.find((m) => m.id === matchId), [matches, matchId]);
  const isExpired = match?.is_active === false;
  const mustWaitForPeer = !isExpired && match?.is_message_restricted && !match?.can_send_first_message;
  const composerLocked = isExpired || mustWaitForPeer;

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
        showAlert(t("common.somethingWentWrong"), t("chat.firstMessageRestricted"));
      }
    },
    [t]
  );

  const { connected, sendMessage, sendImageMessage, markRead } = useChatSocket(
    matchId,
    handleIncoming,
    handleSocketError
  );

  useEffect(() => {
    // Re-fires once `connected` flips true — mount alone isn't enough since
    // opening the WebSocket is async and markRead is a no-op until then.
    if (connected) markRead();
  }, [connected, markRead]);

  // Suggest an opening line once we know there's no history and it's
  // finished loading — a fresh, empty conversation only. Silently does
  // nothing on error (a missing icebreaker is never worth surfacing).
  const { data: icebreaker } = useQuery<Icebreaker>({
    queryKey: ["icebreaker", matchId],
    queryFn: () => getIcebreaker(matchId),
    enabled: !historyLoading && messages.length === 0,
    retry: false,
  });

  // icebreaker.type picks which i18n namespace icebreaker.key belongs to —
  // shared_kcontent -> kcontent.<key>, shared_interest -> interests.<key>,
  // shared_language -> languages.<key>; the other two types carry no key.
  const ICEBREAKER_LABEL_NAMESPACE: Record<string, string> = {
    shared_kcontent: "kcontent",
    shared_interest: "interests",
    shared_language: "languages",
  };
  const icebreakerText = icebreaker
    ? t(`chat.icebreaker.${icebreaker.type}`, {
        label: icebreaker.key
          ? t(`${ICEBREAKER_LABEL_NAMESPACE[icebreaker.type] ?? "interests"}.${icebreaker.key}`, {
              defaultValue: icebreaker.key,
            })
          : "",
      })
    : null;

  const [sendingImage, setSendingImage] = useState(false);

  async function handleSendImage() {
    if (composerLocked || sendingImage) return;
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      showAlert(t("common.somethingWentWrong"), t("chat.imagePermission"));
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8 });
    if (result.canceled || !result.assets[0]) return;

    setSendingImage(true);
    try {
      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignChatImage(contentType);
      await uploadToPresignedUrl(upload_url, result.assets[0].uri, contentType);
      sendImageMessage(gcs_object_path);
      setMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          match_id: matchId,
          sender_id: userId ?? "",
          content: "",
          message_type: "image",
          image_url: result.assets[0].uri,
          original_language: null,
          translated_content: null,
          translated_language: null,
          sent_at: new Date().toISOString(),
          delivered_at: null,
          read_at: null,
        },
      ]);
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? t("chat.imageSendError"));
    } finally {
      setSendingImage(false);
    }
  }

  async function submitReport(reason: string) {
    try {
      await reportUser(otherUserId, reason);
      showAlert(t("chat.reported"), t("chat.reportedBody"));
    } catch {
      showAlert(t("common.somethingWentWrong"), t("chat.errorGeneric"));
    }
  }

  function openReportReasons() {
    showAlert(t("chat.reportReasonTitle"), undefined, [
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
      showAlert(t("common.somethingWentWrong"), t("chat.errorGeneric"));
    }
  }

  function confirmBlock() {
    showAlert(t("chat.blockConfirmTitle"), t("chat.blockConfirmBody"), [
      { text: t("chat.cancel"), style: "cancel" },
      { text: t("chat.blockConfirm"), style: "destructive", onPress: doBlock },
    ]);
  }

  function openMenu() {
    showAlert(otherDisplayName, undefined, [
      {
        text: t("chat.writeCoupleStory"),
        onPress: () => navigation.navigate("SubmitCoupleStory", { matchId, otherDisplayName }),
      },
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
    if (!content || composerLocked) return;

    sendMessage(content);
    setMessages((prev) => [
      ...prev,
      {
        id: `local-${Date.now()}`,
        match_id: matchId,
        sender_id: userId ?? "",
        content,
        message_type: "text",
        image_url: null,
        original_language: null,
        translated_content: null,
        translated_language: null,
        sent_at: new Date().toISOString(),
        delivered_at: null,
        read_at: null,
      },
    ]);
    setInput("");
  }

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      {historyLoading ? (
        <View style={styles.loadingCenter}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      ) : (
        <FlatList
          data={messages}
          keyExtractor={(m) => m.id}
          renderItem={({ item }) => <ChatBubble message={item} isMine={item.sender_id === userId} />}
          contentContainerStyle={styles.list}
        />
      )}
      {!historyLoading && messages.length === 0 && icebreakerText && !composerLocked && (
        <Pressable style={styles.icebreakerChip} onPress={() => setInput(icebreakerText)}>
          <Text style={styles.icebreakerChipLabel}>{t("chat.icebreakerLabel")}</Text>
          <Text style={styles.icebreakerChipText}>{icebreakerText}</Text>
        </Pressable>
      )}
      {isExpired ? (
        <View style={styles.expiredBanner}>
          <Text style={styles.expiredBannerText}>{t("chat.expiredBanner")}</Text>
        </View>
      ) : (
        mustWaitForPeer && (
          <View style={styles.restrictedBanner}>
            <Text style={styles.restrictedBannerText}>{t("chat.restrictedBanner")}</Text>
          </View>
        )
      )}
      {!isExpired && (
        <View style={styles.inputBar}>
          <Pressable
            style={[styles.imageButton, composerLocked && styles.sendButtonDisabled]}
            onPress={handleSendImage}
            disabled={composerLocked || sendingImage}
          >
            {sendingImage ? (
              <ActivityIndicator size="small" color={colors.accentDark} />
            ) : (
              <Ionicons name="image-outline" size={22} color={colors.accentDark} />
            )}
          </Pressable>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder={t("chat.messagePlaceholder")}
            multiline
            editable={!composerLocked}
          />
          <Pressable style={[styles.sendButton, composerLocked && styles.sendButtonDisabled]} onPress={handleSend} disabled={composerLocked}>
            <Text style={styles.sendButtonText}>{t("chat.send")}</Text>
          </Pressable>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  list: { paddingVertical: 12, flexGrow: 1 },
  loadingCenter: { flex: 1, alignItems: "center", justifyContent: "center" },
  menuButton: { paddingHorizontal: 8 },
  menuButtonText: { fontSize: 22, color: colors.ink },
  restrictedBanner: {
    backgroundColor: colors.accentSoft,
    paddingVertical: 10,
    paddingHorizontal: 16,
  },
  restrictedBannerText: { fontSize: 12.5, color: colors.accentDark, textAlign: "center" },
  expiredBanner: {
    backgroundColor: colors.creamDeep,
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  expiredBannerText: { fontSize: 12.5, color: colors.muted, textAlign: "center" },
  icebreakerChip: {
    marginHorizontal: 12,
    marginBottom: 8,
    padding: 12,
    borderRadius: 14,
    backgroundColor: colors.creamDeep,
    borderWidth: 1,
    borderColor: colors.accentSoft,
  },
  icebreakerChipLabel: { fontSize: 10.5, fontWeight: "700", color: colors.accentDark, marginBottom: 3, textTransform: "uppercase" },
  icebreakerChipText: { fontSize: 13.5, color: colors.ink, lineHeight: 18 },
  inputBar: {
    flexDirection: "row",
    alignItems: "flex-end",
    padding: 12,
    borderTopWidth: 1,
    borderTopColor: colors.border,
    gap: 8,
  },
  imageButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.creamDeep,
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
