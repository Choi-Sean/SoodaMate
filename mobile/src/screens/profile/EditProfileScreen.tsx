import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { getMyProfile, updateMyProfile } from "../../api/profiles";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "EditProfile">;

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "other", "all"];

export default function EditProfileScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });

  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [gender, setGender] = useState<Gender>("male");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
  const [minAge, setMinAge] = useState("18");
  const [maxAge, setMaxAge] = useState("99");
  const [maxDistanceKm, setMaxDistanceKm] = useState("50");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profile) return;
    setDisplayName(profile.display_name);
    setBio(profile.bio ?? "");
    setGender(profile.gender);
    setInterestedIn(profile.interested_in);
    setMinAge(String(profile.min_age_pref));
    setMaxAge(String(profile.max_age_pref));
    setMaxDistanceKm(String(profile.max_distance_km));
  }, [profile]);

  async function handleSave() {
    if (!profile) return;
    setError(null);
    setSaving(true);
    try {
      await updateMyProfile({
        display_name: displayName.trim(),
        birth_date: profile.birth_date,
        gender,
        interested_in: interestedIn,
        bio: bio.trim() || null,
        min_age_pref: Number(minAge) || 18,
        max_age_pref: Number(maxAge) || 99,
        max_distance_km: Number(maxDistanceKm) || 50,
      });
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
      navigation.goBack();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSaving(false);
    }
  }

  if (isLoading || !profile) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{t("editProfile.title")}</Text>
      {error && <Text style={styles.error}>{error}</Text>}

      <TextInput style={styles.input} placeholder={t("editProfile.displayName")} value={displayName} onChangeText={setDisplayName} />
      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder={t("editProfile.bio")}
        value={bio}
        onChangeText={setBio}
        multiline
      />

      <Text style={styles.label}>{t("editProfile.iAm")}</Text>
      <View style={styles.row}>
        {GENDERS.map((g) => (
          <Pressable key={g} style={[styles.chip, gender === g && styles.chipSelected]} onPress={() => setGender(g)}>
            <Text style={gender === g ? styles.chipTextSelected : styles.chipText}>{t(`profileSetup.${g}`)}</Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>{t("editProfile.interestedIn")}</Text>
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

      <Text style={styles.label}>{t("editProfile.ageRange")}</Text>
      <View style={styles.row}>
        <TextInput style={[styles.input, styles.smallInput]} keyboardType="number-pad" value={minAge} onChangeText={setMinAge} />
        <Text style={styles.rangeSeparator}>{t("editProfile.to")}</Text>
        <TextInput style={[styles.input, styles.smallInput]} keyboardType="number-pad" value={maxAge} onChangeText={setMaxAge} />
      </View>

      <Text style={styles.label}>{t("editProfile.maxDistance")}</Text>
      <TextInput
        style={[styles.input, styles.smallInput]}
        keyboardType="number-pad"
        value={maxDistanceKm}
        onChangeText={setMaxDistanceKm}
      />

      <Pressable style={styles.photosLink} onPress={() => navigation.navigate("PhotoManager")}>
        <Text style={styles.photosLinkText}>{t("editProfile.managePhotosCount", { count: profile.photos.length })}</Text>
      </Pressable>

      <Pressable style={styles.primaryButton} onPress={handleSave} disabled={saving}>
        {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("editProfile.save")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, flexGrow: 1, backgroundColor: colors.white },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 24, marginTop: 24, color: colors.navy },
  error: { color: colors.danger, marginBottom: 12 },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, marginBottom: 12, fontSize: 16 },
  multiline: { minHeight: 80, textAlignVertical: "top" },
  smallInput: { width: 90, textAlign: "center" },
  label: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, alignItems: "center" },
  rangeSeparator: { color: colors.muted },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff" },
  photosLink: { marginTop: 24, padding: 14, borderWidth: 1, borderColor: colors.border, borderRadius: 10, alignItems: "center" },
  photosLinkText: { color: colors.ink, fontWeight: "500" },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16, marginBottom: 24 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
