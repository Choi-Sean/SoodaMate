import { Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { LinearGradient } from "expo-linear-gradient";
import { useTranslation } from "react-i18next";

import ProfileMedia from "./ProfileMedia";
import VerifiedBadge from "./VerifiedBadge";
import type { Photo } from "../types";
import { colors } from "../theme";
import { formatDistanceKm } from "../utils/units";

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
  faceVerified?: boolean;
}

/** The full-bleed opening photo/video (Hinge-style — a single hero shot up
 * top, not a Tinder/Bumble tap-through carousel) with the name/age/gender
 * overlay. Every other photo/video lives further down the scroll, in
 * ProfileInfoSections — there's no tap-to-advance here anymore, so there's
 * exactly one place to see each piece of media, not two. */
export default function MediaCarousel({
  media,
  displayName,
  age,
  gender,
  distanceKm,
  superlikedMe,
  verifiedBadge,
  faceVerified,
}: Props) {
  const { t, i18n } = useTranslation();
  const current = media[0];
  const useImperial = i18n.language === "en";

  return (
    <View style={styles.container}>
      {current ? (
        <ProfileMedia media={current} style={styles.media} />
      ) : (
        <View style={[styles.media, styles.placeholder]}>
          <Ionicons name="person" size={72} color={colors.border} />
        </View>
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
        {(verifiedBadge || faceVerified) && (
          <View style={styles.verifiedPill}>
            <VerifiedBadge size={14} />
            <Text style={styles.verifiedPillText}>{t("profileDetail.photoVerified")}</Text>
          </View>
        )}
        <View style={styles.nameRow}>
          {gender && GENDER_ICON[gender] && (
            <Ionicons name={GENDER_ICON[gender]} size={20} color="#fff" style={styles.genderIcon} />
          )}
          <Text style={styles.name} numberOfLines={1}>
            {displayName}
          </Text>
          <Text style={styles.age}>{age}</Text>
        </View>
        {distanceKm != null && (
          <View style={styles.distanceRow}>
            <Ionicons name="location-sharp" size={13} color={colors.accentSoft} />
            <Text style={styles.distance}>
              {useImperial
                ? t("discover.milesAway", { mi: formatDistanceKm(distanceKm) })
                : t("discover.kmAway", { km: Math.round(distanceKm) })}
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  // maxWidth keeps the aspectRatio-driven height sane on wide/desktop
  // viewports (web) — without it, a 900px-wide container becomes a ~1250px
  // tall image and pushes the name/age overlay off the bottom of the screen.
  container: { width: "100%", maxWidth: 480, alignSelf: "center", aspectRatio: 0.72, backgroundColor: colors.creamDeep },
  media: { width: "100%", height: "100%" },
  placeholder: { alignItems: "center", justifyContent: "center" },
  videoBadge: {
    position: "absolute",
    top: 16,
    left: 12,
    backgroundColor: "rgba(0,0,0,0.45)",
    borderRadius: 14,
    padding: 6,
  },
  gradient: { position: "absolute", left: 0, right: 0, bottom: 0, height: "40%" },
  superlikeBadge: {
    position: "absolute",
    top: 16,
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
  verifiedPill: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: 5,
    backgroundColor: "rgba(255,255,255,0.22)",
    borderRadius: 999,
    paddingVertical: 4,
    paddingHorizontal: 10,
    marginBottom: 8,
  },
  verifiedPillText: { color: "#fff", fontSize: 11.5, fontWeight: "700" },
  nameRow: { flexDirection: "row", alignItems: "flex-end", gap: 8 },
  genderIcon: { marginBottom: 3 },
  name: { color: "#fff", fontSize: 26, fontWeight: "800", flexShrink: 1 },
  age: { color: "#fff", fontSize: 22, fontWeight: "400" },
  distanceRow: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 4 },
  distance: { color: colors.accentSoft, fontSize: 13, fontWeight: "500" },
});
