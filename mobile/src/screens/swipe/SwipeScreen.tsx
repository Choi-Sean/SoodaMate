import { useRef, useState } from "react";
import { ActivityIndicator, Image, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useNavigation } from "@react-navigation/native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFonts, Fredoka_600SemiBold } from "@expo-google-fonts/fredoka";
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
  const insets = useSafeAreaInsets();
  // Only the brand wordmark below uses this — falls back to the system
  // bold font until it loads, so nothing else on this screen waits on it.
  const [brandFontLoaded] = useFonts({ Fredoka_600SemiBold });
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

  return (
    <View style={styles.container}>
      {/* Swipe doubles as the app's home screen, so it shows the brand
       * wordmark here instead of a section label like every other tab's
       * ScreenHeader — same pattern Bumble/Hinge/Tinder use on their own
       * primary tab. */}
      <View style={[styles.brandBar, { paddingTop: insets.top + 10 }]}>
        <View style={styles.brandRow}>
          <Image source={require("../../../assets/icon.png")} style={styles.logo} />
          <Text style={[styles.brandTitle, brandFontLoaded && styles.brandTitleFredoka]}>SooDaMate</Text>
        </View>
        <Pressable style={styles.filterIconButton} onPress={() => setShowFilters(true)} hitSlop={6}>
          <Ionicons name="options-outline" size={20} color={colors.navy} />
        </Pressable>
      </View>
      {swipeLimit && (
        <Text style={styles.limitText}>
          {swipeLimit.unlimited
            ? t("swipe.unlimited")
            : limitReached
              ? t("swipe.limitReached", { time: formatCountdown(swipeLimit.resets_at!) })
              : t("swipe.remaining", { count: swipeLimit.remaining, limit: swipeLimit.limit })}
        </Text>
      )}

      <View style={styles.cardArea}>
        {isLoading ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={colors.accent} />
          </View>
        ) : isError ? (
          <View style={styles.centered}>
            <Text style={styles.emptyText}>{t("discover.loadError")}</Text>
          </View>
        ) : showAd ? (
          <AdCard onUnavailable={() => setShowAd(false)} />
        ) : current ? (
          <ProfileCard key={current.user_id} candidate={current} flush />
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
  container: { flex: 1, backgroundColor: colors.cream },
  brandBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingBottom: 6,
  },
  brandRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  logo: { width: 30, height: 30, borderRadius: 8 },
  brandTitle: { fontSize: 22, fontWeight: "800", color: colors.navy },
  brandTitleFredoka: { fontFamily: "Fredoka_600SemiBold", fontWeight: "normal" },
  filterIconButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.white,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: colors.navyDeep,
    shadowOpacity: 0.08,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  limitText: { fontSize: 12.5, fontWeight: "600", color: colors.muted, paddingHorizontal: 20, paddingBottom: 6 },
  cardArea: { flex: 1, padding: 0 },
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
