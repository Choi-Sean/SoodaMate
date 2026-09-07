import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import MediaCarousel from "./MediaCarousel";
import ProfileInfoSections from "./ProfileInfoSections";
import { blockUser, reportUser } from "../api/safety";
import { showAlert } from "../utils/alert";
import type { Candidate } from "../types";
import { colors } from "../theme";

interface Props {
  candidate: Candidate;
}

/** A whole scrollable profile, Hinge-style: a single hero photo/video up
 * top (name/age/gender overlaid on it), then scrolling down reveals fact
 * rows, bio, and pill-grid detail sections, followed by every remaining
 * photo/video. Pass `key={candidate.user_id}` from the caller so state
 * resets on a new candidate. Report/block is available here too, not just
 * from an existing chat — real safety concerns (fake photos, harassment in
 * a bio, etc.) can show up before a match ever happens. */
export default function ProfileCard({ candidate }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  async function submitReport(reason: string) {
    try {
      await reportUser(candidate.user_id, reason);
      showAlert(t("chat.reported"), t("chat.reportedBody"));
    } catch {
      showAlert(t("chat.errorGeneric"));
    }
  }

  function openReportReasons() {
    showAlert(t("chat.reportReasonTitle"), undefined, [
      { text: t("chat.reasonHarassment"), onPress: () => submitReport("harassment") },
      { text: t("chat.reasonInappropriate"), onPress: () => submitReport("inappropriate_content") },
      { text: t("chat.reasonFakeProfile"), onPress: () => submitReport("fake_profile") },
      { text: t("chat.cancel"), style: "cancel" },
    ]);
  }

  async function doBlock() {
    try {
      await blockUser(candidate.user_id);
      // A blocked user must disappear from every deck they could show up
      // in, not just the one currently open.
      await queryClient.invalidateQueries({ queryKey: ["candidates"] });
      await queryClient.invalidateQueries({ queryKey: ["recommended"] });
      await queryClient.invalidateQueries({ queryKey: ["likedMe"] });
    } catch {
      showAlert(t("chat.errorGeneric"));
    }
  }

  function confirmBlock() {
    showAlert(t("chat.blockConfirmTitle"), t("chat.blockConfirmBody"), [
      { text: t("chat.cancel"), style: "cancel" },
      { text: t("chat.blockConfirm"), style: "destructive", onPress: doBlock },
    ]);
  }

  function openMenu() {
    showAlert(candidate.display_name, undefined, [
      { text: t("chat.report"), onPress: openReportReasons },
      { text: t("chat.block"), style: "destructive", onPress: confirmBlock },
      { text: t("chat.cancel"), style: "cancel" },
    ]);
  }

  return (
    <View style={styles.card}>
      <ScrollView bounces={false} showsVerticalScrollIndicator={false}>
        <MediaCarousel
          media={candidate.photos}
          displayName={candidate.display_name}
          age={candidate.age}
          gender={candidate.gender}
          distanceKm={candidate.distance_km}
          superlikedMe={candidate.superliked_me}
          verifiedBadge={candidate.verified_badge}
          faceVerified={candidate.face_verified}
        />
        <ProfileInfoSections candidate={candidate} />
      </ScrollView>

      <Pressable style={styles.menuButton} onPress={openMenu} hitSlop={10}>
        <Text style={styles.menuButtonText}>⋯</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    width: "100%",
    maxWidth: 480,
    alignSelf: "center",
    borderRadius: 24,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
  menuButton: {
    position: "absolute",
    top: 14,
    right: 14,
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "rgba(11,41,68,0.35)",
    alignItems: "center",
    justifyContent: "center",
  },
  menuButtonText: { color: "#fff", fontSize: 18, fontWeight: "800", marginTop: -8 },
});
