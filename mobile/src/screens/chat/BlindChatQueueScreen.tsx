import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useIsFocused } from "@react-navigation/native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import {
  claimBlindChatAdBonus,
  getBlindChatLimit,
  getBlindChatQueueStats,
  getBlindChatQueueStatus,
  joinBlindChatQueue,
  leaveBlindChatQueue,
  requestAiMatch,
} from "../../api/blindChat";
import { getMatches } from "../../api/matches";
import { getMyProfile } from "../../api/profiles";
import { vibrateOnMatch } from "../../utils/matchVibration";
import { BLIND_CHAT_CATEGORY_KEYS, knownBlindChatCategories } from "../../constants/blindChatCategories";
import AdCard from "../../components/AdCard";
import ChipSelect from "../../components/ChipSelect";
import MultiChipSelect from "../../components/MultiChipSelect";
import RangeSlider from "../../components/RangeSlider";
import SingleSlider from "../../components/SingleSlider";
import { showRewardedAd } from "../../services/rewardedAd";
import { useAuthStore } from "../../store/authStore";
import { showAlert } from "../../utils/alert";
import { calculateProfileCompleteness, MIN_COMPLETENESS_FOR_ACTIVE } from "../../utils/profileCompleteness";
import { formatDistanceKm } from "../../utils/units";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "BlindChatQueue">;

const categoryOptions = BLIND_CHAT_CATEGORY_KEYS as unknown as readonly string[];
// "all" opens the queue to every gender — the backend already treats it as
// the same "no restriction" value used by Profile.interested_in (see
// blind_chat_service._compatibility_filters), so no backend change was
// needed, just exposing the option here. Leaving the chip unselected still
// falls back to the viewer's own profile interested_in default (opposite
// gender only, for the common straight case).
const GENDER_OPTIONS = ["male", "female", "all"] as const;
const DEFAULT_MIN_AGE = 18;
const DEFAULT_MAX_AGE = 60;
const DEFAULT_DISTANCE_KM = 50;
const MAX_DISTANCE_KM = 500;
// However fast a real match arrives (even instantly, when someone was
// already waiting), the waiting/ad screen stays up at least this long before
// revealing it — otherwise a lucky instant match skips the one ad surface
// left in the app entirely. Re-rolled fresh each time a queue attempt
// starts (see beginWaiting) rather than a fixed value.
function randomMinRevealMs(): number {
  return 3000 + Math.random() * 2000;
}
// After this long with no match, stop pretending the spinner means
// something is about to happen and show an honest empty state instead —
// polling keeps running underneath so a late match still gets picked up.
const QUEUE_TIMEOUT_MS = 20000;

/** Picks categories (+ optional gender/age/distance filters) -> POSTs
 * /blind-chat/queue. A "matched" response (either right away, from this
 * call, or later via polling) resolves the match's masked info from
 * /matches and pushes straight into ChatRoom — see usePurchaseReturnWatch's
 * foreground-refetch note elsewhere for why polling (not a new WS listener)
 * is the deliberate, low-risk choice here: the user is already idle/
 * waiting, so a few seconds of latency costs nothing, and this avoids
 * building a second realtime channel just for a screen with no matchId yet
 * to scope one to. */
