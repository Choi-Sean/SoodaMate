import { Image, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
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
        <View style={[styles.image, styles.imagePlaceholder]}>
          <Ionicons name="person" size={72} color={colors.border} />
        </View>
      )}

      {/* Tinder/Bumble/Hinge-style bottom fade so white text stays readable
       * over any photo without a flat color band cutting the image off. */}
      <LinearGradient
        colors={["transparent", "rgba(11,41,68,0.15)", "rgba(11,41,68,0.92)"]}
        locations={[0, 0.5, 1]}
        style={styles.gradient}
      />

      {candidate.superliked_me && (
        <View style={styles.superlikeBadge}>
          <Ionicons name="star" size={14} color="#fff" />
          <Text style={styles.superlikeBadgeText}>{t("discover.superlikedYou")}</Text>
        </View>
      )}

      <View style={styles.infoOverlay}>
        <View style={styles.nameRow}>
          <Text style={styles.name} numberOfLines={1}>
            {candidate.display_name}
          </Text>
          <Text style={styles.age}>{candidate.age}</Text>
        </View>
        {candidate.distance_km != null && (
          <View style={styles.distanceRow}>
            <Ionicons name="location-sharp" size={13} color={colors.accentSoft} />
            <Text style={styles.distance}>{t("discover.kmAway", { km: Math.round(candidate.distance_km) })}</Text>
          </View>
        )}
        {candidate.bio && (
          <Text style={styles.bio} numberOfLines={2}>
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
    borderRadius: 24,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  image: { width: "100%", height: "100%" },
  imagePlaceholder: { backgroundColor: colors.creamDeep, alignItems: "center", justifyContent: "center" },
  gradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "55%" },
  superlikeBadge: {
    position: "absolute",
    top: 18,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#3B82F6",
    borderRadius: 20,
    paddingVertical: 7,
    paddingHorizontal: 14,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
    elevation: 4,
  },
  superlikeBadgeText: { color: "#fff", fontWeight: "700", fontSize: 12 },
  infoOverlay: { position: "absolute", bottom: 0, left: 0, right: 0, padding: 20 },
  nameRow: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  name: { color: "#fff", fontSize: 26, fontWeight: "800", flexShrink: 1 },
  age: { color: "#fff", fontSize: 22, fontWeight: "400" },
  distanceRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  distance: { color: colors.accentSoft, fontSize: 13, fontWeight: "500" },
  bio: { color: "rgba(255,255,255,0.92)", fontSize: 14, marginTop: 8, lineHeight: 19 },
});
