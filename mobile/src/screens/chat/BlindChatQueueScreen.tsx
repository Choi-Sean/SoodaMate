import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import {
  getBlindChatLimit,
  getBlindChatQueueStatus,
  joinBlindChatQueue,
  leaveBlindChatQueue,
  requestAiMatch,
} from "../../api/blindChat";
import { getMatches } from "../../api/matches";
import { BLIND_CHAT_CATEGORY_KEYS } from "../../constants/blindChatCategories";
import ChipSelect from "../../components/ChipSelect";
import MultiChipSelect from "../../components/MultiChipSelect";
import RangeSlider from "../../components/RangeSlider";
import SingleSlider from "../../components/SingleSlider";
import { showAlert } from "../../utils/alert";
import { formatDistanceKm } from "../../utils/units";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "BlindChatQueue">;

const categoryOptions = BLIND_CHAT_CATEGORY_KEYS as unknown as readonly string[];
const GENDER_OPTIONS = ["male", "female"] as const;
const DEFAULT_MIN_AGE = 18;
const DEFAULT_MAX_AGE = 99;
const DEFAULT_DISTANCE_KM = 50;

/** Picks categories (+ optional gender/age/distance filters) -> POSTs
 * /blind-chat/queue. A "matched" response (either right away, from this
 * call, or later via polling) resolves the match's masked info from
 * /matches and pushes straight into ChatRoom — see usePurchaseReturnWatch's
 * foreground-refetch note elsewhere for why polling (not a new WS listener)
 * is the deliberate, low-risk choice here: the user is already idle/
 * waiting, so a few seconds of latency costs nothing, and this avoids
 * building a second realtime channel just for a screen with no matchId yet
 * to scope one to. */
