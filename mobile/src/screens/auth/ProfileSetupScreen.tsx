import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useTranslation } from "react-i18next";

import { confirmPhoto, updateMyProfile } from "../../api/profiles";
import { presignUpload, uploadToPresignedUrl } from "../../api/uploads";
import ChipSelect from "../../components/ChipSelect";
import MultiChipSelect from "../../components/MultiChipSelect";
import LocationPicker from "../../components/LocationPicker";
import HeightInput from "../../components/HeightInput";
import SelectDropdown, { DropdownOption } from "../../components/SelectDropdown";
import CityAutocomplete from "../../components/CityAutocomplete";
import { calculateAge } from "../../utils/age";
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
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "all"];
const MAX_INTERESTS = 5;

interface Props {
  onComplete: () => void;
}

export default function ProfileSetupScreen({ onComplete }: Props) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState(""); // YYYY-MM-DD
  const [gender, setGender] = useState<Gender>("male");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [locationLat, setLocationLat] = useState<number | null>(null);
  const [locationLng, setLocationLng] = useState<number | null>(null);

  // Optional extended profile fields.
  const [bio, setBio] = useState("");
  const [bio2, setBio2] = useState("");
  const [bio3, setBio3] = useState("");
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
    if (!name.trim() || !/^\d{4}-\d{2}-\d{2}$/.test(birthDate)) {
      setError(t("profileSetup.validationMissing"));
      return;
    }
    if (!photoUri) {
      setError(t("profileSetup.needPhoto"));
      return;
    }
    if (locationLat == null || locationLng == null) {
      setError(t("profileSetup.needLocation"));
      return;
    }

    setError(null);
    setLoading(true);
    try {
      await updateMyProfile({
        // Same name shown to others and used for identity purposes — see
        // editProfile.nameLockNote, this is locked right after this screen.
        display_name: name.trim(),
        legal_first_name: name.trim(),
        birth_date: birthDate,
        gender,
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

  const ageFromBirthDate = calculateAge(birthDate);

  const educationOptions: DropdownOption[] = EDUCATION_KEYS.map((key) => ({
    key,
    label: t(`profileSetup.educationOption.${key}`),
  }));
  const interestOptions = INTEREST_KEYS as unknown as readonly string[];
  const languageOptions = LANGUAGE_KEYS as unknown as readonly string[];

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

      <Text style={styles.fieldLabel}>{t("editProfile.name")}</Text>
      <TextInput
        style={styles.input}
        placeholder={t("editProfile.displayNamePlaceholder")}
        value={name}
        onChangeText={setName}
      />
      <Text style={styles.nameLockNote}>{t("editProfile.nameLockNote")}</Text>

      <Text style={styles.fieldLabel}>{t("profileSetup.birthDate")}</Text>
      <TextInput
        style={styles.input}
        placeholder={t("profileSetup.birthDate")}
        value={birthDate}
        onChangeText={setBirthDate}
      />
      {ageFromBirthDate != null && (
        <Text style={styles.ageHint}>{t("editProfile.age", { age: ageFromBirthDate })}</Text>
      )}

      <Text style={styles.fieldLabel}>{t("editProfile.bio")}</Text>
      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder={t("editProfile.bioPlaceholder")}
        value={bio}
        onChangeText={setBio}
        multiline
      />
      <Text style={styles.fieldLabel}>{t("editProfile.bio2")}</Text>
      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder={t("editProfile.bio2Placeholder")}
        value={bio2}
        onChangeText={setBio2}
        multiline
      />
      <Text style={styles.fieldLabel}>{t("editProfile.bio3")}</Text>
      <TextInput
        style={[styles.input, styles.multiline]}
        placeholder={t("editProfile.bio3Placeholder")}
        value={bio3}
        onChangeText={setBio3}
        multiline
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

      <HeightInput valueCm={heightCm} onChange={setHeightCm} />

      <Text style={styles.fieldLabel}>{t("profileSetup.occupation")}</Text>
      <TextInput
        style={styles.input}
        placeholder={t("editProfile.occupationPlaceholder")}
        value={occupation}
        onChangeText={setOccupation}
      />
      <SelectDropdown
        label={t("profileSetup.education")}
        placeholder={t("profileSetup.education")}
        options={educationOptions}
        value={education}
        onChange={setEducation}
      />
      <CityAutocomplete
        label={t("profileSetup.hometown")}
        placeholder={t("editProfile.hometownPlaceholder")}
        value={hometown}
        onChange={setHometown}
      />

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

      <Pressable style={styles.primaryButton} onPress={handleSubmit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("profileSetup.continue")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: colors.white, flexGrow: 1 },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 24, marginTop: 24, color: colors.navy },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginTop: 24, marginBottom: 4 },
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
  fieldLabel: { fontSize: 14, fontWeight: "600", marginTop: 12, marginBottom: 8, color: colors.muted },
  nameLockNote: { fontSize: 12.5, color: colors.muted, marginTop: -4, marginBottom: 8, lineHeight: 18 },
  ageHint: { fontSize: 12.5, color: colors.accentDark, fontWeight: "600", marginTop: -8, marginBottom: 8 },
  multiline: { minHeight: 70, textAlignVertical: "top" },
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
