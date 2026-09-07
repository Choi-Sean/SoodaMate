import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Image, Modal, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { useVideoPlayer, VideoView } from "expo-video";
import { useTranslation } from "react-i18next";

import { confirmPhoto, deletePhoto, reorderPhotos } from "../api/profiles";
import { presignUpload, uploadToPresignedUrl } from "../api/uploads";
import { showAlert } from "../utils/alert";
import { colors } from "../theme";
import type { Photo } from "../types";

const MAX_PHOTOS = 10;
const VIDEO_MAX_SECONDS = 30;

interface Props {
  photos: Photo[];
  onChanged: () => void | Promise<void>;
}

/** Inline photo/video grid used directly inside Edit Profile — thumbnails,
 * add photo, add one video, delete, reorder (left/right arrows), set-as-
 * default, and a tap-to-preview fullscreen viewer. There is no separate
 * "manage photos" screen anymore; this *is* it.
 *
 * Reorder/set-default are optimistic: `orderIds` is the actual render
 * order and updates instantly on tap, while the PUT /reorder call and the
 * parent's onChanged() (a full profile refetch) happen in the background —
 * previously every single arrow tap awaited both sequentially with the
 * buttons disabled meanwhile, which is what made reordering feel so slow. */
export default function ProfilePhotosGrid({ photos, onChanged }: Props) {
  const { t } = useTranslation();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);

  const byPosition = photos.slice().sort((a, b) => a.position - b.position);
  const [orderIds, setOrderIds] = useState<string[]>(() => byPosition.map((p) => p.id));
  // Counts add/delete/reorder calls still in flight. While it's above zero
  // the resync effect below trusts local state over the (possibly stale)
  // photos prop — without this, firing a second delete before the first
  // one's refetch lands would have the refetch's still-9-items response
  // resync local state back over the second delete's own optimistic
  // update, silently undoing it.
  const pendingMutations = useRef(0);

  // Re-sync only when the underlying *set* of photo ids actually changes
  // (upload/delete) — not on every parent re-render — so an in-flight
  // optimistic reorder never gets clobbered by a profile refetch that's
  // still catching up to it.
  useEffect(() => {
    const propIds = photos.slice().sort((a, b) => a.position - b.position).map((p) => p.id);
    setOrderIds((prev) => {
      if (pendingMutations.current > 0) return prev;
      const sameSet = propIds.length === prev.length && propIds.every((id) => prev.includes(id));
      return sameSet ? prev : propIds;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [photos]);

  const byId = new Map(photos.map((p) => [p.id, p]));
  const sorted = orderIds.map((id) => byId.get(id)).filter((p): p is Photo => !!p);
  const hasVideo = sorted.some((p) => p.media_type === "video");
  const previewPhoto = previewId ? byId.get(previewId) ?? null : null;

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

    setUploading(true);
    pendingMutations.current++;
    try {
      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignUpload(contentType, nextPosition());
      await uploadToPresignedUrl(upload_url, result.assets[0].uri, contentType);
      await confirmPhoto(gcs_object_path, nextPosition());
      await onChanged();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setUploading(false);
      pendingMutations.current--;
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

    setUploading(true);
    pendingMutations.current++;
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
      setUploading(false);
      pendingMutations.current--;
    }
  }

  function handleDelete(photoId: string) {
    if (sorted.length <= 1) {
      showAlert(t("photos.deleteLastTitle"), t("photos.deleteLastBody"));
      return;
    }
    setError(null);
    const previous = orderIds;
    setOrderIds(previous.filter((id) => id !== photoId));
    pendingMutations.current++;
    deletePhoto(photoId)
      .then(() => onChanged())
      .catch((e: any) => {
        setOrderIds(previous);
        setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
      })
      .finally(() => {
        pendingMutations.current--;
      });
  }

  function applyReorder(newOrder: string[]) {
    const previous = orderIds;
    setOrderIds(newOrder);
    setError(null);
    pendingMutations.current++;
    reorderPhotos(newOrder)
      .then(() => onChanged())
      .catch((e: any) => {
        setOrderIds(previous);
        setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
      })
      .finally(() => {
        pendingMutations.current--;
      });
  }

  function handleMove(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= orderIds.length) return;
    const next = orderIds.slice();
    [next[index], next[target]] = [next[target], next[index]];
    applyReorder(next);
  }

  function handleSetDefault(photoId: string) {
    if (orderIds[0] === photoId) return;
    applyReorder([photoId, ...orderIds.filter((id) => id !== photoId)]);
  }

  return (
    <View>
      <Text style={styles.label}>{t("photos.title")}</Text>
      <Text style={styles.hint}>{t("photos.reorderHint")}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <View style={styles.grid}>
        {sorted.map((photo, index) => (
          <View key={photo.id} style={styles.tile}>
            <Pressable style={styles.imagePressable} onPress={() => setPreviewId(photo.id)}>
              {photo.media_type === "video" ? (
                <View style={[styles.image, styles.videoTile]}>
                  <Ionicons name="play-circle" size={26} color="#fff" />
                </View>
              ) : (
                <Image source={{ uri: photo.url }} style={styles.image} />
              )}
            </Pressable>

            <Pressable style={styles.deleteBadge} onPress={() => handleDelete(photo.id)}>
              <Text style={styles.deleteBadgeText}>✕</Text>
            </Pressable>

            {index === 0 ? (
              <View style={styles.primaryBadge}>
                <Text style={styles.primaryBadgeText}>{t("photos.primary")}</Text>
              </View>
            ) : (
              <Pressable style={styles.setDefaultBadge} onPress={() => handleSetDefault(photo.id)}>
                <Ionicons name="star-outline" size={10} color="#fff" />
                <Text style={styles.setDefaultBadgeText}>{t("photos.setDefault")}</Text>
              </Pressable>
            )}

            <View style={styles.moveRow}>
              <Pressable
                style={[styles.moveButton, index === 0 && styles.moveButtonDisabled]}
                onPress={() => handleMove(index, -1)}
                disabled={index === 0}
              >
                <Ionicons name="chevron-back" size={14} color={index === 0 ? colors.border : colors.white} />
              </Pressable>
              <Pressable
                style={[styles.moveButton, index === sorted.length - 1 && styles.moveButtonDisabled]}
                onPress={() => handleMove(index, 1)}
                disabled={index === sorted.length - 1}
              >
                <Ionicons name="chevron-forward" size={14} color={index === sorted.length - 1 ? colors.border : colors.white} />
              </Pressable>
            </View>
          </View>
        ))}

        {sorted.length < MAX_PHOTOS && (
          <Pressable style={[styles.tile, styles.addTile]} onPress={handleAddPhoto} disabled={uploading}>
            {uploading ? <ActivityIndicator /> : <Text style={styles.addTileText}>+</Text>}
          </Pressable>
        )}
      </View>

      {!hasVideo && (
        <Pressable style={styles.addVideoButton} onPress={handleAddVideo} disabled={uploading || sorted.length >= MAX_PHOTOS}>
          <Ionicons name="videocam" size={18} color={colors.accentDark} />
          <Text style={styles.addVideoText}>{t("photos.addVideo", { seconds: VIDEO_MAX_SECONDS })}</Text>
        </Pressable>
      )}

      <Modal visible={!!previewPhoto} transparent animationType="fade" onRequestClose={() => setPreviewId(null)}>
        <View style={styles.viewerBackdrop}>
          <Pressable style={styles.viewerClose} onPress={() => setPreviewId(null)} hitSlop={12}>
            <Ionicons name="close" size={28} color="#fff" />
          </Pressable>
          {previewPhoto && (
            previewPhoto.media_type === "video" ? (
              <PreviewVideo uri={previewPhoto.url} />
            ) : (
              <Image source={{ uri: previewPhoto.url }} style={styles.viewerImage} resizeMode="contain" />
            )
          )}
        </View>
      </Modal>
    </View>
  );
}