export default function BlindChatQueueScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const isFocused = useIsFocused();
  const useImperial = i18n.language === "en";

  const [selected, setSelected] = useState<string[]>([]);
  const [gender, setGender] = useState<string | null>(null);
  const [ageRange, setAgeRange] = useState<[number, number]>([DEFAULT_MIN_AGE, DEFAULT_MAX_AGE]);
  const [distanceOn, setDistanceOn] = useState(false);
  const [distanceKm, setDistanceKm] = useState(DEFAULT_DISTANCE_KM);
  const [waiting, setWaiting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [aiMatching, setAiMatching] = useState(false);

  const { data: limit } = useQuery({ queryKey: ["blindChatLimit"], queryFn: getBlindChatLimit });

  const { data: status } = useQuery({
    queryKey: ["blindChatQueue"],
    queryFn: getBlindChatQueueStatus,
    enabled: waiting && isFocused,
    refetchInterval: waiting ? 3000 : false,
  });

  function currentFilters() {
    return {
      gender: gender as "male" | "female" | null,
      min_age: ageRange[0] === DEFAULT_MIN_AGE ? null : ageRange[0],
      max_age: ageRange[1] === DEFAULT_MAX_AGE ? null : ageRange[1],
      max_distance_km: distanceOn ? distanceKm : null,
    };
  }

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

  function explainError(e: any): string {
    if (e?.response?.status === 429) return t("blindChat.dailyLimitReached");
    return e?.response?.data?.detail ?? e?.message ?? "";
  }

  async function handleStart() {
    if (selected.length === 0) return;
    setStarting(true);
    try {
      const result = await joinBlindChatQueue(selected, currentFilters());
      if (result.status === "matched" && result.match_id) {
        await goToMatch(result.match_id);
      } else {
        setWaiting(true);
      }
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), explainError(e));
    } finally {
      setStarting(false);
    }
  }

  async function handleAiMatch() {
    if (selected.length === 0) return;
    // ai_match_credits are checked server-side (402 -> a "buy credits"
    // prompt below) — this screen doesn't fetch the payments balance just
    // to gate the button locally.
    setAiMatching(true);
    try {
      const result = await requestAiMatch(selected);
      if (result.found && result.match) {
        await goToMatch(result.match.id);
      } else {
        showAlert(t("blindChat.aiMatchTitle"), t("blindChat.aiMatchNoneFound"));
      }
    } catch (e: any) {
      if (e?.response?.status === 402) {
        showAlert(t("blindChat.aiMatchTitle"), t("blindChat.aiMatchNoCredits"));
      } else {
        showAlert(t("common.somethingWentWrong"), explainError(e));
      }
    } finally {
      setAiMatching(false);
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

      {limit && !limit.unlimited && (
        <View style={styles.limitBanner}>
          <Ionicons name="flash-outline" size={14} color={colors.accentDark} />
          <Text style={styles.limitBannerText}>{t("blindChat.dailyLimitRemaining", { count: limit.remaining })}</Text>
        </View>
      )}

      <MultiChipSelect
        label={t("blindChat.categoryLabel")}
        options={categoryOptions}
        translatePrefix="blindChatCategories"
        values={selected}
        onChange={setSelected}
      />

      <View style={styles.filtersCard}>
        <Text style={styles.filtersTitle}>{t("blindChat.filtersTitle")}</Text>
        <ChipSelect
          label={t("blindChat.genderFilterLabel")}
          options={GENDER_OPTIONS}
          translatePrefix="profileSetup"
          value={gender}
          onChange={setGender}
        />
        <RangeSlider
          label={t("blindChat.ageFilterLabel")}
          min={DEFAULT_MIN_AGE}
          max={DEFAULT_MAX_AGE}
          valueMin={ageRange[0]}
          valueMax={ageRange[1]}
          onChange={(lo, hi) => setAgeRange([lo, hi])}
        />
        <View style={styles.switchRow}>
          <Text style={styles.switchLabel}>{t("blindChat.distanceFilterLabel")}</Text>
          <Switch value={distanceOn} onValueChange={setDistanceOn} trackColor={{ true: colors.accent }} />
        </View>
        {distanceOn && (
          <SingleSlider
            label=""
            min={1}
            max={500}
            value={distanceKm}
            formatValue={(v) =>
              useImperial ? t("filters.distanceUpToMi", { mi: formatDistanceKm(v) }) : t("filters.distanceUpToKm", { km: v })
            }
            onChange={setDistanceKm}
          />
        )}
      </View>

      <Pressable
        style={[styles.startButton, selected.length === 0 && styles.startButtonDisabled]}
        onPress={handleStart}
        disabled={selected.length === 0 || starting || aiMatching}
      >
        {starting ? <ActivityIndicator color="#fff" /> : <Text style={styles.startButtonText}>{t("blindChat.start")}</Text>}
      </Pressable>

      <Pressable
        style={[styles.aiMatchButton, selected.length === 0 && styles.startButtonDisabled]}
        onPress={handleAiMatch}
        disabled={selected.length === 0 || starting || aiMatching}
      >
        {aiMatching ? (
          <ActivityIndicator color={colors.navy} />
        ) : (
          <>
            <Ionicons name="sparkles" size={16} color={colors.navy} />
            <Text style={styles.aiMatchButtonText}>{t("blindChat.aiMatchButton")}</Text>
          </>
        )}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, gap: 8 },
  intro: { fontSize: 14, color: colors.muted, lineHeight: 20, marginBottom: 8 },
  limitBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.creamDeep,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginBottom: 8,
    alignSelf: "flex-start",
  },
  limitBannerText: { fontSize: 12.5, color: colors.accentDark, fontWeight: "600" },
  filtersCard: {
    marginTop: 16,
    padding: 14,
    borderRadius: 14,
    backgroundColor: colors.creamDeep,
    gap: 4,
  },
  filtersTitle: { fontSize: 13, fontWeight: "700", color: colors.navy, marginBottom: 4 },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 14 },
  switchLabel: { fontSize: 14, fontWeight: "600", color: colors.muted },
  startButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 24 },
  startButtonDisabled: { opacity: 0.5 },
  startButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  aiMatchButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    borderWidth: 1.5,
    borderColor: colors.navy,
    borderRadius: 12,
    paddingVertical: 13,
    marginTop: 10,
  },
  aiMatchButtonText: { color: colors.navy, fontWeight: "700", fontSize: 15 },
  waitingContainer: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 16 },
  waitingTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, textAlign: "center" },
  waitingChips: { flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "center" },
  waitingChip: { backgroundColor: colors.creamDeep, borderRadius: 20, paddingVertical: 6, paddingHorizontal: 14 },
  waitingChipText: { fontSize: 13, color: colors.ink, fontWeight: "600" },
  cancelButton: { marginTop: 12, paddingVertical: 12, paddingHorizontal: 28, borderRadius: 12, backgroundColor: colors.creamDeep },
  cancelButtonText: { color: colors.muted, fontWeight: "700" },
});
