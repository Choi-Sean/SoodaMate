import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Linking, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { getMyProfile, setPremiumFilters, updateMyProfile } from "../../api/profiles";
import ChipSelect from "../../components/ChipSelect";
import LocationPicker from "../../components/LocationPicker";
import {
  CANNABIS_KEYS,
  EXERCISE_FREQUENCY_KEYS,
  HAS_KIDS_KEYS,
  POLITICAL_VIEW_KEYS,
  RACE_ETHNICITY_KEYS,
  RELATIONSHIP_GOAL_KEYS,
  RELIGION_KEYS,
  SMOKING_KEYS,
  WANTS_KIDS_KEYS,
} from "../../constants/demographicOptions";
import { useAuthStore } from "../../store/authStore";
import { env } from "../../config/env";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "EditProfile">;

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "other", "all"];

function parseCommaList(value: string): string[] {
  return value
    .split(",")
    .map((v) => v.trim())
    .filter((v) => v.length > 0);
}

export default function EditProfileScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const accessToken = useAuthStore((s) => s.accessToken);

  const [displayName, setDisplayName] = useState("");
  const [legalFirstName, setLegalFirstName] = useState("");
  const [bio, setBio] = useState("");
  const [gender, setGender] = useState<Gender>("male");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
  const [minAge, setMinAge] = useState("18");
  const [maxAge, setMaxAge] = useState("99");
  const [maxDistanceKm, setMaxDistanceKm] = useState("50");
  const [locationLat, setLocationLat] = useState<number | null>(null);
  const [locationLng, setLocationLng] = useState<number | null>(null);

  const [raceEthnicity, setRaceEthnicity] = useState<string | null>(null);
  const [religion, setReligion] = useState<string | null>(null);
  const [politicalView, setPoliticalView] = useState<string | null>(null);
  const [heightCm, setHeightCm] = useState("");
  const [occupation, setOccupation] = useState("");
  const [education, setEducation] = useState("");
  const [hometown, setHometown] = useState("");
  const [smoking, setSmoking] = useState<string | null>(null);
  const [cannabis, setCannabis] = useState<string | null>(null);
  const [exerciseFrequency, setExerciseFrequency] = useState<string | null>(null);
  const [relationshipGoal, setRelationshipGoal] = useState<string | null>(null);
  const [wantsKids, setWantsKids] = useState<string | null>(null);
  const [hasKids, setHasKids] = useState<string | null>(null);
  const [interestsText, setInterestsText] = useState("");
  const [languagesText, setLanguagesText] = useState("");

  const [raceFilter, setRaceFilter] = useState<string[]>([]);
  const [religionFilter, setReligionFilter] = useState<string[]>([]);
  const [savingFilters, setSavingFilters] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profile) return;
    setDisplayName(profile.display_name);
    setLegalFirstName(profile.legal_first_name);
    setBio(profile.bio ?? "");
    setGender(profile.gender);
    setInterestedIn(profile.interested_in);
    setMinAge(String(profile.min_age_pref));
    setMaxAge(String(profile.max_age_pref));
    setMaxDistanceKm(String(profile.max_distance_km));
    setLocationLat(profile.location_lat);
    setLocationLng(profile.location_lng);
    setRaceEthnicity(profile.race_ethnicity);
    setReligion(profile.religion);
    setPoliticalView(profile.political_view);
    setHeightCm(profile.height_cm != null ? String(profile.height_cm) : "");
    setOccupation(profile.occupation ?? "");
    setEducation(profile.education ?? "");
    setHometown(profile.hometown ?? "");
    setSmoking(profile.smoking);
    setCannabis(profile.cannabis);
    setExerciseFrequency(profile.exercise_frequency);
    setRelationshipGoal(profile.relationship_goal);
    setWantsKids(profile.wants_kids);
    setHasKids(profile.has_kids);
    setInterestsText(profile.interests.join(", "));
    setLanguagesText(profile.languages.join(", "));
    setRaceFilter(profile.race_filter);
    setReligionFilter(profile.religion_filter);
  }, [profile]);

  async function handleSave() {
    if (!profile) return;
    setError(null);
    setSaving(true);
    try {
      await updateMyProfile({
        display_name: displayName.trim(),
        legal_first_name: legalFirstName.trim(),
        birth_date: profile.birth_date,
        gender,
        interested_in: interestedIn,
        bio: bio.trim() || null,
        location_lat: locationLat,
        location_lng: locationLng,
        race_ethnicity: raceEthnicity,
        religion,
        political_view: politicalView,
        height_cm: heightCm ? Number(heightCm) : null,
        occupation: occupation.trim() || null,
        education: education.trim() || null,
        hometown: hometown.trim() || null,
        smoking,
        cannabis,
        exercise_frequency: exerciseFrequency,
        relationship_goal: relationshipGoal,
        wants_kids: wantsKids,
        has_kids: hasKids,
        interests: parseCommaList(interestsText),
        languages: parseCommaList(languagesText),
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

  function toggleFilterValue(list: string[], key: string): string[] {
    return list.includes(key) ? list.filter((k) => k !== key) : [...list, key];
  }

  function openShop() {
    const shopUrl = env.marketingSiteUrl + "/shop.html?token=" + encodeURIComponent(accessToken ?? "");
    Linking.openURL(shopUrl);
  }

  async function handleSaveFilters() {
    setSavingFilters(true);
    try {
      await setPremiumFilters(raceFilter, religionFilter);
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
    } catch (e: any) {
      Alert.alert(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSavingFilters(false);
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

      <LocationPicker
        lat={locationLat}
        lng={locationLng}
        onChange={(lat, lng) => {
          setLocationLat(lat);
          setLocationLng(lng);
        }}
      />

      <Text style={styles.sectionTitle}>{t("profileSetup.optionalSection")}</Text>

      <ChipSelect
        label={t("profileSetup.raceEthnicity")}
        options={RACE_ETHNICITY_KEYS}
        translatePrefix="profileSetup.race"
        value={raceEthnicity}
        onChange={setRaceEthnicity}
      />

      <ChipSelect
        label={t("profileSetup.religion")}
        options={RELIGION_KEYS}
        translatePrefix="profileSetup.religionOption"
        value={religion}
        onChange={setReligion}
      />

      <ChipSelect
        label={t("profileSetup.politicalView")}
        options={POLITICAL_VIEW_KEYS}
        translatePrefix="profileSetup.politicalViewOption"
        value={politicalView}
        onChange={setPoliticalView}
      />

      <TextInput
        style={styles.input}
        placeholder={t("profileSetup.heightCm")}
        keyboardType="number-pad"
        value={heightCm}
        onChangeText={setHeightCm}
      />
      <TextInput style={styles.input} placeholder={t("profileSetup.occupation")} value={occupation} onChangeText={setOccupation} />
      <TextInput style={styles.input} placeholder={t("profileSetup.education")} value={education} onChangeText={setEducation} />
      <TextInput style={styles.input} placeholder={t("profileSetup.hometown")} value={hometown} onChangeText={setHometown} />

      <ChipSelect
        label={t("profileSetup.smoking")}
        options={SMOKING_KEYS}
        translatePrefix="profileSetup.smokingOption"
        value={smoking}
        onChange={setSmoking}
      />

      <ChipSelect
        label={t("profileSetup.cannabis")}
        options={CANNABIS_KEYS}
        translatePrefix="profileSetup.cannabisOption"
        value={cannabis}
        onChange={setCannabis}
      />

      <ChipSelect
        label={t("profileSetup.exerciseFrequency")}
        options={EXERCISE_FREQUENCY_KEYS}
        translatePrefix="profileSetup.exerciseFrequencyOption"
        value={exerciseFrequency}
        onChange={setExerciseFrequency}
      />

      <ChipSelect
        label={t("profileSetup.relationshipGoal")}
        options={RELATIONSHIP_GOAL_KEYS}
        translatePrefix="profileSetup.relationshipGoalOption"
        value={relationshipGoal}
        onChange={setRelationshipGoal}
      />

      <ChipSelect
        label={t("profileSetup.wantsKids")}
        options={WANTS_KIDS_KEYS}
        translatePrefix="profileSetup.wantsKidsOption"
        value={wantsKids}
        onChange={setWantsKids}
      />

      <ChipSelect
        label={t("profileSetup.hasKids")}
        options={HAS_KIDS_KEYS}
        translatePrefix="profileSetup.hasKidsOption"
        value={hasKids}
        onChange={setHasKids}
      />

      <TextInput
        style={styles.input}
        placeholder={t("profileSetup.interestsPlaceholder")}
        value={interestsText}
        onChangeText={setInterestsText}
      />
      <TextInput
        style={styles.input}
        placeholder={t("profileSetup.languagesPlaceholder")}
        value={languagesText}
        onChangeText={setLanguagesText}
      />

      <Pressable style={styles.photosLink} onPress={() => navigation.navigate("PhotoManager")}>
        <Text style={styles.photosLinkText}>{t("editProfile.managePhotosCount", { count: profile.photos.length })}</Text>
      </Pressable>

      <Pressable style={styles.primaryButton} onPress={handleSave} disabled={saving}>
        {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("editProfile.save")}</Text>}
      </Pressable>

      <View style={styles.premiumSection}>
        <Text style={styles.premiumTitle}>{t("premiumFilters.title")}</Text>
        {profile.is_premium_member ? (
          <>
            <Text style={styles.label}>{t("premiumFilters.raceLabel")}</Text>
            <View style={styles.row}>
              {RACE_ETHNICITY_KEYS.map((key) => (
                <Pressable
                  key={key}
                  style={[styles.chip, raceFilter.includes(key) && styles.chipSelected]}
                  onPress={() => setRaceFilter(toggleFilterValue(raceFilter, key))}
                >
                  <Text style={raceFilter.includes(key) ? styles.chipTextSelected : styles.chipText}>
                    {t(`profileSetup.race.${key}`)}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>{t("premiumFilters.religionLabel")}</Text>
            <View style={styles.row}>
              {RELIGION_KEYS.map((key) => (
                <Pressable
                  key={key}
                  style={[styles.chip, religionFilter.includes(key) && styles.chipSelected]}
                  onPress={() => setReligionFilter(toggleFilterValue(religionFilter, key))}
                >
                  <Text style={religionFilter.includes(key) ? styles.chipTextSelected : styles.chipText}>
                    {t(`profileSetup.religionOption.${key}`)}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Pressable style={styles.premiumSaveButton} onPress={handleSaveFilters} disabled={savingFilters}>
              {savingFilters ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryButtonText}>{t("premiumFilters.save")}</Text>
              )}
            </Pressable>
          </>
        ) : (
          <>
            <Text style={styles.premiumLockedBody}>{t("premiumFilters.lockedBody")}</Text>
            <Pressable style={styles.premiumSaveButton} onPress={openShop}>
              <Text style={styles.primaryButtonText}>{t("premiumFilters.upgrade")}</Text>
            </Pressable>
          </>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, flexGrow: 1, backgroundColor: colors.white },
  centered: { flex: 1, alignItems: "center", justifyContent: "center" },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 24, marginTop: 24, color: colors.navy },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginTop: 24, marginBottom: 4 },
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
  premiumSection: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 20, marginBottom: 24 },
  premiumTitle: { fontSize: 18, fontWeight: "800", color: colors.navy, marginBottom: 8 },
  premiumLockedBody: { color: colors.muted, fontSize: 14, marginBottom: 16 },
  premiumSaveButton: { backgroundColor: colors.navy, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16 },
});
