import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
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
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import BlindChatFeedbackModal from "../../components/BlindChatFeedbackModal";
import ChatBubble from "../../components/ChatBubble";
import { getMessageHistory } from "../../api/messages";
import {
  acceptBlindReveal,
  deleteMatch,
  getIcebreaker,
  requestBlindReveal,
  spendBlindPeek,
  submitBlindFeedback,
} from "../../api/matches";
import { getMyProfile } from "../../api/profiles";
import { openShop } from "../../utils/openShop";
import { presignChatImage, uploadToPresignedUrl } from "../../api/uploads";
import { blockUser, reportUser } from "../../api/safety";
import { MBTI_COMPATIBLE_TYPE, type MbtiType } from "../../constants/mbtiTypes";
import { useCall } from "../../services/CallContext";
import { webrtcAvailable } from "../../services/webrtc";
import { showAlert } from "../../utils/alert";
import { useChatSocket, type ChatSocketError } from "../../hooks/useChatSocket";
import { useMatches } from "../../hooks/useMatches";
import { useAuthStore } from "../../store/authStore";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import type { BlindChatFeedbackInput, ChatMessage, Icebreaker } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "ChatRoom">;

export default function ChatRoomScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { matchId, otherUserId, otherDisplayName: otherDisplayNameParam } = route.params;
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
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
  // The route param is only a fallback for the first paint before /matches
  // has loaded — live match data (masked "S***" pre-reveal, real name once
  // blind_revealed flips) always wins once available.
  const otherDisplayName = match?.other_display_name ?? otherDisplayNameParam;
  // Mutual reveal only — both sides agreed. This is the one that must gate
  // video calling: a call exposes a live face/voice to the PEER too, so it
  // must never unlock just because *I* privately peeked (see canOpenProfile
  // below) — that would blow the whole point of a stealth peek.
  const mutuallyRevealed = !!match && (!match.is_blind || match.blind_revealed);
  // Same gate the backend uses for other_display_name/other_photo_url masking
  // (services/match_service.py's hide_identity) — true once EITHER side has
  // mutually revealed OR I personally spent a stealth-peek credit on this
  // match (has_peeked is always my own, never the peer's — see MatchOut's
  // docstring). Only for one-way things: opening the header/MatchedProfileScreen.
  const canOpenProfile = mutuallyRevealed || !!match?.has_peeked;

  // Cheap cache read in practice — RootNavigator already populated this exact
  // key on app open. Only needed here for the MBTI-compatibility hint below.
  const { data: myProfile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const myMbti = (myProfile?.mbti as MbtiType | undefined) ?? null;
  const otherMbti = (match?.other_mbti as MbtiType | undefined) ?? null;
  const isMbtiCompatible = !!myMbti && !!otherMbti && MBTI_COMPATIBLE_TYPE[myMbti] === otherMbti;

  async function handleRequestReveal() {
    try {
      await requestBlindReveal(matchId);
      await queryClient.invalidateQueries({ queryKey: ["matches"] });
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    }
  }

  async function handleAcceptReveal() {
    try {
      await acceptBlindReveal(matchId);
      await queryClient.invalidateQueries({ queryKey: ["matches"] });
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    }
  }

  const [peeking, setPeeking] = useState(false);

  async function doPeek() {
    setPeeking(true);
    try {
      await spendBlindPeek(matchId);
      await queryClient.invalidateQueries({ queryKey: ["matches"] });
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
    } catch (e: any) {
      if (e?.response?.status === 402) {
        // No credits left — same "go buy some" flow as everywhere else in
        // the app that hits a 402 (blind chat's AI-match, superlikes, ...).
        showAlert(t("blindChat.peekNoCreditsTitle"), t("blindChat.peekNoCreditsBody"), [
          { text: t("common.cancel"), style: "cancel" },
          { text: t("blindChat.peekBuyCta"), onPress: () => openShop(queryClient) },
        ]);
      } else {
        showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
      }
    } finally {
      setPeeking(false);
    }
  }

  function handlePeek() {
    if (peeking) return;
    // Everyone gets 1 free peek/day, spent before any purchased credit (see
    // match_service.use_blind_peek) — say so up front so "사용" doesn't
    // surprise someone who still has today's free one left, or someone with
    // none left into thinking this one's free when it'll spend a purchased
    // credit.
    const freeRemaining = myProfile?.free_peek_remaining ?? 0;
    const body = freeRemaining > 0 ? t("blindChat.peekConfirmBodyFree", { count: freeRemaining }) : t("blindChat.peekConfirmBody");
    showAlert(t("blindChat.peekConfirmTitle"), body, [
      { text: t("common.cancel"), style: "cancel" },
      { text: t("blindChat.peekConfirm"), onPress: doPeek },
    ]);
  }

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  // KeyboardAvoidingView measures its frame relative to its *parent*, but the
  // keyboard's position is in window coordinates. The native header (and status
  // bar) sit above this screen, so without their height as the offset the input
  // bar ends up that far underneath the keyboard. Measure it instead of
  // hard-coding a header height so it holds on every device / text size.
  const wrapRef = useRef<View>(null);
  const [keyboardOffset, setKeyboardOffset] = useState(0);
  const measureKeyboardOffset = useCallback(() => {
    wrapRef.current?.measureInWindow((_x, y) => setKeyboardOffset((prev) => (Math.abs(prev - y) < 0.5 ? prev : y)));
  }, []);
  const [bioExpanded, setBioExpanded] = useState(false);
  const [feedbackModalVisible, setFeedbackModalVisible] = useState(false);
  const otherBioLines = [match?.other_bio, match?.other_bio2, match?.other_bio3].filter(
    (b): b is string => !!b && b.trim().length > 0
  );

  useEffect(() => {
    if (history) setMessages(history);
  }, [history]);

  const handleIncoming = useCallback((msg: ChatMessage) => {
    setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
  }, []);

  const handleSocketError = useCallback(
    (err: ChatSocketError) => {
      // Roll back the optimistic local echo of whatever we just tried to send.
      const rejection: Record<string, string> = {
        first_message_restricted: "chat.firstMessageRestricted",
        message_too_long: "chat.messageTooLong",
        rate_limited: "chat.rateLimited",
        invalid_image: "chat.invalidImage",
      };
      const key = rejection[err.code];
      if (key) {
        setMessages((prev) => prev.filter((m) => !m.id.startsWith("local-")));
        showAlert(t("common.somethingWentWrong"), t(key));
      }
    },
    [t]
  );

  const handleBlindRevealUpdate = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["matches"] });
  }, [queryClient]);

  const markMessageDeletedLocally = useCallback((messageId: string) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? { ...m, message_type: "deleted", content: "", image_url: null, translated_content: null }
          : m
      )
    );
  }, []);

  const { connected, sendMessage, sendImageMessage, markRead, deleteMessage } = useChatSocket(
    matchId,
    handleIncoming,
    handleSocketError,
    handleBlindRevealUpdate,
    markMessageDeletedLocally
  );

  const handleDeleteMessage = useCallback(
    (messageId: string) => {
      // No round-trip confirmation comes back to the deleter (see
      // useChatSocket's deleteMessage docstring) — update locally right away.
      markMessageDeletedLocally(messageId);
      deleteMessage(messageId);
    },
    [deleteMessage, markMessageDeletedLocally]
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

  async function handleSubmitFeedback(input: BlindChatFeedbackInput) {
    try {
      await submitBlindFeedback(matchId, input);
      setFeedbackModalVisible(false);
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    }
  }

  function confirmBlock() {
    showAlert(t("chat.blockConfirmTitle"), t("chat.blockConfirmBody"), [
      { text: t("chat.cancel"), style: "cancel" },
      { text: t("chat.blockConfirm"), style: "destructive", onPress: doBlock },
    ]);
  }

  async function doDeleteMatch() {
    try {
      await deleteMatch(matchId);
      await queryClient.invalidateQueries({ queryKey: ["matches"] });
      navigation.navigate("ChatList");
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    }
  }

  function confirmDeleteMatch() {
    showAlert(t("chat.deleteChatTitle"), t("chat.deleteChatBody"), [
      { text: t("common.cancel"), style: "cancel" },
      { text: t("common.delete"), style: "destructive", onPress: doDeleteMatch },
    ]);
  }

  function openMenu() {
    showAlert(otherDisplayName, undefined, [
      {
        text: t("chat.writeCoupleStory"),
        onPress: () => navigation.navigate("SubmitCoupleStory", { matchId, otherDisplayName }),
      },
      ...(match?.is_blind
        ? [{ text: t("blindFeedback.menuItem"), onPress: () => setFeedbackModalVisible(true) }]
        : []),
      { text: t("chat.report"), onPress: openReportReasons },
      { text: t("chat.block"), style: "destructive", onPress: confirmBlock },
      { text: t("chat.deleteChat"), style: "destructive", onPress: confirmDeleteMatch },
      { text: t("chat.cancel"), style: "cancel" },
    ]);
  }

  const genderIconName =
    match?.other_gender === "male" ? "male" : match?.other_gender === "female" ? "female" : null;

  const call = useCall();
  // Reuses the exact same gate the server checks for calling (chat_service.
  // is_message_allowed — the Bumble-style "she goes first" rule, see routers/
  // ws_chat.py::_handle_call_offer): can_send_first_message already encodes
  // it for messaging, and the two are deliberately the same underlying state.
  const canCall =
    webrtcAvailable && mutuallyRevealed && !isExpired && !!match?.can_send_first_message && call.phase === "idle";

  function handleStartCall() {
    if (!canCall) return;
    call.startCall({ matchId, otherUserId, otherDisplayName, otherGender: match?.other_gender ?? null }, "video");
  }

  function handleStartVoiceCall() {
    if (!canCall) return;
    call.startCall({ matchId, otherUserId, otherDisplayName, otherGender: match?.other_gender ?? null }, "audio");
  }

  useLayoutEffect(() => {
    navigation.setOptions({
      headerTitle: () => (
        <Pressable
          onPress={canOpenProfile ? () => navigation.navigate("MatchedProfile", { matchId }) : undefined}
          disabled={!canOpenProfile}
          hitSlop={8}
          style={styles.headerTitleRow}
        >
          <Text style={styles.headerTitleText} numberOfLines={1}>
            {otherDisplayName}
          </Text>
          {genderIconName && (
            <Ionicons
              name={genderIconName}
              size={15}
              color={match?.other_gender === "male" ? colors.navy : colors.heart}
              style={styles.headerGenderIcon}
            />
          )}
        </Pressable>
      ),
      headerRight: () => (
        <View style={styles.headerRightRow}>
          {webrtcAvailable && mutuallyRevealed && !isExpired && (
            <>
              <Pressable
                onPress={handleStartVoiceCall}
                disabled={!canCall}
                hitSlop={12}
                style={[styles.callButton, !canCall && styles.callButtonDisabled]}
              >
                <Ionicons name="call" size={19} color={canCall ? colors.accentDark : colors.muted} />
              </Pressable>
              <Pressable
                onPress={handleStartCall}
                disabled={!canCall}
                hitSlop={12}
                style={[styles.callButton, !canCall && styles.callButtonDisabled]}
              >
                <Ionicons name="videocam" size={20} color={canCall ? colors.accentDark : colors.muted} />
              </Pressable>
            </>
          )}
          <Pressable onPress={openMenu} hitSlop={12} style={styles.menuButton}>
            <Text style={styles.menuButtonText}>⋯</Text>
          </Pressable>
        </View>
      ),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    navigation,
    otherUserId,
    otherDisplayName,
    match?.other_gender,
    canOpenProfile,
    mutuallyRevealed,
    matchId,
    canCall,
    isExpired,
  ]);

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
    <View ref={wrapRef} style={styles.container} onLayout={measureKeyboardOffset}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={keyboardOffset}
      >
        {historyLoading ? (
          <View style={styles.loadingCenter}>
            <ActivityIndicator size="large" color={colors.accent} />
          </View>
        ) : (
          <FlatList
            data={messages}
            keyExtractor={(m) => m.id}
            renderItem={({ item }) => (
              <ChatBubble
                message={item}
                isMine={item.sender_id === userId}
                onDelete={item.sender_id === userId ? handleDeleteMessage : undefined}
              />
            )}
            contentContainerStyle={styles.list}
          />
        )}
        {otherBioLines.length > 0 && (
          <Pressable style={styles.bioCard} onPress={() => setBioExpanded((v) => !v)}>
            <View style={styles.bioCardHeader}>
              <Text style={styles.bioCardLabel}>{t("chat.aboutThem", { name: otherDisplayName })}</Text>
              <Ionicons name={bioExpanded ? "chevron-up" : "chevron-down"} size={16} color={colors.muted} />
            </View>
            {bioExpanded && (
              <View style={styles.bioCardBody}>
                {otherBioLines.map((line, i) => (
                  <Text key={i} style={styles.bioCardText}>
                    {line}
                  </Text>
                ))}
              </View>
            )}
          </Pressable>
        )}
        {!historyLoading && messages.length === 0 && icebreakerText && !composerLocked && (
          <Pressable style={styles.icebreakerChip} onPress={() => setInput(icebreakerText)}>
            <Text style={styles.icebreakerChipLabel}>{t("chat.icebreakerLabel")}</Text>
            <Text style={styles.icebreakerChipText}>{icebreakerText}</Text>
          </Pressable>
        )}
        {match?.is_blind && !match.blind_revealed && (
          <View style={styles.blindBanner}>
            {match.blind_categories.length > 0 && (
              <Text style={styles.blindBannerCategories}>
                {t("blindChat.matchedOn", {
                  categories: match.blind_categories.map((c) => t(`blindChatCategories.${c}`)).join(", "),
                })}
              </Text>
            )}
            {otherMbti && (
              <Text style={styles.blindBannerCategories}>
                {t(isMbtiCompatible ? "blindChat.matchedMbtiCompatible" : "blindChat.matchedMbti", { mbti: otherMbti })}
              </Text>
            )}
            {match.has_incoming_reveal_request ? (
              <>
                <Text style={styles.blindBannerText}>{t("blindChat.incomingRevealRequest", { name: otherDisplayName })}</Text>
                <Pressable style={styles.blindBannerButton} onPress={handleAcceptReveal}>
                  <Text style={styles.blindBannerButtonText}>{t("blindChat.acceptReveal")}</Text>
                </Pressable>
              </>
            ) : match.reveal_requested_by_me ? (
              <Text style={styles.blindBannerText}>{t("blindChat.revealPending")}</Text>
            ) : (
              match.can_request_reveal && (
                <Pressable style={styles.blindBannerButton} onPress={handleRequestReveal}>
                  <Text style={styles.blindBannerButtonText}>{t("blindChat.requestReveal")}</Text>
                </Pressable>
              )
            )}
            {/* Independent of the mutual-reveal flow above — a private, one-sided
                peek nobody else here ever finds out about. */}
            {match.has_peeked ? (
              <Pressable onPress={() => navigation.navigate("MatchedProfile", { matchId })} hitSlop={8}>
                <Text style={styles.blindBannerPeekedText}>{t("blindChat.peekedAlready")}</Text>
              </Pressable>
            ) : (
              <Pressable
                style={styles.blindBannerSecondaryButton}
                onPress={handlePeek}
                disabled={peeking}
                hitSlop={8}
              >
                {peeking ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text style={styles.blindBannerSecondaryButtonText}>{t("blindChat.peekButton")}</Text>
                )}
              </Pressable>
            )}
          </View>
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
              maxLength={2000}
              editable={!composerLocked}
            />
            <Pressable style={[styles.sendButton, composerLocked && styles.sendButtonDisabled]} onPress={handleSend} disabled={composerLocked}>
              <Text style={styles.sendButtonText}>{t("chat.send")}</Text>
            </Pressable>
          </View>
        )}
        <BlindChatFeedbackModal
          visible={feedbackModalVisible}
          otherDisplayName={otherDisplayName}
          onCancel={() => setFeedbackModalVisible(false)}
          onSubmit={handleSubmitFeedback}
        />
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  list: { paddingVertical: 12, flexGrow: 1 },
  loadingCenter: { flex: 1, alignItems: "center", justifyContent: "center" },
  headerRightRow: { flexDirection: "row", alignItems: "center" },
  callButton: { paddingHorizontal: 8 },
  callButtonDisabled: { opacity: 0.4 },
  menuButton: { paddingHorizontal: 8 },
  menuButtonText: { fontSize: 22, color: colors.ink },
  headerTitleRow: { flexDirection: "row", alignItems: "center", maxWidth: 220 },
  headerTitleText: { fontSize: 17, fontWeight: "800", color: colors.navy, flexShrink: 1 },
  headerGenderIcon: { marginLeft: 4 },
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
  bioCard: {
    marginHorizontal: 12,
    marginBottom: 8,
    padding: 12,
    borderRadius: 14,
    backgroundColor: colors.creamDeep,
  },
  bioCardHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  bioCardLabel: { fontSize: 12, fontWeight: "700", color: colors.navy },
  bioCardBody: { marginTop: 8, gap: 6 },
  bioCardText: { fontSize: 13, color: colors.ink, lineHeight: 18 },
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
  blindBanner: {
    marginHorizontal: 12,
    marginBottom: 8,
    padding: 12,
    borderRadius: 14,
    backgroundColor: colors.navy,
    gap: 8,
    alignItems: "center",
  },
  blindBannerCategories: { fontSize: 11.5, color: "rgba(255,255,255,0.75)", textAlign: "center" },
  blindBannerText: { fontSize: 13, color: "#fff", textAlign: "center", fontWeight: "600" },
  blindBannerButton: { backgroundColor: colors.accent, borderRadius: 20, paddingVertical: 9, paddingHorizontal: 20 },
  blindBannerSecondaryButton: {
    borderWidth: 1,
    borderColor: "rgba(255,255,255,0.5)",
    borderRadius: 20,
    paddingVertical: 7,
    paddingHorizontal: 16,
    minHeight: 30,
    minWidth: 30,
    alignItems: "center",
    justifyContent: "center",
  },
  blindBannerSecondaryButtonText: { color: "#fff", fontWeight: "600", fontSize: 12.5 },
  blindBannerPeekedText: { color: "rgba(255,255,255,0.75)", fontSize: 12, textDecorationLine: "underline" },
  blindBannerButtonText: { color: "#fff", fontWeight: "700", fontSize: 13.5 },
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
