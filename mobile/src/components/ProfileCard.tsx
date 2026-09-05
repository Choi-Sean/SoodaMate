import { Image, Text, View, StyleSheet } from "react-native";
import { useTranslation } from "react-i18next";

import type { Candidate } from "../types";
import { colors } from "../theme";

interface Props {
  candidate: Candidate;
}

export default function ProfileCard({ candidate }: Props) {
  const { t } = useTranslation();
  const photo = candidate.photos[0];

  return (
    <View style={styles.card}>
      {photo ? (
        <Image source={{ uri: photo.url }} style={styles.image} />
      ) : (
        <View style={[styles.image, styles.imagePlaceholder]} />
      )}

      {candidate.superliked_me && (
        <View style={styles.superlikeBadge}>
          <Text style={styles.superlikeBadgeText}>{t("discover.superlikedYou")}</Text>
        </View>
      )}

      <View style={styles.infoOverlay}>
        <Text style={styles.name}>
          {candidate.display_name}, {candidate.age}
        </Text>
        {candidate.distance_km != null && (
          <Text style={styles.distance}>{t("discover.kmAway", { km: Math.round(candidate.distance_km) })}</Text>
        )}
        {candidate.bio && (
          <Text style={styles.bio} numberOfLines={3}>
            {candidate.bio}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 16,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
  },
  image: { width: "100%", height: "100%" },
  imagePlaceholder: { backgroundColor: colors.border },
  superlikeBadge: {
    position: "absolute",
    top: 16,
    right: 16,
    backgroundColor: "#3B82F6",
    borderRadius: 20,
    paddingVertical: 6,
    paddingHorizontal: 12,
  },
  superlikeBadgeText: { color: "#fff", fontWeight: "700", fontSize: 12 },
  infoOverlay: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    padding: 16,
    backgroundColor: "rgba(11,59,99,0.55)",
  },
  name: { color: "#fff", fontSize: 22, fontWeight: "700" },
  distance: { color: "#f0e8e0", fontSize: 13, marginTop: 2 },
  bio: { color: "#fff", fontSize: 14, marginTop: 6 },
});
