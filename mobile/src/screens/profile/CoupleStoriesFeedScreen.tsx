import { ActivityIndicator, FlatList, Image, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { getCoupleStoriesFeed, reportCoupleStory } from "../../api/coupleStories";
import { showAlert } from "../../utils/alert";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import type { CoupleStory } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "CoupleStoriesFeed">;

function StoryCard({ story }: { story: CoupleStory }) {
  const { t, i18n } = useTranslation();

  function openMenu() {
    // "Options" — reuses chat.menuTitle (same generic label) rather than
    // duplicating a coupleStory-namespaced copy across all 5 locale files.
    showAlert(t("chat.menuTitle"), undefined, [
      { text: t("coupleStory.report"), style: "destructive", onPress: confirmReport },
      { text: t("common.cancel"), style: "cancel" },
    ]);
  }

  function confirmReport() {
    showAlert(t("coupleStory.reportConfirmTitle"), undefined, [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("coupleStory.report"),
        style: "destructive",
        onPress: async () => {
          try {
            await reportCoupleStory(story.id, "inappropriate_content");
            showAlert(t("coupleStory.report"), t("coupleStory.reportSuccess"));
          } catch {
            showAlert(t("common.somethingWentWrong"), t("coupleStory.errorGeneric"));
          }
        },
      },
    ]);
  }

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.names}>
          {story.author_display_name} 💕 {story.peer_display_name}
        </Text>
        <Pressable onPress={openMenu} hitSlop={10}>
          <Ionicons name="ellipsis-horizontal" size={18} color={colors.muted} />
        </Pressable>
      </View>
      {story.photo_url && <Image source={{ uri: story.photo_url }} style={styles.photo} />}
      <Text style={styles.storyText}>{story.story_text}</Text>
      {story.published_at && (
        // published_at is a full ISO datetime (not a plain YYYY-MM-DD date),
        // so this uses the same inline toLocaleDateString ChatListScreen
        // already uses for matched_at — utils/age.ts's formatDate is
        // date-only (it appends "T00:00:00" itself) and would double up
        // the time component here, producing "Invalid Date".
        <Text style={styles.date}>
          {t("coupleStory.publishedOn", { date: new Date(story.published_at).toLocaleDateString(i18n.language) })}
        </Text>
      )}
    </View>
  );
}

/** Public community feed — published stories only (server-side filtered;
 * see routers/couple_stories.py::feed). "My stories" (the button in the
 * header) is where a pending confirm/decline actually happens. */
export default function CoupleStoriesFeedScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const { data: stories, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: ["coupleStoriesFeed"],
    queryFn: () => getCoupleStoriesFeed(),
  });

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Pressable style={styles.myStoriesButton} onPress={() => navigation.navigate("MyCoupleStories")}>
          <Text style={styles.myStoriesButtonText}>{t("coupleStory.myStoriesButton")}</Text>
        </Pressable>
      </View>

      {isLoading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      ) : isError ? (
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{t("coupleStory.loadError")}</Text>
        </View>
      ) : (
        <FlatList
          data={stories}
          keyExtractor={(s) => s.id}
          renderItem={({ item }) => <StoryCard story={item} />}
          contentContainerStyle={styles.list}
          refreshing={isFetching}
          onRefresh={refetch}
          ListEmptyComponent={
            <View style={styles.centered}>
              <Text style={styles.emptyText}>{t("coupleStory.feedEmpty")}</Text>
            </View>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  headerRow: { flexDirection: "row", justifyContent: "flex-end", paddingHorizontal: 16, paddingTop: 12 },
  myStoriesButton: { paddingVertical: 8, paddingHorizontal: 14, borderRadius: 20, backgroundColor: colors.creamDeep },
  myStoriesButtonText: { color: colors.accentDark, fontWeight: "700", fontSize: 13 },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 60, paddingHorizontal: 30 },
  emptyText: { color: colors.muted, textAlign: "center", fontSize: 14, lineHeight: 20 },
  list: { padding: 16, gap: 14 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: colors.border,
    gap: 10,
  },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  names: { fontSize: 15, fontWeight: "800", color: colors.navy },
  photo: { width: "100%", aspectRatio: 4 / 3, borderRadius: 12, backgroundColor: colors.creamDeep },
  storyText: { fontSize: 14, color: colors.ink, lineHeight: 20 },
  date: { fontSize: 11, color: colors.muted },
});
