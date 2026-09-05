import { useState } from "react";
import { ActivityIndicator, Image, Pressable, Text, View, StyleSheet } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { deletePhoto, confirmPhoto, getMyProfile } from "../../api/profiles";
import { presignUpload, uploadToPresignedUrl } from "../../api/uploads";
import { colors } from "../../theme";

const MAX_PHOTOS = 6;

export default function PhotoManagerScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const photos = profile?.photos ?? [];

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
  }

  async function handleAddPhoto() {
    setError(null);
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(t("profileSetup.photoPermission"));
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsEditing: true,
      aspect: [3, 4],
    });
    if (result.canceled || !result.assets[0]) return;

    const nextPosition = photos.length ? Math.max(...photos.map((p) => p.position)) + 1 : 0;
    setBusy(true);
    try {
      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignUpload(contentType, nextPosition);
      await uploadToPresignedUrl(upload_url, result.assets[0].uri, contentType);
      await confirmPhoto(gcs_object_path, nextPosition);
      await refresh();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setBusy(false);
    }
  }

  async function handleDeletePhoto(photoId: string) {
    setBusy(true);
    setError(null);
    try {
      await deletePhoto(photoId);
      await refresh();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{t("photos.title")}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <View style={styles.grid}>
        {photos
          .slice()
          .sort((a, b) => a.position - b.position)
          .map((photo) => (
            <View key={photo.id} style={styles.tile}>
              <Image source={{ uri: photo.url }} style={styles.image} />
              <Pressable style={styles.deleteBadge} onPress={() => handleDeletePhoto(photo.id)} disabled={busy}>
                <Text style={styles.deleteBadgeText}>✕</Text>
              </Pressable>
            </View>
          ))}

        {photos.length < MAX_PHOTOS && (
          <Pressable style={[styles.tile, styles.addTile]} onPress={handleAddPhoto} disabled={busy}>
            {busy ? <ActivityIndicator /> : <Text style={styles.addTileText}>+</Text>}
          </Pressable>
        )}
      </View>
    </View>
  );
}

const TILE_SIZE = 100;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, padding: 24 },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 16, marginTop: 24, color: colors.navy },
  error: { color: colors.danger, marginBottom: 12 },
  grid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  tile: { width: TILE_SIZE, height: TILE_SIZE, borderRadius: 10, overflow: "hidden", backgroundColor: colors.creamDeep },
  image: { width: "100%", height: "100%" },
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
});
