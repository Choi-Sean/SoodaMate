import { useState } from "react";
import { ActivityIndicator, Image, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useTranslation } from "react-i18next";

import { confirmPhoto, deletePhoto, reorderPhotos } from "../api/profiles";
import { presignUpload, uploadToPresignedUrl } from "../api/uploads";
import { colors } from "../theme";
import type { Photo } from "../types";

const MAX_PHOTOS = 10;
const VIDEO_MAX_SECONDS = 30;

interface Props {
  photos: Photo[];
  onChanged: () => void | Promise<void>;
}

/** Inline photo/video grid used directly inside Edit Profile — thumbnails,
 * add photo, add one video, delete, and reorder (left/right arrows rather
 * than drag-and-drop, which would need a new gesture/drag-list dependency).
 * There is no separate "manage photos" screen anymore; this *is* it. */
export default function ProfilePhotosGrid({ photos, onChanged }: Props) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sorted = photos.slice().sort((a, b) => a.position - b.position);
  const hasVideo = sorted.some((p) => p.media_type === "video");

  function nextPosition() {
    return sorted.length ? Math.max(...sorted.map((p) => p.position)) + 1 : 0;
  }

  async function handleAddPhoto() {
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(t("profileSetup.photoPermission"));
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
      allowsEditing: true,
      aspect: [3, 4],
    });
    if (result.canceled || !result.assets[0]) return;

    setBusy(true);
    try {
      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignUpload(contentType, nextPosition());
      await uploadToPresignedUrl(upload_url, result.assets[0].uri, contentType);
      await confirmPhoto(gcs_object_path, nextPosition());
      await onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setBusy(false);
    }
  }

  async function handleAddVideo() {
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(t("profileSetup.photoPermission"));
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["videos"],
      videoMaxDuration: VIDEO_MAX_SECONDS,
      quality: 0.8,
    });
    if (result.canceled || !result.assets[0]) return;

    setBusy(true);
    try {
      const contentType = "video/mp4";
      const position = nextPosition();
      const { upload_url, gcs_object_path } = await presignUpload(contentType, position);
      await uploadToPresignedUrl(upload_url, result.assets[0].uri, contentType);
      await confirmPhoto(gcs_object_path, position);
      await onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(photoId: string) {
    setBusy(true);
    setError(null);
    try {
      await deletePhoto(photoId);
      await onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setBusy(false);
    }
  }

  async function handleMove(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= sorted.length) return;
    const ids = sorted.map((p) => p.id);
    [ids[index], ids[target]] = [ids[target], ids[index]];
    setBusy(true);
    setError(null);
    try {
      await reorderPhotos(ids);
      await onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View>
      <Text style={styles.label}>{t("photos.title")}</Text>
      <Text style={styles.hint}>{t("photos.reorderHint")}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <View style={styles.grid}>
        {sorted.map((photo, index) => (
          <View key={photo.id} style={styles.tile}>
            {photo.media_type === "video" ? (
              <View style={[styles.image, styles.videoTile]}>
                <Ionicons name="play-circle" size={26} color="#fff" />
              </View>
            ) : (
              <Image source={{ uri: photo.url }} style={styles.image} />
            )}

            <Pressable style={styles.deleteBadge} onPress={() => handleDelete(photo.id)} disabled={busy}>
              <Text style={styles.deleteBadgeText}>✕</Text>
            </Pressable>

            {index === 0 && (
              <View style={styles.primaryBadge}>
                <Text style={styles.primaryBadgeText}>{t("photos.primary")}</Text>
              </View>
            )}

            <View style={styles.moveRow}>
              <Pressable
                style={[styles.moveButton, index === 0 && styles.moveButtonDisabled]}
                onPress={() => handleMove(index, -1)}
                disabled={busy || index === 0}
              >
                <Ionicons name="chevron-back" size={14} color={index === 0 ? colors.border : colors.white} />
              </Pressable>
              <Pressable
                style={[styles.moveButton, index === sorted.length - 1 && styles.moveButtonDisabled]}
                onPress={() => handleMove(index, 1)}
                disabled={busy || index === sorted.length - 1}
              >
                <Ionicons name="chevron-forward" size={14} color={index === sorted.length - 1 ? colors.border : colors.white} />
              </Pressable>
            </View>
          </View>
        ))}

        {sorted.length < MAX_PHOTOS && (
          <Pressable style={[styles.tile, styles.addTile]} onPress={handleAddPhoto} disabled={busy}>
            {busy ? <ActivityIndicator /> : <Text style={styles.addTileText}>+</Text>}
          </Pressable>
        )}
      </View>

      {!hasVideo && (
        <Pressable style={styles.addVideoButton} onPress={handleAddVideo} disabled={busy || sorted.length >= MAX_PHOTOS}>
          <Ionicons name="videocam" size={18} color={colors.accentDark} />
          <Text style={styles.addVideoText}>{t("photos.addVideo", { seconds: VIDEO_MAX_SECONDS })}</Text>
        </Pressable>
      )}
    </View>
  );
}

const TILE_SIZE = 100;

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 4, color: colors.muted },
  hint: { fontSize: 12, color: colors.muted, marginBottom: 10 },
  error: { color: colors.danger, marginBottom: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  tile: { width: TILE_SIZE, height: TILE_SIZE, borderRadius: 10, overflow: "hidden", backgroundColor: colors.creamDeep },
  image: { width: "100%", height: "100%" },
  videoTile: { backgroundColor: colors.navy, alignItems: "center", justifyContent: "center" },
  addTile: { alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.border, borderStyle: "dashed" },
  addTileText: { fontSize: 32, color: colors.muted },
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
  primaryBadge: {
    position: "absolute",
    top: 4,
    left: 4,
    backgroundColor: "rgba(226,145,77,0.9)",
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 6,
  },
  primaryBadgeText: { color: "#fff", fontSize: 9, fontWeight: "700" },
  moveRow: {
    position: "absolute",
    bottom: 4,
    left: 4,
    right: 4,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  moveButton: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: "rgba(11,59,99,0.7)",
    alignItems: "center",
    justifyContent: "center",
  },
  moveButtonDisabled: { backgroundColor: "rgba(11,59,99,0.25)" },
  addVideoButton: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    marginTop: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: colors.accentSoft,
    borderRadius: 10,
  },
  addVideoText: { color: colors.accentDark, fontWeight: "600" },
});
