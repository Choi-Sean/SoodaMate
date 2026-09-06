import { useState } from "react";
import { ActivityIndicator, FlatList, Image, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";

import ProfileCard from "../../components/ProfileCard";
import { useRecommended } from "../../hooks/useRecommended";
import type { Candidate } from "../../types";
import { colors } from "../../theme";

/** Pure browsing — nearby people matching the viewer's preferences, no
 * like/pass actions. The interactive deck lives on the Swipe tab; this is
 * a lightweight recommendation feed you can look through and tap into. */
export default function DiscoverScreen() {
  const { t } = useTranslation();
  const { data: candidates, isLoading, isError } = useRecommended();
  const [selected, setSelected] = useState<Candidate | null>(null);

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

  const renderItem = ({ item }: { item: Candidate }) => {
    const photo = item.photos[0];
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
          {item.distance_km != null && (
            <Text style={styles.tileDistance}>{t("discover.kmAway", { km: Math.round(item.distance_km) })}</Text>
          )}
        </View>
      </Pressable>
    );
  };

  return (
    <View style={styles.container}>
      <Text style={styles.header}>{t("discover.title")}</Text>
      {!candidates || candidates.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{t("discover.empty")}</Text>
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
            <View style={styles.detailCardWrap}>
              <ProfileCard candidate={selected} />
            </View>
          )}
          <Pressable style={styles.closeButton} onPress={() => setSelected(null)}>
            <Ionicons name="close" size={26} color="#fff" />
          </Pressable>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  header: { fontSize: 24, fontWeight: "800", padding: 16, paddingTop: 48, color: colors.navy },
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
  tilePlaceholder: { alignItems: "center", justifyContent: "center" },
  tileVideoPlaceholder: { backgroundColor: colors.navy, alignItems: "center", justifyContent: "center" },
  tileGradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "45%" },
  tileSuperlike: {
    position: "absolute",
    top: 8,
    right: 8,
    backgroundColor: "#3B82F6",
    borderRadius: 12,
    padding: 5,
  },
  tileTextWrap: { position: "absolute", bottom: 10, left: 10, right: 10 },
  tileName: { color: "#fff", fontSize: 14, fontWeight: "700" },
  tileDistance: { color: colors.accentSoft, fontSize: 11, marginTop: 1 },
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