export default function BlindChatQueueScreen({ navigation, route }: Props) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const userId = useAuthStore((s) => s.userId);
  const isFocused = useIsFocused();
  const useImperial = i18n.language === "en";

  const [selected, setSelected] = useState<string[]>(route.params?.initialCategories ?? []);
  const [gender, setGender] = useState<string | null>(null);
  const [ageRange, setAgeRange] = useState<[number, number]>([DEFAULT_MIN_AGE, DEFAULT_MAX_AGE]);
  const [distanceOn, setDistanceOn] = useState(false);
  const [distanceKm, setDistanceKm] = useState(DEFAULT_DISTANCE_KM);
  const [waiting, setWaiting] = useState(false);
  const [starting, setStarting] = useState(false);
  const [aiMatching, setAiMatching] = useState(false);
  const [claimingBonus, setClaimingBonus] = useState(false);
  // The wait for a match is genuine idle time (no active conversation to
  // interrupt), unlike the chat itself — one of the app's ad surfaces
  // alongside the Swipe deck's own in-stack sponsored cards. Hidden outright
  // on failure to load rather than leaving a dead/broken box.
  const [adUnavailable, setAdUnavailable] = useState(false);
  // When the current queue attempt started (Date.now()) — the anchor both
  // revealMatch (minimum ad-exposure hold) and the timeout timer measure
  // from. Kept in state (not just a ref) because the polling effect below
  // needs to read it on a later render, after the initial tap.
  const [waitingStartedAt, setWaitingStartedAt] = useState<number | null>(null);
  // True once QUEUE_TIMEOUT_MS has passed with no match — swaps the spinner
  // for an honest "no one's here" state. Polling keeps running underneath,
  // so a match that arrives after this still gets picked up and revealed.
  const [queueTimedOut, setQueueTimedOut] = useState(false);
  const revealTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const timeoutTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (revealTimerRef.current) clearTimeout(revealTimerRef.current);
      if (timeoutTimerRef.current) clearTimeout(timeoutTimerRef.current);
    };
  }, []);

  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const { data: limit } = useQuery({ queryKey: ["blindChatLimit"], queryFn: getBlindChatLimit });
  // Live per-category headcount for the picker screen — off while waiting
  // (that screen shows its own spinner, this number would just be stale
  // noise by the time anyone looked at it).
  const { data: queueStats } = useQuery({
    queryKey: ["blindChatQueueStats"],
    queryFn: getBlindChatQueueStats,
    enabled: !waiting && isFocused,
    refetchInterval: !waiting && isFocused ? 15000 : false,
  });
  const selectedWaitingCount = selected.reduce((sum, key) => sum + (queueStats?.counts[key] ?? 0), 0);
  // Only suggest alternatives once at least one category is picked and none
  // of them have anyone waiting — an empty selection has nothing to compare.
  const otherWaitingCategories =
    selected.length > 0 && selectedWaitingCount === 0
      ? Object.entries(queueStats?.counts ?? {})
          .filter(([key]) => !selected.includes(key))
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
      : [];

  // Preselect the categories chosen at signup (or last saved on Edit
  // Profile) so a returning user doesn't have to re-pick every time — but
  // only when nothing more specific was passed in (the popup's own
  // one-category tap, via route.params.initialCategories) and the user
  // hasn't already touched the picker on this screen.
  useEffect(() => {
    if (route.params?.initialCategories) return;
    if (selected.length > 0) return;
    const saved = knownBlindChatCategories(profile?.preferred_categories);
    if (saved.length > 0) setSelected(saved);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profile]);

  // The gender chip starts on the profile's own "interested in" so what's
  // shown is exactly what gets used (previously it started empty and
  // silently fell back to the profile value). Once only — never overwrites a
  // choice the user has already changed. Choosing something different for
  // this match is allowed and wins over the profile, after a confirmation
  // (see confirmGenderChoice).
  const genderDefaulted = useRef(false);
  useEffect(() => {
    if (genderDefaulted.current || !profile) return;
    genderDefaulted.current = true;
    if ((GENDER_OPTIONS as readonly string[]).includes(profile.interested_in)) setGender(profile.interested_in);
  }, [profile]);

  const { data: status } = useQuery({
    queryKey: ["blindChatQueue"],
    queryFn: getBlindChatQueueStatus,
    enabled: waiting && isFocused,
    refetchInterval: waiting ? 3000 : false,
  });

  function currentFilters() {
    return {
      gender: gender as "male" | "female" | "all" | null,
      min_age: ageRange[0] === DEFAULT_MIN_AGE ? null : ageRange[0],
      max_age: ageRange[1] === DEFAULT_MAX_AGE ? null : ageRange[1],
      max_distance_km: distanceOn ? distanceKm : null,
    };
  }

  async function goToMatch(matchId: string) {
    setWaiting(false);
    vibrateOnMatch();
    const matches = await queryClient.fetchQuery({ queryKey: ["matches"], queryFn: getMatches });
    const match = matches.find((m) => m.id === matchId);
    navigation.replace("ChatRoom", {
      matchId,
      otherUserId: match?.other_user_id ?? "",
      otherDisplayName: match?.other_display_name ?? "?***",
    });
  }

  // Starts (or restarts, on retry) a queue attempt's local bookkeeping —
  // resets the timeout clock and hands back the start timestamp revealMatch
  // needs, since the caller's own `waitingStartedAt` state read in the same
  // tick would still be stale (React hasn't re-rendered yet).
  function beginWaiting(): number {
    if (timeoutTimerRef.current) clearTimeout(timeoutTimerRef.current);
    setQueueTimedOut(false);
    const startedAt = Date.now();
    setWaitingStartedAt(startedAt);
    setWaiting(true);
    timeoutTimerRef.current = setTimeout(() => setQueueTimedOut(true), QUEUE_TIMEOUT_MS);
    return startedAt;
  }

  // Whether the match was found instantly (from the initial join call) or
  // via polling, both paths funnel through here so neither can skip the
  // minimum ad-exposure hold.
  function revealMatch(matchId: string, startedAt: number) {
    // A reveal is already scheduled (e.g. the 3s poll ticked again during
    // the hold) — don't stack a second timer on top of it.
    if (revealTimerRef.current) return;
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current);
      timeoutTimerRef.current = null;
    }
    const remaining = Math.max(0, randomMinRevealMs() - (Date.now() - startedAt));
    revealTimerRef.current = setTimeout(() => goToMatch(matchId), remaining);
  }

  useEffect(() => {
    if (status?.status === "matched" && status.match_id && waitingStartedAt != null) {
      revealMatch(status.match_id, waitingStartedAt);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status]);

  function explainError(e: any): string {
    const detail = e?.response?.data?.detail;
    if (e?.response?.status === 429) {
      // 429 means two different things here: the API's per-minute rate limit
      // (plain string, backend/app/core/rate_limit.py) or the daily match limit.
      return typeof detail === "string" && detail.startsWith("too many requests")
        ? t("common.tooManyRequests")
        : t("blindChat.dailyLimitReached");
    }
    if (e?.response?.status === 403 && detail === "identity verification required") {
      return t("blindChat.verificationRequiredBody");
    }
    return detail ?? e?.message ?? "";
  }

  // Defense-in-depth — ChatListScreen's banner already blocks getting here
  // at all when unverified, but this screen is also reachable directly (e.g.
  // a deep link), so the actual "interact with other profiles" calls below
  // re-check rather than trusting how the screen was reached.
  function requireVerified(): boolean {
    if (profile == null) return true;
    if (!profile.face_verified) {
      showAlert(t("blindChat.verificationRequiredTitle"), t("blindChat.verificationRequiredBody"), [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("blindChat.verificationRequiredCta"),
          onPress: () => navigation.getParent()?.navigate("Profile", { screen: "FaceVerification" } as never),
        },
      ]);
      return false;
    }
    if (calculateProfileCompleteness(profile) < MIN_COMPLETENESS_FOR_ACTIVE) {
      showAlert(t("blindChat.profileIncompleteTitle"), t("blindChat.profileIncompleteBody"), [
        { text: t("common.cancel"), style: "cancel" },
        {
          text: t("blindChat.profileIncompleteCta"),
          onPress: () => navigation.getParent()?.navigate("Profile", { screen: "EditProfile" } as never),
        },
      ]);
      return false;
    }
    return true;
  }

  // The pick wins over the profile's "interested in", but a stray tap
  // shouldn't silently override it — so when they differ, name both and ask.
  function confirmGenderChoice(): Promise<boolean> {
    if (!profile || !gender || gender === profile.interested_in) return Promise.resolve(true);
    return new Promise((resolve) => {
      showAlert(
        t("blindChat.genderConfirmTitle"),
        t("blindChat.genderConfirmBody", {
          profile: t(`profileSetup.${profile.interested_in}`),
          selected: t(`profileSetup.${gender}`),
        }),
        [
          { text: t("blindChat.genderConfirmChange"), style: "cancel", onPress: () => resolve(false) },
          { text: t("blindChat.genderConfirmYes"), onPress: () => resolve(true) },
        ]
      );
    });
  }

  async function handleStart(options?: { confirmed?: boolean }) {
    if (selected.length === 0 || !requireVerified()) return;
    if (!options?.confirmed && !(await confirmGenderChoice())) return;
    setStarting(true);
    // Shown immediately, before the network call resolves — a match that's
    // already waiting can come back instantly, and it still needs to land
    // on the ad-bearing waiting screen rather than skip straight to chat.
    const startedAt = beginWaiting();
    try {
      const result = await joinBlindChatQueue(selected, currentFilters());
      if (result.status === "matched" && result.match_id) {
        revealMatch(result.match_id, startedAt);
      }
    } catch (e: any) {
      if (timeoutTimerRef.current) {
        clearTimeout(timeoutTimerRef.current);
        timeoutTimerRef.current = null;
      }
      setWaiting(false);
      showAlert(t("common.somethingWentWrong"), explainError(e));
    } finally {
      setStarting(false);
    }
  }

  async function handleAiMatch() {
    if (selected.length === 0 || !requireVerified()) return;
    // Credits are also re-checked server-side (402 -> the same alert) since
    // this client-known balance can be stale, but checking it here first
    // saves a round trip for the common "I already know I'm at zero" case.
    if ((profile?.ai_match_credits ?? 0) <= 0) {
      showAlert(t("blindChat.aiMatchTitle"), t("blindChat.aiMatchNoCredits"));
      return;
    }
    if (!(await confirmGenderChoice())) return;
    setAiMatching(true);
    try {
      // Same match-time gender/age/distance as a regular start — the AI match
      // follows what's picked on this screen, not just the profile defaults.
      const result = await requestAiMatch(selected, currentFilters());
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

  async function handleWatchAdForBonus() {
    setClaimingBonus(true);
    try {
      const earned = await showRewardedAd(userId, "blind_chat");
      if (!earned) {
        showAlert(t("blindChat.adBonusTitle"), t("blindChat.adBonusUnavailable"));
        return;
      }
      let limit = await claimBlindChatAdBonus();
      // With server-side ad verification the bonus lands when AdMob's callback
      // reaches the backend (usually 1-3 s after the ad closes), so poll briefly.
      for (let i = 0; i < 6 && limit.bonus_available; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        limit = await getBlindChatLimit();
      }
      await queryClient.invalidateQueries({ queryKey: ["blindChatLimit"] });
      showAlert(
        t("blindChat.adBonusTitle"),
        limit.bonus_available ? t("blindChat.adBonusPending") : t("blindChat.adBonusSuccess")
      );
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), explainError(e));
    } finally {
      setClaimingBonus(false);
    }
  }

  async function handleCancel() {
    if (revealTimerRef.current) {
      clearTimeout(revealTimerRef.current);
      revealTimerRef.current = null;
    }
    if (timeoutTimerRef.current) {
      clearTimeout(timeoutTimerRef.current);
      timeoutTimerRef.current = null;
    }
    setWaiting(false);
    setQueueTimedOut(false);
    try {
      await leaveBlindChatQueue();
    } catch {
      // best-effort — the queue entry is harmless to leave behind briefly
    }
  }

  if (waiting) {
    return (
      <View style={styles.waitingContainer}>
        {queueTimedOut ? (
          <>
            <Ionicons name="hourglass-outline" size={36} color={colors.muted} />
            <Text style={styles.waitingTitle}>{t("blindChat.queueTimeoutTitle")}</Text>
            <Text style={styles.queueTimeoutBody}>{t("blindChat.queueTimeoutBody")}</Text>
            <Pressable style={styles.retryButton} onPress={() => handleStart({ confirmed: true })} disabled={starting}>
              {starting ? <ActivityIndicator color="#fff" /> : <Text style={styles.retryButtonText}>{t("common.tryAgain")}</Text>}
            </Pressable>
          </>
        ) : (
          <>
            <ActivityIndicator size="large" color={colors.accent} />
            <Text style={styles.waitingTitle}>{t("blindChat.waitingTitle")}</Text>
          </>
        )}
        <View style={styles.waitingChips}>
          {selected.map((key) => (
            <View key={key} style={styles.waitingChip}>
              <Text style={styles.waitingChipText}>{t(`blindChatCategories.${key}`)}</Text>
            </View>
          ))}
        </View>
        {!adUnavailable && (
          <View style={styles.waitingAdSlot}>
            <AdCard onUnavailable={() => setAdUnavailable(true)} />
          </View>
        )}
        <Pressable style={styles.cancelButton} onPress={handleCancel}>
          <Text style={styles.cancelButtonText}>{t("common.cancel")}</Text>
        </Pressable>
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.intro}>{t("blindChat.intro")}</Text>

      <View style={styles.liveNoticeCard}>
        <Ionicons name="radio-outline" size={14} color={colors.accentDark} />
        <Text style={styles.liveNoticeText}>{t("blindChat.liveMatchingNotice")}</Text>
      </View>

      {queueStats && (
        <View style={styles.queueStatsCard}>
          <Text style={styles.queueStatsText}>
            {queueStats.total > 0
              ? t("blindChat.queueCountSummary", { count: queueStats.total })
              : t("blindChat.queueCountNone")}
          </Text>
          {otherWaitingCategories.length > 0 && (
            <Text style={styles.queueSuggestText}>
              {t("blindChat.queueSuggestOthers", {
                categories: otherWaitingCategories
                  .map(([key, count]) =>
                    t("blindChat.categoryWaitingCount", { category: t(`blindChatCategories.${key}`), count })
                  )
                  .join(", "),
              })}
            </Text>
          )}
        </View>
      )}

      {limit && !limit.unlimited && (
        <View style={styles.limitRow}>
          <View style={styles.limitBanner}>
            <Ionicons name="flash-outline" size={14} color={colors.accentDark} />
            <Text style={styles.limitBannerText}>{t("blindChat.dailyLimitRemaining", { count: limit.remaining })}</Text>
          </View>
          {limit.bonus_available && (
            <Pressable style={styles.adBonusButton} onPress={handleWatchAdForBonus} disabled={claimingBonus}>
              {claimingBonus ? (
                <ActivityIndicator size="small" color={colors.accentDark} />
              ) : (
                <>
                  <Ionicons name="play-circle" size={14} color={colors.accentDark} />
                  <Text style={styles.adBonusButtonText}>{t("blindChat.watchAdForBonus")}</Text>
                </>
              )}
            </Pressable>
          )}
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
            max={MAX_DISTANCE_KM}
            value={distanceKm}
            formatValue={(v) =>
              v >= MAX_DISTANCE_KM
                ? t("filters.distanceNoLimit")
                : useImperial
                  ? t("filters.distanceUpToMi", { mi: formatDistanceKm(v) })
                  : t("filters.distanceUpToKm", { km: v })
            }
            onChange={setDistanceKm}
          />
        )}
      </View>

      <Pressable
        style={[styles.startButton, selected.length === 0 && styles.startButtonDisabled]}
        onPress={() => handleStart()}
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
      {profile && <Text style={styles.aiMatchCreditsText}>{t("profile.aiMatchCredits", { count: profile.ai_match_credits })}</Text>}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, gap: 8 },
  intro: { fontSize: 14, color: colors.muted, lineHeight: 20, marginBottom: 8 },
  liveNoticeCard: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 6,
    backgroundColor: colors.accentSoft,
    borderRadius: 10,
    paddingVertical: 9,
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  liveNoticeText: { flex: 1, fontSize: 12, color: colors.accentDark, lineHeight: 17 },
  queueStatsCard: {
    backgroundColor: colors.creamDeep,
    borderRadius: 10,
    paddingVertical: 9,
    paddingHorizontal: 12,
    marginBottom: 8,
    gap: 4,
  },
  queueStatsText: { fontSize: 12.5, color: colors.navy, fontWeight: "600" },
  queueSuggestText: { fontSize: 12, color: colors.muted, lineHeight: 16 },
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
  limitRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 8 },
  adBonusButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    backgroundColor: colors.accentSoft,
    borderRadius: 10,
    paddingVertical: 8,
    paddingHorizontal: 12,
    alignSelf: "flex-start",
  },
  adBonusButtonText: { fontSize: 12.5, color: colors.accentDark, fontWeight: "700" },
  // Matches the white-bordered `card` pattern used everywhere else
  // (EditProfileScreen/ProfileSetupScreen) — this used to be a flat
  // colors.creamDeep block with no border, which read as visually
  // inconsistent with the rest of the app.
  filtersCard: {
    marginTop: 16,
    padding: 16,
    borderRadius: 16,
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
  },
  filtersTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginBottom: 4 },
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
  aiMatchCreditsText: { fontSize: 12.5, color: colors.muted, textAlign: "center", marginTop: 8 },
  waitingContainer: { flex: 1, alignItems: "center", justifyContent: "center", padding: 32, gap: 16 },
  waitingTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, textAlign: "center" },
  queueTimeoutBody: { fontSize: 13.5, color: colors.muted, textAlign: "center", lineHeight: 19, marginTop: -8 },
  retryButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 13, paddingHorizontal: 32, alignItems: "center" },
  retryButtonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  waitingChips: { flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "center" },
  waitingChip: { backgroundColor: colors.creamDeep, borderRadius: 20, paddingVertical: 6, paddingHorizontal: 14 },
  waitingChipText: { fontSize: 13, color: colors.ink, fontWeight: "600" },
  waitingAdSlot: { width: "100%", height: 220, marginTop: 8 },
  cancelButton: { marginTop: 12, paddingVertical: 12, paddingHorizontal: 28, borderRadius: 12, backgroundColor: colors.creamDeep },
  cancelButtonText: { color: colors.muted, fontWeight: "700" },
});