function PreviewVideo({ uri }: { uri: string }) {
  const player = useVideoPlayer(uri, (p) => {
    p.loop = true;
    p.play();
  });
  return <VideoView player={player} style={styles.viewerImage} contentFit="contain" nativeControls />;
}

const TILE_SIZE = 100;

const styles = StyleSheet.create({
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 4, color: colors.muted },
  hint: { fontSize: 12, color: colors.muted, marginBottom: 10 },
  error: { color: colors.danger, marginBottom: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  tile: { width: TILE_SIZE, height: TILE_SIZE, borderRadius: 10, overflow: "hidden", backgroundColor: colors.creamDeep },
  imagePressable: { width: "100%", height: "100%" },
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
  setDefaultBadge: {
    position: "absolute",
    top: 4,
    left: 4,
    flexDirection: "row",
    alignItems: "center",
    gap: 2,
    backgroundColor: "rgba(11,59,99,0.7)",
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 5,
  },
  setDefaultBadgeText: { color: "#fff", fontSize: 8, fontWeight: "700" },
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
  viewerBackdrop: { flex: 1, backgroundColor: "rgba(11,41,68,0.95)", alignItems: "center", justifyContent: "center" },
  viewerClose: { position: "absolute", top: 50, right: 20, zIndex: 1, padding: 8 },
  viewerImage: { width: "100%", height: "80%" },
});
