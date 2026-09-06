import { useRef, useState } from "react";
import { ActivityIndicator, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { useTranslation } from "react-i18next";

import ProfileCard from "../../components/ProfileCard";
import AdCard from "../../components/AdCard";
import ActionButtons from "../../components/ActionButtons";
import FilterModal from "../../components/FilterModal";
import MatchCelebrationModal from "../matches/MatchCelebrationModal";
import { useCandidates } from "../../hooks/useCandidates";
import { useSwipeAction } from "../../hooks/useSwipeAction";
import { useSwipeLimit } from "../../hooks/useSwipeLimit";
import type { SwipeAction } from "../../api/interactions";
import { colors } from "../../theme";

// A sponsored card takes the place of the next real candidate every 5
// swipes — same cadence Tinder/Bumble/Hinge use for in-deck ad cards.
const SWIPES_PER_AD = 5;

function formatCountdown(resetsAt: string): string {
  const ms = new Date(resetsAt).getTime() - Date.now();
  if (ms <= 0) return "0:00";
  const totalMinutes = Math.ceil(ms / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

export default function SwipeScreen() {
  const { t } = useTranslation();
  const { data: candidates, isLoading, isError } = useCandidates();
  const { data: swipeLimit } = useSwipeLimit();
  const swipeMutation = useSwipeAction();
  const navigation = useNavigation<any>();

  const swipeCountRef = useRef(0);
  const [showAd, setShowAd] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  const [matchInfo, setMatchInfo] = useState<{
    matchId: string;
    otherUserId: string;
    otherDisplayName: string;
    otherPhotoUrl: string | null;
  } | null>(null);

  const current = candidates?.[0];
  const limitReached = swipeLimit?.remaining === 0;

  function handleAction(action: SwipeAction) {
    if (!current || swipeMutation.isPending || limitReached) return;
    swipeMutation.mutate(
      { action, candidate: current },
      {
        onSuccess: (result) => {
          swipeCountRef.current += 1;
          if (swipeCountRef.current % SWIPES_PER_AD === 0) setShowAd(true);
          if (result.matched && result.match_id) {
            setMatchInfo({
              matchId: result.match_id,
              otherUserId: current.user_id,
              otherDisplayName: current.display_name,
              otherPhotoUrl: current.photos.find((p) => p.media_type === "photo")?.url ?? null,
            });
          }
        },
      }
    );
  }

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  if (isError) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>{t("discover.loadError")}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.topBar}>
        <Pressable style={styles.filterPill} onPress={() => setShowFilters(true)}>
          <Ionicons name="options-outline" size={16} color={colors.navy} />
          <Text style={styles.filterPillText}>{t("filters.title")}</Text>
        </Pressable>
        {swipeLimit && (
          <Text style={styles.limitText}>
            {limitReached
              ? t("swipe.limitReached", { time: formatCountdown(swipeLimit.resets_at!) })
              : t("swipe.remaining", { count: swipeLimit.remaining, limit: swipeLimit.limit })}
          </Text>
        )}
      </View>

      <View style={styles.cardArea}>
        {showAd ? (
          <AdCard onUnavailable={() => setShowAd(false)} />
        ) : current ? (
          <ProfileCard key={current.user_id} candidate={current} />
        ) : (
          <View style={styles.centered}>
            <Text style={styles.emptyText}>
              {limitReached ? t("swipe.limitReachedEmpty") : t("discover.empty")}
            </Text>
          </View>
        )}
      </View>

      {showAd ? (
        <Pressable style={styles.continueButton} onPress={() => setShowAd(false)}>
          <Text style={styles.continueButtonText}>{t("swipe.continue")}</Text>
        </Pressable>
      ) : (
        <ActionButtons
          onPass={() => handleAction("pass")}
          onLike={() => handleAction("like")}
          onSuperLike={() => handleAction("superlike")}
          disabled={!current || swipeMutation.isPending || limitReached}
        />
      )}

      <MatchCelebrationModal
        visible={matchInfo !== null}
        otherDisplayName={matchInfo?.otherDisplayName ?? null}
        otherPhotoUrl={matchInfo?.otherPhotoUrl}
        onKeepBrowsing={() => setMatchInfo(null)}
        onSendMessage={() => {
          if (!matchInfo) return;
          const { matchId, otherUserId, otherDisplayName } = matchInfo;
          setMatchInfo(null);
          navigation.navigate("Chat", {
            screen: "ChatRoom",
            params: { matchId, otherUserId, otherDisplayName },
          });
        }}
      />

      <FilterModal visible={showFilters} onClose={() => setShowFilters(false)} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 4,
  },
  filterPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingVertical: 7,
    paddingHorizontal: 14,
  },
  filterPillText: { fontSize: 13, fontWeight: "700", color: colors.navy },
  limitText: { fontSize: 13, fontWeight: "600", color: colors.muted },
  cardArea: { flex: 1, padding: 16 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  emptyText: { color: colors.muted, textAlign: "center" },
  continueButton: {
    marginHorizontal: 16,
    marginBottom: 18,
    backgroundColor: colors.accent,
    borderRadius: 999,
    paddingVertical: 16,
    alignItems: "center",
  },
  continueButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
