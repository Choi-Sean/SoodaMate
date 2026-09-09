import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { createCoupleStory } from "../../api/coupleStories";
import { presignStoryImage, uploadToPresignedUrl } from "../../api/uploads";
import { showAlert } from "../../utils/alert";
import { colors } from "../../theme";

interface Props {
  route: { params: { matchId: string; otherDisplayName: string } };
  navigation: { goBack: () => void };
}

/** Reached from ChatRoomScreen's "⋯" menu for a specific match. Submitting
 * doesn't publish anything yet — the story sits as "pending" until the
 * matched peer confirms from their own MyCoupleStoriesScreen (see
 * routers/couple_stories.py — the consent gate the user asked for). */
export default function SubmitCoupleStoryScreen({ route, navigation }: Props) {
  const { t } = useTranslation();
  const { matchId, otherDisplayName } = route.params;

  const [storyText, setStoryText] = useState("");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [photoObjectPath, setPhotoObjectPath] = useState<string | null>(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handlePickPhoto() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError(t("profileSetup.photoPermission"));
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"],
      quality: 0.8,
      allowsEditing: true,
      aspect: [4, 3],
    });
    if (result.canceled || !result.assets[0]) return;

    setUploadingPhoto(true);
    setError(null);
    try {
      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignStoryImage(contentType);
      await uploadToPresignedUrl(upload_url, result.assets[0].uri, contentType);
      setPhotoObjectPath(gcs_object_path);
      setPhotoUri(result.assets[0].uri);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setUploadingPhoto(false);
    }
  }

  async function handleSubmit() {
    if (!storyText.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createCoupleStory(matchId, storyText.trim(), photoObjectPath);
      showAlert(t("coupleStory.writeTitle"), t("coupleStory.submitSuccess"));
      navigation.goBack();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      if (e?.response?.status === 409) {
        setError(t("coupleStory.alreadyExists"));
      } else {
        setError(detail ?? e?.message ?? t("coupleStory.submitError"));
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.subtitle}>{otherDisplayName}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <Text style={styles.label}>{t("coupleStory.storyLabel")}</Text>
      <TextInput
        style={styles.textArea}
        value={storyText}
        onChangeText={setStoryText}
        placeholder={t("coupleStory.storyPlaceholder")}
        multiline
        maxLength={2000}
      />

      <Text style={styles.label}>{t("coupleStory.addPhotoOptional")}</Text>
      {photoUri ? (
        <Pressable onPress={handlePickPhoto}>
          <Image source={{ uri: photoUri }} style={styles.photo} />
        </Pressable>
      ) : (
        <Pressable style={styles.photoPicker} onPress={handlePickPhoto} disabled={uploadingPhoto}>
          {uploadingPhoto ? (
            <ActivityIndicator color={colors.accentDark} />
          ) : (
            <Ionicons name="camera-outline" size={26} color={colors.accentDark} />
          )}
        </Pressable>
      )}

      <Text style={styles.consentNotice}>{t("coupleStory.consentNotice")}</Text>

      <Pressable
        style={[styles.submitButton, (!storyText.trim() || submitting) && styles.submitButtonDisabled]}
        onPress={handleSubmit}
        disabled={!storyText.trim() || submitting}
      >
        {submitting ? <ActivityIndicator color="#fff" /> : <Text style={styles.submitButtonText}>{t("coupleStory.submit")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, gap: 6 },
  subtitle: { fontSize: 14, color: colors.muted, marginBottom: 10 },
  error: { color: colors.danger, marginBottom: 8 },
  label: { fontSize: 14, fontWeight: "600", color: colors.muted, marginTop: 14, marginBottom: 8 },
  textArea: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 12,
    padding: 14,
    minHeight: 120,
    fontSize: 15,
    color: colors.ink,
    textAlignVertical: "top",
  },
  photoPicker: {
    width: 120,
    height: 90,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: "dashed",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.creamDeep,
  },
  photo: { width: 160, height: 120, borderRadius: 12 },
  consentNotice: { fontSize: 12, color: colors.muted, marginTop: 16, lineHeight: 17 },
  submitButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 20 },
  submitButtonDisabled: { opacity: 0.5 },
  submitButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
