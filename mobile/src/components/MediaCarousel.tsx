import { useEffect, useState } from "react";
import { Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";

import ProfileMedia from "./ProfileMedia";
import type { Photo } from "../types";
import { colors } from "../theme";

const GENDER_ICON: Record<string, keyof typeof Ionicons.glyphMap> = {
  male: "male",
  female: "female",
  other: "male-female",
};

interface Props {
  media: Photo[];
  displayName: string;
  age: number;
  gender: string;
  distanceKm: number | null;
  superlikedMe: boolean;
  verifiedBadge: "work" | "school" | null;
}

/** Tinder-style tap-to-advance carousel (left third = previous, right two
 * thirds = next) with Bumble-style dot indicators and a bottom name/age/
 * gender overlay. Resets to the first item whenever the candidate changes
 * (parent passes a `key={candidate.user_id}` so this remounts). */
export default function MediaCarousel({
  media,
  displayName,
  age,
  gender,
  distanceKm,
  superlikedMe,
  verifiedBadge,
}: Props) {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const current = media[index];

  // Guards against an out-of-range index if a candidate somehow has fewer
  // media items than the previous one had (shouldn't happen with the
  // remount-on-candidate-change key, but cheap to be safe).
  useEffect(() => {
    if (index >= media.length && media.length > 0) setIndex(0);
  }, [media.length, index]);

  return (
    <View style={styles.container}>
      {current ? (
        <ProfileMedia media={current} style={styles.media} />
      ) : (
        <View style={[styles.media, styles.placeholder]}>
          <Ionicons name="person" size={72} color={colors.border} />
        </View>
      )}

      {media.length > 1 && (
        <>
          <Pressable
            style={styles.tapLeft}
            onPress={() => setIndex((i) => Math.max(0, i - 1))}
            hitSlop={0}
          />
          <Pressable
            style={styles.tapRight}
            onPress={() => setIndex((i) => Math.min(media.length - 1, i + 1))}
            hitSlop={0}
          />
          <View style={styles.dotsRow}>
            {media.map((_, i) => (
              <View key={i} style={[styles.dot, i === index && styles.dotActive]} />
            ))}
          </View>
        </>
      )}

      {current?.media_type === "video" && (
        <View style={styles.videoBadge}>
          <Ionicons name="volume-mute" size={13} color="#fff" />
        </View>
      )}

      <LinearGradient
        colors={["transparent", "rgba(11,41,68,0.15)", "rgba(11,41,68,0.92)"]}
        locations={[0, 0.5, 1]}
        style={styles.gradient}
      />

      {superlikedMe && (
        <View style={styles.superlikeBadge}>
          <Ionicons name="star" size={14} color="#fff" />
          <Text style={styles.superlikeBadgeText}>{t("discover.superlikedYou")}</Text>
        </View>
      )}

      <View style={styles.infoOverlay}>
        <View style={styles.nameRow}>
          {gender && GENDER_ICON[gender] && (
            <Ionicons name={GENDER_ICON[gender]} size={20} color="#fff" style={styles.genderIcon} />
          )}
          <Text style={styles.name} numberOfLines={1}>
            {displayName}
          </Text>
          <Text style={styles.age}>{age}</Text>
          {verifiedBadge && <Ionicons name="checkmark-circle" size={20} color="#4FC3F7" />}
        </View>
        {distanceKm != null && (
          <View style={styles.distanceRow}>
            <Ionicons name="location-sharp" size={13} color={colors.accentSoft} />
            <Text style={styles.distance}>{t("discover.kmAway", { km: Math.round(distanceKm) })}</Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { width: "100%", aspectRatio: 0.72, backgroundColor: colors.creamDeep },
  media: { width: "100%", height: "100%" },
  placeholder: { alignItems: "center", justifyContent: "center" },
  tapLeft: { position: "absolute", top: 0, bottom: 0, left: 0, width: "34%" },
  tapRight: { position: "absolute", top: 0, bottom: 0, right: 0, width: "66%" },
  dotsRow: {
    position: "absolute",
    top: 12,
    left: 12,
    right: 12,
    flexDirection: "row",
    gap: 4,
  },
  dot: { flex: 1, height: 3, borderRadius: 2, backgroundColor: "rgba(255,255,255,0.4)" },
  dotActive: { backgroundColor: "#fff" },
  videoBadge: {
    position: "absolute",
    top: 26,
    left: 12,
    backgroundColor: "rgba(0,0,0,0.45)",
    borderRadius: 14,
    padding: 6,
  },
  gradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "40%" },
  superlikeBadge: {
    position: "absolute",
    top: 26,
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
  genderIcon: { marginBottom: 3 },
  name: { color: "#fff", fontSize: 26, fontWeight: "800", flexShrink: 1 },
  age: { color: "#fff", fontSize: 22, fontWeight: "400" },
  distanceRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  distance: { color: colors.accentSoft, fontSize: 13, fontWeight: "500" },
});
