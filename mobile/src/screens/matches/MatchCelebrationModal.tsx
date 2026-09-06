import { Image, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { colors } from "../../theme";

interface Props {
  visible: boolean;
  otherDisplayName: string | null;
  /** First real photo (never a video — no autoplay in a quick celebration
   * popup), or null/undefined if there isn't one. */
  otherPhotoUrl?: string | null;
  onKeepBrowsing: () => void;
  onSendMessage: () => void;
}

export default function MatchCelebrationModal({
  visible,
  otherDisplayName,
  otherPhotoUrl,
  onKeepBrowsing,
  onSendMessage,
}: Props) {
  const { t } = useTranslation();
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.backdrop}>
        <View style={styles.card}>
          {otherPhotoUrl ? (
            <Image source={{ uri: otherPhotoUrl }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarPlaceholder]}>
              <Ionicons name="heart" size={32} color={colors.accent} />
            </View>
          )}
          <Text style={styles.title}>{t("match.title")}</Text>
          <Text style={styles.subtitle}>
            {t("match.subtitle", { name: otherDisplayName ?? t("match.someone") })}
          </Text>

          <Pressable style={styles.primaryButton} onPress={onSendMessage}>
            <Text style={styles.primaryButtonText}>{t("match.sendMessage")}</Text>
          </Pressable>
          <Pressable style={styles.secondaryButton} onPress={onKeepBrowsing}>
            <Text style={styles.secondaryButtonText}>{t("match.keepBrowsing")}</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(11,59,99,0.6)",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
  },
  card: { backgroundColor: colors.white, borderRadius: 20, padding: 28, width: "100%", alignItems: "center" },
  avatar: { width: 88, height: 88, borderRadius: 44, marginBottom: 16 },
  avatarPlaceholder: { backgroundColor: colors.creamDeep, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 28, fontWeight: "800", color: colors.accent },
  subtitle: { fontSize: 15, color: colors.muted, marginTop: 8, marginBottom: 24, textAlign: "center" },
  primaryButton: {
    backgroundColor: colors.accent,
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
    width: "100%",
  },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  secondaryButton: { padding: 14, alignItems: "center", width: "100%" },
  secondaryButtonText: { color: colors.muted, fontSize: 15 },
});
