import { ActivityIndicator, FlatList, Image, Pressable, Text, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { confirmCoupleStory, declineCoupleStory, getMyCoupleStories } from "../../api/coupleStories";
import { showAlert } from "../../utils/alert";
import { useAuthStore } from "../../store/authStore";
import type { CoupleStory } from "../../types";
import { colors } from "../../theme";

const STATUS_KEY: Record<CoupleStory["status"], string> = {
  pending: "coupleStory.statusPending",
  published: "coupleStory.statusPublished",
  declined: "coupleStory.statusDeclined",
  hidden: "coupleStory.statusHidden",
};

/** Every story the viewer is party to (author or peer), any status — the
 * one place a pending confirm/decline actually happens (see routers/
 * couple_stories.py — a story never goes public without the peer's
 * explicit confirm here). */
export default function MyCoupleStoriesScreen() {
  const { t } = useTranslation();
  const userId = useAuthStore((s) => s.userId);
  const queryClient = useQueryClient();
  const { data: stories, isLoading } = useQuery({
    queryKey: ["myCoupleStories"],
    queryFn: getMyCoupleStories,
  });

  async function handleConfirm(story: CoupleStory) {
    try {
      await confirmCoupleStory(story.id);
      await queryClient.invalidateQueries({ queryKey: ["myCoupleStories"] });
      await queryClient.invalidateQueries({ queryKey: ["coupleStoriesFeed"] });
    } catch {
      showAlert(t("common.somethingWentWrong"), t("coupleStory.errorGeneric"));
    }
  }

  function confirmDecline(story: CoupleStory) {
    showAlert(t("coupleStory.declineConfirmTitle"), t("coupleStory.declineConfirmBody"), [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("coupleStory.decline"),
        style: "destructive",
        onPress: async () => {
          try {
            await declineCoupleStory(story.id);
            await queryClient.invalidateQueries({ queryKey: ["myCoupleStories"] });
          } catch {
            showAlert(t("common.somethingWentWrong"), t("coupleStory.errorGeneric"));
          }
        },
      },
    ]);
  }

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <FlatList
      data={stories}
      keyExtractor={(s) => s.id}
      contentContainerStyle={styles.list}
      ListEmptyComponent={
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{t("coupleStory.myStoriesEmpty")}</Text>
        </View>
      }
      renderItem={({ item }) => {
        const isPeer = item.peer_id === userId;
        const needsMyAction = isPeer && item.status === "pending";
        const otherName = isPeer ? item.author_display_name : item.peer_display_name;
        return (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <Text style={styles.names}>
                {item.author_display_name} 💕 {item.peer_display_name}
              </Text>
              <View style={styles.statusPill}>
                <Text style={styles.statusPillText}>{t(STATUS_KEY[item.status])}</Text>
              </View>
            </View>
            {item.photo_url && <Image source={{ uri: item.photo_url }} style={styles.photo} />}
            <Text style={styles.storyText}>{item.story_text}</Text>
            {needsMyAction && (
              <>
                <Text style={styles.pendingNotice}>{t("coupleStory.pendingYourAction", { name: otherName })}</Text>
                <View style={styles.actionRow}>
                  <Pressable style={styles.declineButton} onPress={() => confirmDecline(item)}>
                    <Text style={styles.declineButtonText}>{t("coupleStory.decline")}</Text>
                  </Pressable>
                  <Pressable style={styles.confirmButton} onPress={() => handleConfirm(item)}>
                    <Text style={styles.confirmButtonText}>{t("coupleStory.confirm")}</Text>
                  </Pressable>
                </View>
              </>
            )}
          </View>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 60, paddingHorizontal: 30 },
  emptyText: { color: colors.muted, textAlign: "center", fontSize: 14, lineHeight: 20 },
  list: { padding: 16, gap: 14, flexGrow: 1 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 10,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  names: { fontSize: 15, fontWeight: "800", color: colors.navy, flexShrink: 1 },
  statusPill: { backgroundColor: colors.creamDeep, borderRadius: 20, paddingVertical: 4, paddingHorizontal: 10 },
  statusPillText: { fontSize: 11, fontWeight: "700", color: colors.accentDark },
  photo: { width: "100%", aspectRatio: 4 / 3, borderRadius: 12, backgroundColor: colors.creamDeep },
  storyText: { fontSize: 14, color: colors.ink, lineHeight: 20 },
  pendingNotice: { fontSize: 12.5, color: colors.accentDark, fontWeight: "600" },
  actionRow: { flexDirection: "row", gap: 10 },
  declineButton: { flex: 1, paddingVertical: 11, borderRadius: 10, alignItems: "center", backgroundColor: colors.creamDeep },
  declineButtonText: { color: colors.muted, fontWeight: "700", fontSize: 13.5 },
  confirmButton: { flex: 1, paddingVertical: 11, borderRadius: 10, alignItems: "center", backgroundColor: colors.accent },
  confirmButtonText: { color: "#fff", fontWeight: "700", fontSize: 13.5 },
});
