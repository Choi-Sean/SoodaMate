import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { useIsFocused } from "@react-navigation/native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { getBlindChatQueueStatus, joinBlindChatQueue, leaveBlindChatQueue } from "../../api/blindChat";
import { getMatches } from "../../api/matches";
import { BLIND_CHAT_CATEGORY_KEYS } from "../../constants/blindChatCategories";
import MultiChipSelect from "../../components/MultiChipSelect";
import { showAlert } from "../../utils/alert";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "BlindChatQueue">;

const categoryOptions = BLIND_CHAT_CATEGORY_KEYS as unknown as readonly string[];

/** Picks categories -> POSTs /blind-chat/queue. A "matched" response
 * (either right away, from this call, or later via polling) resolves the
 * match's masked info from /matches and pushes straight into ChatRoom —
 * see usePurchaseReturnWatch's foreground-refetch note elsewhere for why
 * polling (not a new WS listener) is the deliberate, low-risk choice here:
 * the user is already idle/waiting, so a few seconds of latency costs
 * nothing, and this avoids building a second realtime channel just for a
 * screen with no matchId yet to scope one to. */
export default function BlindChatQueueScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isFocused = useIsFocused();

  const [selected, setSelected] = useState<string[]>([]);
  const [waiting, setWaiting] = useState(false);
  const [starting, setStarting] = useState(false);

  const { data: status } = useQuery({
    queryKey: ["blindChatQueue"],
    queryFn: getBlindChatQueueStatus,
    enabled: waiting && isFocused,
    refetchInterval: waiting ? 3000 : false,
  });

  async function goToMatch(matchId: string) {
    setWaiting(false);
    const matches = await queryClient.fetchQuery({ queryKey: ["matches"], queryFn: getMatches });
    const match = matches.find((m) => m.id === matchId);
    navigation.replace("ChatRoom", {
      matchId,
      otherUserId: match?.other_user_id ?? "",
      otherDisplayName: match?.other_display_name ?? "?***",
    });
  }

  useEffect(() => {
    if (status?.status === "matched" && status.match_id) {
      goToMatch(status.match_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  async function handleStart() {
    if (selected.length === 0) return;
    setStarting(true);
    try {
      const result = await joinBlindChatQueue(selected);
      if (result.status === "matched" && result.match_id) {
        await goToMatch(result.match_id);
      } else {
        setWaiting(true);
      }
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    } finally {
      setStarting(false);
    }
  }

  async function handleCancel() {
    setWaiting(false);
    try {
      await leaveBlindChatQueue();
    } catch {
      // best-effort — the queue entry is harmless to leave behind briefly
    }
  }

  if (waiting) {
    return (
      <View style={styles.waitingContainer}>
        <ActivityIndicator size="large" color={colors.accent} />
        <Text style={styles.waitingTitle}>{t("blindChat.waitingTitle")}</Text>
        <View style={styles.waitingChips}>
          {selected.map((key) => (
            <View key={key} style={styles.waitingChip}>
              <Text style={styles.waitingChipText}>{t(`blindChatCategories.${key}`)}</Text>
            </View>
          ))}
        </View>
        <Pressable style={styles.cancelButton} onPress={handleCancel}>
          <Text style={styles.cancelButtonText}>{t("common.cancel")}</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.intro}>{t("blindChat.intro")}</Text>
      <MultiChipSelect
        label={t("blindChat.categoryLabel")}
        options={categoryOptions}
        translatePrefix="blindChatCategories"
        values={selected}
        onChange={setSelected}
      />
      <Pressable
        style={[styles.startButton, selected.length === 0 && styles.startButtonDisabled]}
        onPress={handleStart}
        disabled={selected.length === 0 || starting}
      >
        {starting ? <ActivityIndicator color="#fff" /> : <Text style={styles.startButtonText}>{t("blindChat.start")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, gap: 8 },
  intro: { fontSize: 14, color: colors.muted, lineHeight: 20, marginBottom: 8 },
  startButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 24 },
  startButtonDisabled: { opacity: 0.5 },
  startButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  waitingContainer: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 16 },
  waitingTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, textAlign: "center" },
  waitingChips: { flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "center" },
  waitingChip: { backgroundColor: colors.creamDeep, borderRadius: 20, paddingVertical: 6, paddingHorizontal: 14 },
  waitingChipText: { fontSize: 13, color: colors.ink, fontWeight: "600" },
  cancelButton: { marginTop: 12, paddingVertical: 12, paddingHorizontal: 28, borderRadius: 12, backgroundColor: colors.creamDeep },
  cancelButtonText: { color: colors.muted, fontWeight: "700" },
});
