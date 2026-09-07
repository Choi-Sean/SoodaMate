import { useEffect, useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import * as ImagePicker from "expo-image-picker";
import { useTranslation } from "react-i18next";

import { getMyProfile } from "../../api/profiles";
import { getFaceVerificationStatus, presignFacePhoto, submitFaceVerification } from "../../api/verification";
import { uploadToPresignedUrl } from "../../api/uploads";
import { colors } from "../../theme";

export default function FaceVerificationScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const { data: status, refetch } = useQuery({
    queryKey: ["faceVerificationStatus"],
    queryFn: getFaceVerificationStatus,
  });

  const [selfieUri, setSelfieUri] = useState<string | null>(null);
  const [idPhotoUri, setIdPhotoUri] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function pickSelfie() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    const result = permission.granted
      ? await ImagePicker.launchCameraAsync({ quality: 0.8, allowsEditing: true, aspect: [1, 1], cameraType: ImagePicker.CameraType.front })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8, allowsEditing: true, aspect: [1, 1] });
    if (!result.canceled && result.assets[0]) {
      setSelfieUri(result.assets[0].uri);
    }
  }

  async function pickIdPhoto() {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    const result = permission.granted
      ? await ImagePicker.launchCameraAsync({ quality: 0.8, allowsEditing: true, aspect: [4, 3] })
      : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], quality: 0.8, allowsEditing: true, aspect: [4, 3] });
    if (!result.canceled && result.assets[0]) {
      setIdPhotoUri(result.assets[0].uri);
    }
  }

  async function handleSubmit() {
    if (!selfieUri || !idPhotoUri) return;
    setError(null);
    setSubmitting(true);
    try {
      const contentType = "image/jpeg";
      const selfiePresign = await presignFacePhoto(contentType, "selfie");
      await uploadToPresignedUrl(selfiePresign.upload_url, selfieUri, contentType);

      const idPresign = await presignFacePhoto(contentType, "id_photo");
      await uploadToPresignedUrl(idPresign.upload_url, idPhotoUri, contentType);

      await submitFaceVerification(selfiePresign.gcs_object_path, idPresign.gcs_object_path);
      await refetch();
      setSelfieUri(null);
      setIdPhotoUri(null);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSubmitting(false);
    }
  }

  const isVerified = profile?.face_verified;
  const statusKey = status?.status ?? "unsubmitted";

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{t("faceVerification.title")}</Text>
      <Text style={styles.subtitle}>{t("faceVerification.subtitle")}</Text>

      {isVerified && (
        <View style={styles.badgeBanner}>
          <Text style={styles.badgeBannerText}>✅ {t("faceVerification.verifiedBanner")}</Text>
        </View>
      )}

      {!isVerified && statusKey === "pending" && (
        <View style={styles.pendingBanner}>
          <Text style={styles.pendingBannerText}>⏳ {t("faceVerification.pendingBanner")}</Text>
        </View>
      )}

      {!isVerified && statusKey === "rejected" && (
        <View style={styles.rejectedBanner}>
          <Text style={styles.rejectedBannerText}>{t("faceVerification.rejectedBanner")}</Text>
        </View>
      )}

      {error && <Text style={styles.error}>{error}</Text>}

      {!isVerified && (
        <>
          <Text style={styles.fieldLabel}>{t("faceVerification.selfieLabel")}</Text>
          <Pressable style={styles.photoPicker} onPress={pickSelfie}>
            {selfieUri ? (
              <Image source={{ uri: selfieUri }} style={styles.photo} />
            ) : (
              <Text style={styles.photoPickerText}>{t("faceVerification.takeSelfie")}</Text>
            )}
          </Pressable>

          <Text style={styles.fieldLabel}>{t("faceVerification.idPhotoLabel")}</Text>
          <Text style={styles.idPhotoHint}>{t("faceVerification.idPhotoHint")}</Text>
          <Pressable style={[styles.photoPicker, styles.idPhotoPicker]} onPress={pickIdPhoto}>
            {idPhotoUri ? (
              <Image source={{ uri: idPhotoUri }} style={styles.photo} />
            ) : (
              <Text style={styles.photoPickerText}>{t("faceVerification.takeIdPhoto")}</Text>
            )}
          </Pressable>

          <Pressable style={styles.primaryButton} onPress={handleSubmit} disabled={submitting || !selfieUri || !idPhotoUri}>
            {submitting ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.primaryButtonText}>
                {statusKey === "rejected" ? t("faceVerification.resubmit") : t("faceVerification.submit")}
              </Text>
            )}
          </Pressable>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, flexGrow: 1, backgroundColor: colors.white },
  title: { fontSize: 24, fontWeight: "700", marginTop: 8, marginBottom: 4, color: colors.navy },
  subtitle: { color: colors.muted, marginBottom: 20, lineHeight: 20 },
  badgeBanner: { backgroundColor: "#E6F4EA", borderRadius: 12, padding: 14, marginBottom: 16 },
  badgeBannerText: { color: "#1E7A34", fontWeight: "700" },
  pendingBanner: { backgroundColor: colors.creamDeep, borderRadius: 12, padding: 14, marginBottom: 16 },
  pendingBannerText: { color: colors.navy, fontWeight: "600" },
  rejectedBanner: { backgroundColor: "#FBEAE9", borderRadius: 12, padding: 14, marginBottom: 16 },
  rejectedBannerText: { color: "#B3261E", fontWeight: "600" },
  error: { color: colors.danger, marginBottom: 12 },
  fieldLabel: { fontSize: 14, fontWeight: "700", color: colors.navy, marginBottom: 6 },
  idPhotoHint: { fontSize: 12.5, color: colors.muted, marginBottom: 10 },
  photoPicker: {
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: colors.creamDeep,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
    marginBottom: 24,
    overflow: "hidden",
  },
  idPhotoPicker: { width: "100%", height: 180, borderRadius: 12, alignSelf: "stretch" },
  photo: { width: "100%", height: "100%" },
  photoPickerText: { color: colors.muted, textAlign: "center", paddingHorizontal: 16 },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center" },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
