import { useState } from "react";
import { ActivityIndicator, Text, View, StyleSheet } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTranslation } from "react-i18next";

import ProfileCard from "../../components/ProfileCard";
import ActionButtons from "../../components/ActionButtons";
import AdSlot from "../../components/AdSlot";
import MatchCelebrationModal from "../matches/MatchCelebrationModal";
import { useCandidates } from "../../hooks/useCandidates";
import { useSwipeAction } from "../../hooks/useSwipeAction";
import type { SwipeAction } from "../../api/interactions";
import { colors } from "../../theme";

export default function DiscoverScreen() {
  const { t } = useTranslation();
  const { data: candidates, isLoading, isError } = useCandidates();
  const swipeMutation = useSwipeAction();
  const navigation = useNavigation<any>();

  const [matchInfo, setMatchInfo] = useState<{
    matchId: string;
    otherUserId: string;
    otherDisplayName: string;
  } | null>(null);

  const current = candidates?.[0];

  function handleAction(action: SwipeAction) {
    if (!current || swipeMutation.isPending) return;
    swipeMutation.mutate(
      { action, candidate: current },
      {
        onSuccess: (result) => {
          if (result.matched && result.match_id) {
            setMatchInfo({
              matchId: result.match_id,
              otherUserId: current.user_id,
              otherDisplayName: current.display_name,
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
      <View style={styles.cardArea}>
        {current ? (
          <ProfileCard candidate={current} />
        ) : (
          <View style={styles.centered}>
            <Text style={styles.emptyText}>{t("discover.empty")}</Text>
          </View>
        )}
      </View>

      <ActionButtons
        onPass={() => handleAction("pass")}
        onLike={() => handleAction("like")}
        onSuperLike={() => handleAction("superlike")}
        disabled={!current || swipeMutation.isPending}
      />

      <AdSlot />

      <MatchCelebrationModal
        visible={matchInfo !== null}
        otherDisplayName={matchInfo?.otherDisplayName ?? null}
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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  cardArea: { flex: 1, padding: 16 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  emptyText: { color: colors.muted, textAlign: "center" },
});
