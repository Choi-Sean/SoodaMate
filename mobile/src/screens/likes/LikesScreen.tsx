import { useState } from "react";
import { ActivityIndicator, FlatList, Image, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useNavigation } from "@react-navigation/native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import ProfileCard from "../../components/ProfileCard";
import ActionButtons from "../../components/ActionButtons";
import ScreenHeader from "../../components/ScreenHeader";
import MatchCelebrationModal from "../matches/MatchCelebrationModal";
import { useLikedMe } from "../../hooks/useLikedMe";
import { useSwipeAction } from "../../hooks/useSwipeAction";
import { getMyProfile } from "../../api/profiles";
import { openShop } from "../../utils/openShop";
import type { SwipeAction } from "../../api/interactions";
import type { Candidate } from "../../types";
import { colors } from "../../theme";

/** People who already liked/superliked the viewer — tap a tile to see the
 * full profile and like back (instant match) or pass. Seeing WHO liked you
 * (not just that you have likes) is the premium hook every dating app uses
 * this screen for, so every tile is blurred-and-locked behind
 * is_premium_member; only the count and the superlike star still show
 * through as the enticing bit. */
export default function LikesScreen() {
  const { t } = useTranslation();
  const { data: candidates, isLoading, isError } = useLikedMe();
  const { data: myProfile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const isPremium = myProfile?.is_premium_member ?? false;
  const swipeMutation = useSwipeAction();
  const navigation = useNavigation<any>();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Candidate | null>(null);
  const [matchInfo, setMatchInfo] = useState<{
    matchId: string;
    otherUserId: string;
    otherDisplayName: string;
    otherPhotoUrl: string | null;
  } | null>(null);

  const handleOpenShop = () => openShop(queryClient);

  function handleAction(candidate: Candidate, action: SwipeAction) {
    if (swipeMutation.isPending) return;
    swipeMutation.mutate(
      { action, candidate },
      {
        onSuccess: (result) => {
          setSelected(null);
          if (result.matched && result.match_id) {
            setMatchInfo({
              matchId: result.match_id,
              otherUserId: candidate.user_id,
              otherDisplayName: candidate.display_name,
              otherPhotoUrl: candidate.photos.find((p) => p.media_type === "photo")?.url ?? null,
            });
          }
        },
      }
    );
  }

  const renderItem = ({ item }: { item: Candidate }) => {
    const photo = item.photos[0];
    if (!isPremium) {
      // Locked: still shows a photo (dimmed, under a frosted overlay) and
      // the superlike star as the enticing hint that there's someone real
      // behind it, but no name/age and no tap-through to the profile —
      // that identity reveal is exactly what premium is selling here.
      return (
        <Pressable style={styles.tile} onPress={handleOpenShop}>
          {photo ? (
            <Image source={{ uri: photo.url }} style={[styles.tileImage, styles.tileImageLocked]} blurRadius={18} />
          ) : (
            <View style={[styles.tileImage, styles.tilePlaceholder]} />
          )}
          <View style={styles.lockOverlay} />
          {item.superliked_me && (
            <View style={styles.tileSuperlike}>
              <Ionicons name="star" size={11} color="#fff" />
            </View>
          )}
          <View style={styles.lockBadge}>
            <Ionicons name="lock-closed" size={20} color="#fff" />
          </View>
        </Pressable>
      );
    }
    return (
      <Pressable style={styles.tile} onPress={() => setSelected(item)}>
        {photo && photo.media_type === "video" ? (
          <View style={[styles.tileImage, styles.tileVideoPlaceholder]}>
            <Ionicons name="play-circle" size={40} color="#fff" />
          </View>
        ) : photo ? (
          <Image source={{ uri: photo.url }} style={styles.tileImage} />
        ) : (
          <View style={[styles.tileImage, styles.tilePlaceholder]}>
            <Ionicons name="person" size={32} color={colors.border} />
          </View>
        )}
        <LinearGradient colors={["transparent", "rgba(11,41,68,0.88)"]} style={styles.tileGradient} />
        {item.superliked_me && (
          <View style={styles.tileSuperlike}>
            <Ionicons name="star" size={11} color="#fff" />
          </View>
        )}
        <View style={styles.tileTextWrap}>
          <Text style={styles.tileName} numberOfLines={1}>
            {item.display_name}, {item.age}
          </Text>
        </View>
        <Pressable
          style={styles.likeBackButton}
          onPress={(e) => {
            e.stopPropagation();
            handleAction(item, "like");
          }}
          disabled={swipeMutation.isPending}
        >
          <Ionicons name="heart" size={18} color="#fff" />
        </Pressable>
      </Pressable>
    );
  };

  return (
    <View style={styles.container}>
      <ScreenHeader title={t("likes.title")} />
      {!isPremium && candidates && candidates.length > 0 && (
        <View style={styles.lockedBanner}>
          <Ionicons name="lock-closed" size={14} color={colors.accentDark} />
          <Text style={styles.lockedBannerText}>{t("likes.premiumHint", { count: candidates.length })}</Text>
        </View>
      )}
      {isLoading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      ) : isError ? (
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{t("likes.loadError")}</Text>
        </View>
      ) : !candidates || candidates.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{t("likes.empty")}</Text>
        </View>
      ) : (
        <FlatList
          data={candidates}
          keyExtractor={(c) => c.user_id}
          renderItem={renderItem}
          numColumns={2}
          contentContainerStyle={styles.grid}
          columnWrapperStyle={styles.gridRow}
        />
      )}

      <Modal visible={selected !== null} animationType="slide" onRequestClose={() => setSelected(null)}>
        <View style={styles.detailContainer}>
          {selected && (
            <>
              <View style={styles.detailCardWrap}>
                <ProfileCard key={selected.user_id} candidate={selected} />
              </View>
              <ActionButtons
                onPass={() => handleAction(selected, "pass")}
                onLike={() => handleAction(selected, "like")}
                onSuperLike={() => handleAction(selected, "superlike")}
                disabled={swipeMutation.isPending}
              />
            </>
          )}
          <Pressable style={styles.closeButton} onPress={() => setSelected(null)}>
            <Ionicons name="close" size={26} color="#fff" />
          </Pressable>
        </View>
      </Modal>

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
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  lockedBanner: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginHorizontal: 16,
    marginBottom: 10,
    backgroundColor: colors.creamDeep,
    borderRadius: 12,
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  lockedBannerText: { fontSize: 12.5, color: colors.accentDark, fontWeight: "700", flexShrink: 1 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  emptyText: { color: colors.muted, textAlign: "center" },
  grid: { paddingHorizontal: 12, paddingBottom: 16, gap: 12 },
  gridRow: { gap: 12 },
  tile: {
    flex: 1,
    aspectRatio: 0.72,
    borderRadius: 18,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
    shadowColor: "#000",
    shadowOpacity: 0.12,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 4 },
    elevation: 3,
  },
  tileImage: { width: "100%", height: "100%" },
  tileImageLocked: { opacity: 0.7 },
  lockOverlay: { position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: "rgba(11,41,68,0.28)" },
  lockBadge: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  tilePlaceholder: { alignItems: "center", justifyContent: "center" },
  tileVideoPlaceholder: { backgroundColor: colors.navy, alignItems: "center", justifyContent: "center" },
  tileGradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "45%" },
  tileSuperlike: {
    position: "absolute",
    top: 8,
    left: 8,
    backgroundColor: "#3B82F6",
    borderRadius: 12,
    padding: 5,
  },
  tileTextWrap: { position: "absolute", bottom: 10, left: 10, right: 44 },
  tileName: { color: "#fff", fontSize: 14, fontWeight: "700" },
  likeBackButton: {
    position: "absolute",
    bottom: 8,
    right: 8,
    backgroundColor: colors.accent,
    borderRadius: 16,
    width: 32,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOpacity: 0.25,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 2 },
    elevation: 3,
  },
  detailContainer: { flex: 1, backgroundColor: colors.navyDeep },
  detailCardWrap: { flex: 1, padding: 16, paddingTop: 56 },
  closeButton: {
    position: "absolute",
    top: 56,
    right: 20,
    backgroundColor: "rgba(0,0,0,0.4)",
    borderRadius: 20,
    padding: 8,
  },
});
