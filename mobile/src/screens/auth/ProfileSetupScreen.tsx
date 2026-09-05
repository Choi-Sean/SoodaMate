import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useTranslation } from "react-i18next";

import { confirmPhoto, updateMyProfile } from "../../api/profiles";
import { presignUpload, uploadToPresignedUrl } from "../../api/uploads";
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "other", "all"];

interface Props {
  onComplete: () => void;
}

export default function ProfileSetupScreen({ onComplete }: Props) {
  const { t } = useTranslation();
  const [displayName, setDisplayName] = useState("");
  const [birthDate, setBirthDate] = useState(""); // YYYY-MM-DD
  const [gender, setGender] = useState<Gender>("male");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pickPhoto() {
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
    if (!result.canceled && result.assets[0]) {
      setPhotoUri(result.assets[0].uri);
    }
  }

  async function handleSubmit() {
    if (!displayName.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) {
      setError(t("profileSetup.validationMissing"));
      return;
    }
    if (!photoUri) {
      setError(t("profileSetup.needPhoto"));
      return;
    }

    setError(null);
    setLoading(true);
    try {
      await updateMyProfile({
        display_name: displayName.trim(),
        birth_date: birthDate,
        gender,
        interested_in: interestedIn,
      });

      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignUpload(contentType, 0);
      await uploadToPresignedUrl(upload_url, photoUri, contentType);
      await confirmPhoto(gcs_object_path, 0);

      onComplete();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{t("profileSetup.title")}</Text>

      {error && <Text style={styles.error}>{error}</Text>}

      <Pressable style={styles.photoPicker} onPress={pickPhoto}>
        {photoUri ? (
          <Image source={{ uri: photoUri }} style={styles.photo} />
        ) : (
          <Text style={styles.photoPickerText}>{t("profileSetup.addPhoto")}</Text>
        )}
      </Pressable>

      <TextInput
        style={styles.input}
        placeholder={t("profileSetup.displayName")}
        value={displayName}
        onChangeText={setDisplayName}
      />
      <TextInput
        style={styles.input}
        placeholder={t("profileSetup.birthDate")}
        value={birthDate}
        onChangeText={setBirthDate}
      />

      <Text style={styles.label}>{t("profileSetup.iAm")}</Text>
      <View style={styles.row}>
        {GENDERS.map((g) => (
          <Pressable
            key={g}
            style={[styles.chip, gender === g && styles.chipSelected]}
            onPress={() => setGender(g)}
          >
            <Text style={gender === g ? styles.chipTextSelected : styles.chipText}>{t(`profileSetup.${g}`)}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>{t("profileSetup.interestedIn")}</Text>
      <View style={styles.row}>
        {INTERESTS.map((g) => (
          <Pressable
            key={g}
            style={[styles.chip, interestedIn === g && styles.chipSelected]}
            onPress={() => setInterestedIn(g)}
          >
            <Text style={interestedIn === g ? styles.chipTextSelected : styles.chipText}>{t(`profileSetup.${g}`)}</Text>
          </Pressable>
        ))}
      </View>

      <Pressable style={styles.primaryButton} onPress={handleSubmit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("profileSetup.continue")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: colors.white, flexGrow: 1 },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 24, marginTop: 24, color: colors.navy },
  error: { color: colors.danger, marginBottom: 12 },
  photoPicker: {
    width: 140,
    height: 180,
    borderRadius: 12,
    backgroundColor: colors.creamDeep,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
    marginBottom: 24,
    overflow: "hidden",
  },
  photo: { width: "100%", height: "100%" },
  photoPickerText: { color: colors.muted },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    marginBottom: 12,
    fontSize: 16,
  },
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff" },
  primaryButton: {
    backgroundColor: colors.accent,
    borderRadius: 10,
    padding: 14,
    alignItems: "center",
    marginTop: 32,
    marginBottom: 24,
  },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
