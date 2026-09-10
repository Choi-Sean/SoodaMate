import { useState } from "react";
import {
  ActivityIndicator,
  Image,
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
  StyleSheet,
} from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { createMoment, deleteMoment } from "../api/moments";
import { presignMomentImage, uploadToPresignedUrl } from "../api/uploads";
import { showAlert } from "../utils/alert";
import { formatTimestampDate } from "../utils/age";
import { colors } from "../theme";
import type { Moment } from "../types";

const MOMENT_LIMIT = 6;

interface Props {
  moments: Moment[];
  onChanged: () => void | Promise<void>;
}

/** Inline "요즘 나 / Lately" editor for Edit Profile — a horizontal strip of
 * recent moment cards (photo + short caption + date) plus an add tile. A
 * rolling window: the backend keeps only the newest MOMENT_LIMIT, so the
 * add tile stays available and the oldest silently drops off. */
export default function MomentsEditor({ moments, onChanged }: Props) {
  const { t, i18n } = useTranslation();
  const [error, setError] = useState<string | null>(null);
  const [pendingUri, setPendingUri] = useState<string | null>(null);
  const [caption, setCaption] = useState("");
  const [posting, setPosting] = useState(false);

  async function handlePick() {
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(t("profileSetup.photoPermission"));
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8, allowsEditing: true });
    if (result.canceled || !result.assets[0]) return;
    setPendingUri(result.assets[0].uri);
    setCaption("");
  }

  async function handlePost() {
    if (!pendingUri) return;
    setPosting(true);
    setError(null);
    try {
      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignMomentImage(contentType);
      await uploadToPresignedUrl(upload_url, pendingUri, contentType);
      await createMoment(gcs_object_path, caption);
      setPendingUri(null);
      setCaption("");
      await onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setPosting(false);
    }
  }

  function confirmDelete(id: string) {
    showAlert(t("moments.deleteConfirmTitle"), undefined, [
      { text: t("common.cancel"), style: "cancel" },
      {
        text: t("common.delete"),
        style: "destructive",
        onPress: async () => {
          try {
            await deleteMoment(id);
            await onChanged();
          } catch {
            setError(t("common.somethingWentWrong"));
          }
        },
      },
    ]);
  }

  return (
    <View>
      <Text style={styles.label}>{t("moments.editLabel")}</Text>
      <Text style={styles.hint}>{t("moments.editHint")}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.strip}>
        {moments.map((m) => (
          <View key={m.id} style={styles.card}>
            <Image source={{ uri: m.image_url }} style={styles.cardImage} />
            <Pressable style={styles.deleteBadge} onPress={() => confirmDelete(m.id)}>
              <Text style={styles.deleteBadgeText}>✕</Text>
            </Pressable>
            {m.caption ? (
              <Text style={styles.caption} numberOfLines={2}>
                {m.caption}
              </Text>
            ) : (
              <View style={styles.captionSpacer} />
            )}
            <Text style={styles.date}>{formatTimestampDate(m.created_at, i18n.language)}</Text>
          </View>
        ))}
        {moments.length < MOMENT_LIMIT && (
          <Pressable style={[styles.card, styles.addCard]} onPress={handlePick}>
            <Ionicons name="add" size={28} color={colors.muted} />
            <Text style={styles.addText}>{t("moments.addButton")}</Text>
          </Pressable>
        )}
      </ScrollView>

      <Modal visible={!!pendingUri} transparent animationType="fade" onRequestClose={() => setPendingUri(null)}>
        <View style={styles.modalBackdrop}>
          <View style={styles.modalCard}>
            {pendingUri && <Image source={{ uri: pendingUri }} style={styles.modalImage} />}
            <TextInput
              style={styles.modalInput}
              value={caption}
              onChangeText={setCaption}
              placeholder={t("moments.captionPlaceholder")}
              maxLength={280}
              multiline
            />
            <View style={styles.modalActions}>
              <Pressable style={styles.modalCancel} onPress={() => setPendingUri(null)} disabled={posting}>
                <Text style={styles.modalCancelText}>{t("common.cancel")}</Text>
              </Pressable>
              <Pressable style={styles.modalPost} onPress={handlePost} disabled={posting}>
                {posting ? <ActivityIndicator color="#fff" /> : <Text style={styles.modalPostText}>{t("moments.post")}</Text>}
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const CARD_W = 120;

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", color: colors.muted, marginTop: 12, marginBottom: 4 },
  hint: { fontSize: 12, color: colors.muted, marginBottom: 10, lineHeight: 16 },
  error: { color: colors.danger, marginBottom: 8 },
  strip: { gap: 10, paddingRight: 4 },
  card: { width: CARD_W, borderRadius: 12, backgroundColor: colors.creamDeep, overflow: "hidden", paddingBottom: 8 },
  cardImage: { width: CARD_W, height: CARD_W },
  caption: { fontSize: 11.5, color: colors.ink, paddingHorizontal: 8, paddingTop: 6, lineHeight: 15, minHeight: 34 },
  captionSpacer: { minHeight: 34, paddingTop: 6 },
  date: { fontSize: 10, color: colors.muted, paddingHorizontal: 8, paddingTop: 2 },
  deleteBadge: {
    position: "absolute",
    top: 4,
    right: 4,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: "rgba(11,59,99,0.7)",
    alignItems: "center",
    justifyContent: "center",
  },
  deleteBadgeText: { color: "#fff", fontSize: 12 },
  addCard: {
    height: CARD_W + 42,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: "dashed",
    backgroundColor: colors.white,
  },
  addText: { fontSize: 12, color: colors.muted, marginTop: 2 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.6)", alignItems: "center", justifyContent: "center", padding: 24 },
  modalCard: { width: "100%", maxWidth: 340, backgroundColor: colors.white, borderRadius: 16, padding: 16, gap: 12 },
  modalImage: { width: "100%", aspectRatio: 1, borderRadius: 12, backgroundColor: colors.creamDeep },
  modalInput: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 12,
    minHeight: 60,
    fontSize: 14,
    color: colors.ink,
    textAlignVertical: "top",
  },
  modalActions: { flexDirection: "row", gap: 10 },
  modalCancel: { flex: 1, paddingVertical: 12, borderRadius: 10, alignItems: "center", backgroundColor: colors.creamDeep },
  modalCancelText: { color: colors.muted, fontWeight: "700" },
  modalPost: { flex: 1, paddingVertical: 12, borderRadius: 10, alignItems: "center", backgroundColor: colors.accent },
  modalPostText: { color: "#fff", fontWeight: "700" },
});
