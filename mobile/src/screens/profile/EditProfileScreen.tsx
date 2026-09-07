import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Linking, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { getMyProfile, setPremiumFilters, updateMyProfile } from "../../api/profiles";
import ChipSelect from "../../components/ChipSelect";
import MultiChipSelect from "../../components/MultiChipSelect";
import LocationPicker from "../../components/LocationPicker";
import RangeSlider from "../../components/RangeSlider";
import SelectDropdown, { DropdownOption } from "../../components/SelectDropdown";
import ProfilePhotosGrid from "../../components/ProfilePhotosGrid";
import ProfileCompletenessBar from "../../components/ProfileCompletenessBar";
import HeightInput from "../../components/HeightInput";
import CityAutocomplete from "../../components/CityAutocomplete";
import { calculateProfileCompleteness } from "../../utils/profileCompleteness";
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
import { EDUCATION_KEYS } from "../../constants/educationLevels";
import { INTEREST_KEYS, LANGUAGE_KEYS } from "../../constants/interestsAndLanguages";
import { DISTANCE_OPTIONS_KM } from "../../constants/distanceOptions";
import { useAuthStore } from "../../store/authStore";
import { env } from "../../config/env";
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "EditProfile">;

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "all"];
const MAX_INTERESTS = 5;

export default function EditProfileScreen({ navigation }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });
  const accessToken = useAuthStore((s) => s.accessToken);

  const [bio, setBio] = useState("");
  const [gender, setGender] = useState<Gender>("male");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
  const [minAge, setMinAge] = useState(18);
  const [maxAge, setMaxAge] = useState(99);
  const [maxDistanceKm, setMaxDistanceKm] = useState<string>("50");
  const [locationLat, setLocationLat] = useState<number | null>(null);
  const [locationLng, setLocationLng] = useState<number | null>(null);

  const [raceEthnicity, setRaceEthnicity] = useState<string | null>(null);
  const [religion, setReligion] = useState<string | null>(null);
  const [politicalView, setPoliticalView] = useState<string | null>(null);
  const [heightCm, setHeightCm] = useState(170);
  const [occupation, setOccupation] = useState("");
  const [education, setEducation] = useState<string | null>(null);
  const [hometown, setHometown] = useState("");
  const [smoking, setSmoking] = useState<string | null>(null);
  const [cannabis, setCannabis] = useState<string | null>(null);
  const [exerciseFrequency, setExerciseFrequency] = useState<string | null>(null);
  const [relationshipGoal, setRelationshipGoal] = useState<string | null>(null);
  const [wantsKids, setWantsKids] = useState<string | null>(null);
  const [hasKids, setHasKids] = useState<string | null>(null);
  const [interests, setInterests] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);

  const [raceFilter, setRaceFilter] = useState<string[]>([]);
  const [religionFilter, setReligionFilter] = useState<string[]>([]);
  const [savingFilters, setSavingFilters] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profile) return;
    setBio(profile.bio ?? "");
    setGender(profile.gender);
    setInterestedIn(profile.interested_in === "other" ? "all" : profile.interested_in);
    setMinAge(profile.min_age_pref);
    setMaxAge(profile.max_age_pref);
    setMaxDistanceKm(String(profile.max_distance_km));
    setLocationLat(profile.location_lat);
    setLocationLng(profile.location_lng);
    setRaceEthnicity(profile.race_ethnicity);
    setReligion(profile.religion);
    setPoliticalView(profile.political_view);
    setHeightCm(profile.height_cm ?? 170);
    setOccupation(profile.occupation ?? "");
    setEducation(profile.education);
    setHometown(profile.hometown ?? "");
    setSmoking(profile.smoking);
    setCannabis(profile.cannabis);
    setExerciseFrequency(profile.exercise_frequency);
    setRelationshipGoal(profile.relationship_goal);
    setWantsKids(profile.wants_kids);
    setHasKids(profile.has_kids);
    setInterests(profile.interests);
    setLanguages(profile.languages);
    setRaceFilter(profile.race_filter);
    setReligionFilter(profile.religion_filter);
  }, [profile]);

  async function refreshProfile() {
    await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
  }

  async function handleSave() {
    if (!profile) return;
    setError(null);
    setSaving(true);
    try {
      await updateMyProfile({
        // Locked after signup (see nameLockNote below) — sent back
        // unchanged; the backend also ignores any attempt to change these
        // on an existing profile, this just keeps the payload honest.
        display_name: profile.display_name,
        legal_first_name: profile.legal_first_name,
        birth_date: profile.birth_date,
        gender,
        interested_in: interestedIn,
        bio: bio.trim() || null,
        location_lat: locationLat,
        location_lng: locationLng,
        race_ethnicity: raceEthnicity,
        religion,
        political_view: politicalView,
        height_cm: heightCm,
        occupation: occupation.trim() || null,
        education,
        hometown: hometown.trim() || null,
        smoking,
        cannabis,
        exercise_frequency: exerciseFrequency,
        relationship_goal: relationshipGoal,
        wants_kids: wantsKids,
        has_kids: hasKids,
        interests,
        languages,
        min_age_pref: minAge,
        max_age_pref: maxAge,
        max_distance_km: Number(maxDistanceKm) || 50,
      });
      await refreshProfile();
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
      // Round-trips the other premium filter dimensions unchanged (set via
      // the Swipe tab's filter modal) — set_premium_filters is a full
      // replace, so sending only race/religion here would silently clear
      // whatever was set there.
      await setPremiumFilters({
        race_filter: raceFilter,
        religion_filter: religionFilter,
        ...(profile?.premium_filters ?? {}),
      });
      await refreshProfile();
    } catch (e: any) {
      Alert.alert(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSavingFilters(false);
    }
  }

  const distanceOptions: DropdownOption[] = DISTANCE_OPTIONS_KM.map((km) => ({
    key: String(km),
    label: km >= 500 ? t("editProfile.distanceAny") : t("editProfile.distanceKm", { km }),
  }));
  const educationOptions: DropdownOption[] = EDUCATION_KEYS.map((key) => ({
    key,
    label: t(`profileSetup.educationOption.${key}`),
  }));

  const interestOptions = INTEREST_KEYS as unknown as readonly string[];
  const languageOptions = LANGUAGE_KEYS as unknown as readonly string[];

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

      <ProfilePhotosGrid photos={profile.photos} onChanged={refreshProfile} />

      <ProfileCompletenessBar percent={calculateProfileCompleteness(profile)} />

      <Pressable
        style={[styles.verifyCard, profile.face_verified && styles.verifyCardDone]}
        onPress={() => !profile.face_verified && navigation.navigate("FaceVerification")}
      >
        <Text style={styles.verifyCardEmoji}>{profile.face_verified ? "✅" : "🪪"}</Text>
        <View style={styles.verifyCardTextWrap}>
          <Text style={styles.verifyCardTitle}>
            {profile.face_verified ? t("faceVerification.verifiedBanner") : t("faceVerification.cardTitle")}
          </Text>
          {!profile.face_verified && <Text style={styles.verifyCardSubtitle}>{t("faceVerification.cardSubtitle")}</Text>}
        </View>
        {!profile.face_verified && <Ionicons name="chevron-forward" size={18} color={colors.accentDark} />}
      </Pressable>

      <View style={styles.field}>
        <Text style={styles.fieldLabel}>{t("editProfile.name")}</Text>
        <View style={styles.lockedField}>
          <Text style={styles.lockedFieldText}>{profile.display_name}</Text>
          <Ionicons name="lock-closed" size={14} color={colors.muted} />
        </View>
        <Text style={styles.nameLockNote}>{t("editProfile.nameLockNote")}</Text>
      </View>

      <View style={styles.field}>
        <Text style={styles.fieldLabel}>{t("editProfile.bio")}</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder={t("editProfile.bioPlaceholder")}
          value={bio}
          onChangeText={setBio}
          multiline
        />
      </View>

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

      <RangeSlider
        label={t("editProfile.ageRange")}
        min={18}
        max={99}
        valueMin={minAge}
        valueMax={maxAge}
        onChange={(mn, mx) => {
          setMinAge(mn);
          setMaxAge(mx);
        }}
      />

      <SelectDropdown
        label={t("editProfile.maxDistance")}
        placeholder={t("editProfile.maxDistance")}
        options={distanceOptions}
        value={maxDistanceKm}
        onChange={setMaxDistanceKm}
      />

      <View style={styles.section}>
        <LocationPicker
          lat={locationLat}
          lng={locationLng}
          onChange={(lat, lng) => {
            setLocationLat(lat);
            setLocationLng(lng);
          }}
        />
      </View>

      <Text style={styles.sectionTitle}>{t("profileSetup.optionalSection")}</Text>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.raceEthnicity")}
          options={RACE_ETHNICITY_KEYS}
          translatePrefix="profileSetup.race"
          value={raceEthnicity}
          onChange={setRaceEthnicity}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.religion")}
          options={RELIGION_KEYS}
          translatePrefix="profileSetup.religionOption"
          value={religion}
          onChange={setReligion}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.politicalView")}
          options={POLITICAL_VIEW_KEYS}
          translatePrefix="profileSetup.politicalViewOption"
          value={politicalView}
          onChange={setPoliticalView}
        />
      </View>

      <View style={styles.section}>
        <HeightInput valueCm={heightCm} onChange={setHeightCm} />
      </View>
      <View style={styles.section}>
        <Text style={styles.fieldLabel}>{t("profileSetup.occupation")}</Text>
        <TextInput
          style={styles.input}
          placeholder={t("editProfile.occupationPlaceholder")}
          value={occupation}
          onChangeText={setOccupation}
        />
      </View>
      <View style={styles.section}>
        <SelectDropdown
          label={t("profileSetup.education")}
          placeholder={t("profileSetup.education")}
          options={educationOptions}
          value={education}
          onChange={setEducation}
        />
      </View>
      <View style={styles.section}>
        <CityAutocomplete
          label={t("profileSetup.hometown")}
          placeholder={t("editProfile.hometownPlaceholder")}
          value={hometown}
          onChange={setHometown}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.smoking")}
          options={SMOKING_KEYS}
          translatePrefix="profileSetup.smokingOption"
          value={smoking}
          onChange={setSmoking}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.cannabis")}
          options={CANNABIS_KEYS}
          translatePrefix="profileSetup.cannabisOption"
          value={cannabis}
          onChange={setCannabis}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.exerciseFrequency")}
          options={EXERCISE_FREQUENCY_KEYS}
          translatePrefix="profileSetup.exerciseFrequencyOption"
          value={exerciseFrequency}
          onChange={setExerciseFrequency}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.relationshipGoal")}
          options={RELATIONSHIP_GOAL_KEYS}
          translatePrefix="profileSetup.relationshipGoalOption"
          value={relationshipGoal}
          onChange={setRelationshipGoal}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.wantsKids")}
          options={WANTS_KIDS_KEYS}
          translatePrefix="profileSetup.wantsKidsOption"
          value={wantsKids}
          onChange={setWantsKids}
        />
      </View>

      <View style={styles.section}>
        <ChipSelect
          label={t("profileSetup.hasKids")}
          options={HAS_KIDS_KEYS}
          translatePrefix="profileSetup.hasKidsOption"
          value={hasKids}
          onChange={setHasKids}
        />
      </View>

      <View style={styles.section}>
        <MultiChipSelect
          label={t("profileSetup.interests")}
          options={interestOptions}
          translatePrefix="interests"
          values={interests}
          onChange={setInterests}
          max={MAX_INTERESTS}
        />
      </View>
      <View style={styles.section}>
        <MultiChipSelect
          label={t("profileSetup.languages")}
          options={languageOptions}
          translatePrefix="languages"
          values={languages}
          onChange={setLanguages}
        />
      </View>

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
  title: { fontSize: 24, fontWeight: "700", marginBottom: 4, marginTop: 24, color: colors.navy },
  verifyCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: colors.creamDeep,
    borderRadius: 14,
    padding: 16,
    marginTop: 16,
    marginBottom: 8,
  },
  verifyCardDone: { backgroundColor: "#E6F4EA" },
  verifyCardEmoji: { fontSize: 28 },
  verifyCardTextWrap: { flex: 1 },
  verifyCardTitle: { fontSize: 15, fontWeight: "700", color: colors.navy },
  verifyCardSubtitle: { fontSize: 12.5, color: colors.muted, marginTop: 2 },
  section: { marginTop: 20 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginTop: 28, marginBottom: 4 },
  error: { color: colors.danger, marginBottom: 12 },
  field: { marginTop: 20 },
  fieldLabel: { fontSize: 14, fontWeight: "600", marginBottom: 8, color: colors.muted },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: 10, padding: 14, fontSize: 16 },
  multiline: { minHeight: 80, textAlignVertical: "top" },
  lockedField: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    backgroundColor: colors.creamDeep,
  },
  lockedFieldText: { fontSize: 16, color: colors.ink },
  nameLockNote: { fontSize: 12.5, color: colors.muted, marginTop: 8, lineHeight: 18 },
  label: { fontSize: 14, fontWeight: "600", marginTop: 20, marginBottom: 8, color: colors.muted },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, alignItems: "center" },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff" },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 28, marginBottom: 24 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  premiumSection: { borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 20, marginBottom: 24 },
  premiumTitle: { fontSize: 18, fontWeight: "800", color: colors.navy, marginBottom: 8 },
  premiumLockedBody: { color: colors.muted, fontSize: 14, marginBottom: 16 },
  premiumSaveButton: { backgroundColor: colors.navy, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 16 },
});
