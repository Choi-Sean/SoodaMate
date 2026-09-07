import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { showAlert } from "../../utils/alert";
import { getMyProfile, updateMyProfile } from "../../api/profiles";
import ChipSelect from "../../components/ChipSelect";
import MultiChipSelect from "../../components/MultiChipSelect";
import LocationPicker from "../../components/LocationPicker";
import SelectDropdown, { DropdownOption } from "../../components/SelectDropdown";
import ProfilePhotosGrid from "../../components/ProfilePhotosGrid";
import VerifiedBadge from "../../components/VerifiedBadge";
import ProfileCompletenessBar from "../../components/ProfileCompletenessBar";
import HeightInput from "../../components/HeightInput";
import CityAutocomplete from "../../components/CityAutocomplete";
import { calculateProfileCompleteness } from "../../utils/profileCompleteness";
import { calculateAge, formatDate } from "../../utils/age";
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
import type { ProfileStackParamList } from "../../navigation/ProfileStack";
import type { InterestedIn } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ProfileStackParamList, "EditProfile">;

const INTERESTS: InterestedIn[] = ["male", "female", "all"];
const MAX_INTERESTS = 5;

export default function EditProfileScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const { data: profile, isLoading } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile });

  const [bio, setBio] = useState("");
  const [bio2, setBio2] = useState("");
  const [bio3, setBio3] = useState("");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
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

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profile) return;
    setBio(profile.bio ?? "");
    setBio2(profile.bio2 ?? "");
    setBio3(profile.bio3 ?? "");
    setInterestedIn(profile.interested_in === "other" ? "all" : profile.interested_in);
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
    // Older profiles (seeded/saved before INTEREST_KEYS/LANGUAGE_KEYS
    // existed) can still hold free-text values like "여행" instead of the
    // canonical key "travel" — MultiChipSelect highlights a chip via
    // values.includes(key), so a stored value that matches no key renders
    // as "selected but nothing highlighted" (the count still reflects the
    // raw array length). Dropping unrecognized values here keeps the count
    // and the highlighted chips honest; saving afterwards naturally
    // rewrites the stored value to only ever contain valid keys.
    setInterests(profile.interests.filter((key) => (INTEREST_KEYS as readonly string[]).includes(key)));
    setLanguages(profile.languages.filter((key) => (LANGUAGE_KEYS as readonly string[]).includes(key)));
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
        // Locked after signup (see lockedInfoNote below) — sent back
        // unchanged; the backend also ignores any attempt to change these
        // on an existing profile, this just keeps the payload honest.
        display_name: profile.display_name,
        legal_first_name: profile.legal_first_name,
        birth_date: profile.birth_date,
        gender: profile.gender,
        interested_in: interestedIn,
        bio: bio.trim() || null,
        bio2: bio2.trim() || null,
        bio3: bio3.trim() || null,
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
        // Not editable on this screen anymore (age/distance now live only
        // in the Swipe tab's Filters modal) — round-tripped unchanged so
        // this full-replace PUT doesn't reset them to schema defaults.
        min_age_pref: profile.min_age_pref,
        max_age_pref: profile.max_age_pref,
        max_distance_km: profile.max_distance_km,
      });
      await refreshProfile();
      navigation.goBack();
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong"));
    } finally {
      setSaving(false);
    }
  }

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

  const age = calculateAge(profile.birth_date);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {error && <Text style={styles.error}>{error}</Text>}

      <ProfilePhotosGrid photos={profile.photos} onChanged={refreshProfile} />

      <ProfileCompletenessBar percent={calculateProfileCompleteness(profile)} />

      <Pressable
        style={[styles.verifyCard, profile.face_verified && styles.verifyCardDone]}
        onPress={() => !profile.face_verified && navigation.navigate("FaceVerification")}
      >
        {profile.face_verified ? (
          <VerifiedBadge size={30} />
        ) : (
          <Ionicons name="shield-checkmark-outline" size={28} color={colors.accentDark} />
        )}
        <View style={styles.verifyCardTextWrap}>
          <Text style={styles.verifyCardTitle}>
            {profile.face_verified ? t("faceVerification.verifiedBanner") : t("faceVerification.cardTitle")}
          </Text>
          {!profile.face_verified && <Text style={styles.verifyCardSubtitle}>{t("faceVerification.cardSubtitle")}</Text>}
        </View>
        {!profile.face_verified && <Ionicons name="chevron-forward" size={18} color={colors.accentDark} />}
      </Pressable>

      <Text style={styles.sectionTitle}>{t("editProfile.sectionBasicInfo")}</Text>
      <View style={styles.card}>
        <Text style={styles.fieldLabel}>{t("editProfile.name")}</Text>
        <View style={styles.lockedField}>
          <Text style={styles.lockedFieldText}>{profile.display_name}</Text>
          <Ionicons name="lock-closed" size={14} color={colors.muted} />
        </View>

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{t("editProfile.iAm")}</Text>
        <View style={styles.lockedField}>
          <Text style={styles.lockedFieldText}>{t(`profileSetup.${profile.gender}`)}</Text>
          <Ionicons name="lock-closed" size={14} color={colors.muted} />
        </View>

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{t("editProfile.birthDate")}</Text>
        <View style={styles.lockedField}>
          <Text style={styles.lockedFieldText}>
            {formatDate(profile.birth_date, i18n.language)}
            {age != null ? `  ·  ${t("editProfile.age", { age })}` : ""}
          </Text>
          <Ionicons name="lock-closed" size={14} color={colors.muted} />
        </View>

        <Text style={styles.nameLockNote}>{t("editProfile.lockedInfoNote")}</Text>
      </View>

      <Text style={styles.sectionTitle}>{t("editProfile.sectionAboutMe")}</Text>
      <View style={styles.card}>
        <Text style={styles.fieldLabel}>{t("editProfile.bio")}</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder={t("editProfile.bioPlaceholder")}
          value={bio}
          onChangeText={setBio}
          multiline
        />
        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{t("editProfile.bio2")}</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder={t("editProfile.bio2Placeholder")}
          value={bio2}
          onChangeText={setBio2}
          multiline
        />
        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{t("editProfile.bio3")}</Text>
        <TextInput
          style={[styles.input, styles.multiline]}
          placeholder={t("editProfile.bio3Placeholder")}
          value={bio3}
          onChangeText={setBio3}
          multiline
        />
      </View>

      <Text style={styles.sectionTitle}>{t("editProfile.sectionPreferences")}</Text>
      <View style={styles.card}>
        <Text style={styles.fieldLabel}>{t("editProfile.interestedIn")}</Text>
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

        <View style={styles.fieldGap}>
          <LocationPicker
            lat={locationLat}
            lng={locationLng}
            onChange={(lat, lng) => {
              setLocationLat(lat);
              setLocationLng(lng);
            }}
          />
        </View>
      </View>

      <Text style={styles.sectionTitle}>{t("profileSetup.optionalSection")}</Text>
      <View style={styles.card}>
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

        <View style={styles.fieldGap}>
          <HeightInput valueCm={heightCm} onChange={setHeightCm} />
        </View>

        <View style={styles.fieldGap}>
          <Text style={styles.fieldLabel}>{t("profileSetup.occupation")}</Text>
          <TextInput
            style={styles.input}
            placeholder={t("editProfile.occupationPlaceholder")}
            value={occupation}
            onChangeText={setOccupation}
          />
        </View>

        <View style={styles.fieldGap}>
          <SelectDropdown
            label={t("profileSetup.education")}
            placeholder={t("profileSetup.education")}
            options={educationOptions}
            value={education}
            onChange={setEducation}
          />
        </View>

        <View style={styles.fieldGap}>
          <CityAutocomplete
            label={t("profileSetup.hometown")}
            placeholder={t("editProfile.hometownPlaceholder")}
            value={hometown}
            onChange={setHometown}
          />
        </View>

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
      </View>

      <Text style={styles.sectionTitle}>{t("editProfile.sectionInterests")}</Text>
      <View style={styles.card}>
        <MultiChipSelect
          label={t("profileSetup.interests")}
          options={interestOptions}
          translatePrefix="interests"
          values={interests}
          onChange={setInterests}
          max={MAX_INTERESTS}
        />
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
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, flexGrow: 1, backgroundColor: colors.white, paddingTop: 0 },
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
  verifyCardTextWrap: { flex: 1 },
  verifyCardTitle: { fontSize: 15, fontWeight: "700", color: colors.navy },
  verifyCardSubtitle: { fontSize: 12.5, color: colors.muted, marginTop: 2 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginTop: 28, marginBottom: 10 },
  card: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 16,
  },
  fieldGap: { marginTop: 16 },
  error: { color: colors.danger, marginBottom: 12 },
  fieldLabel: { fontSize: 14, fontWeight: "600", marginBottom: 8, color: colors.muted },
  fieldLabelSpaced: { marginTop: 16 },
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
  lockedFieldText: { fontSize: 16, color: colors.ink, flex: 1, marginRight: 8 },
  nameLockNote: { fontSize: 12.5, color: colors.muted, marginTop: 12, lineHeight: 18 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8, alignItems: "center" },
  chip: { borderWidth: 1, borderColor: colors.border, borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 },
  chipSelected: { backgroundColor: colors.accent, borderColor: colors.accent },
  chipText: { color: colors.ink },
  chipTextSelected: { color: "#fff" },
  primaryButton: { backgroundColor: colors.accent, borderRadius: 10, padding: 14, alignItems: "center", marginTop: 28, marginBottom: 24 },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
