import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Switch, Text, TextInput, View, StyleSheet } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { useTranslation } from "react-i18next";

import { updateEmail } from "../../api/account";
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
import { K_CONTENT_KEYS } from "../../constants/kContentTags";
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "all"];
const MAX_INTERESTS = 5;
const MAX_K_CONTENT_TAGS = 6;

// Format check only — this email is collected for marketing outreach, never
// verified, so we just need to reject obvious typos before hitting the API.
function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());
}

// Signup is gated to 18-70 (matches the max age on the discovery/blind-chat
// age filters) — the year dropdown only ever offers birth years that land in
// that range, so there's no separate "must be 18+" check to run later.
const CURRENT_YEAR = new Date().getFullYear();
const MIN_SIGNUP_AGE = 18;
const MAX_SIGNUP_AGE = 70;
const YEAR_OPTIONS: DropdownOption[] = Array.from({ length: MAX_SIGNUP_AGE - MIN_SIGNUP_AGE + 1 }, (_, i) => {
  const year = CURRENT_YEAR - MIN_SIGNUP_AGE - i;
  return { key: String(year), label: String(year) };
});
const MONTH_OPTIONS: DropdownOption[] = Array.from({ length: 12 }, (_, i) => {
  const month = String(i + 1).padStart(2, "0");
  return { key: month, label: month };
});
const DAY_OPTIONS: DropdownOption[] = Array.from({ length: 31 }, (_, i) => {
  const day = String(i + 1).padStart(2, "0");
  return { key: day, label: day };
});

interface Props {
  onComplete: () => void;
}

export default function ProfileSetupScreen({ onComplete }: Props) {
  const { t } = useTranslation();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [birthYear, setBirthYear] = useState<string | null>(null);
  const [birthMonth, setBirthMonth] = useState<string | null>(null);
  const [birthDay, setBirthDay] = useState<string | null>(null);
  const [gender, setGender] = useState<Gender>("male");
  const [interestedIn, setInterestedIn] = useState<InterestedIn>("female");
  const [openToLanguageExchange, setOpenToLanguageExchange] = useState(false);
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
  const [exerciseFrequency, setExerciseFrequency] = useState<string | null>(null);
  const [relationshipGoal, setRelationshipGoal] = useState<string | null>(null);
  const [wantsKids, setWantsKids] = useState<string | null>(null);
  const [hasKids, setHasKids] = useState<string | null>(null);
  const [interests, setInterests] = useState<string[]>([]);
  const [kContentTags, setKContentTags] = useState<string[]>([]);
  const [languages, setLanguages] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  // Derived, never stored directly — always rebuilt from the three dropdowns
  // so there's a single source of truth (same convention as the phone-number
  // formatting on PhoneAuthScreen).
  const birthDate = birthYear && birthMonth && birthDay ? `${birthYear}-${birthMonth}-${birthDay}` : "";

  async function pickPhoto() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setErrors([t("profileSetup.photoPermission")]);
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

  function getValidationErrors(): string[] {
    const list: string[] = [];
    if (!photoUri) list.push(t("profileSetup.needPhoto"));
    if (!name.trim()) list.push(t("profileSetup.nameRequired"));
    if (!isValidEmail(email)) list.push(t("profileSetup.invalidEmail"));
    if (!birthDate) list.push(t("profileSetup.birthDateRequired"));
    if (!bio.trim()) list.push(t("profileSetup.bioRequired"));
    if (locationLat == null || locationLng == null) list.push(t("profileSetup.needLocation"));
    return list;
  }

  async function handleSubmit() {
    const validationErrors = getValidationErrors();
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors([]);
    setLoading(true);
    try {
      await updateEmail(email.trim());
      await updateMyProfile({
        // Same name shown to others and used for identity purposes — see
        // editProfile.nameLockNote, this is locked right after this screen.
        display_name: name.trim(),
        legal_first_name: name.trim(),
        birth_date: birthDate,
        gender,
        interested_in: interestedIn,
        open_to_language_exchange: openToLanguageExchange,
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
        exercise_frequency: exerciseFrequency,
        relationship_goal: relationshipGoal,
        wants_kids: wantsKids,
        has_kids: hasKids,
        interests,
        k_content_tags: kContentTags,
        languages,
      });

      const contentType = "image/jpeg";
      const { upload_url, gcs_object_path } = await presignUpload(contentType, 0);
      await uploadToPresignedUrl(upload_url, photoUri!, contentType);
      await confirmPhoto(gcs_object_path, 0);

      onComplete();
    } catch (e: any) {
      if (e?.response?.status === 409) {
        setErrors([t("profileSetup.emailInUse")]);
      } else {
        setErrors([e?.response?.data?.detail ?? e?.message ?? t("common.somethingWentWrong")]);
      }
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
  const kContentOptions = K_CONTENT_KEYS as unknown as readonly string[];

  const errorBox = errors.length > 0 && (
    <View style={styles.errorBox}>
      {errors.map((msg, i) => (
        <Text key={i} style={styles.errorText}>
          • {msg}
        </Text>
      ))}
    </View>
  );

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>{t("profileSetup.title")}</Text>

      {errorBox}

      {/* Grouped into the same section shape as EditProfileScreen
          (sectionBasicInfo/sectionAboutMe/sectionPreferences/optionalSection/
          sectionInterests) so the two screens read the same way and this one
          isn't just a flat, hard-to-scan list of fields. */}
      <Text style={styles.sectionTitle}>{t("editProfile.sectionBasicInfo")}</Text>
      <View style={styles.card}>
        <Text style={styles.fieldLabel}>
          {t("profileSetup.photoLabel")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
        <Pressable style={styles.photoPicker} onPress={pickPhoto}>
          {photoUri ? (
            <Image source={{ uri: photoUri }} style={styles.photo} />
          ) : (
            <Text style={styles.photoPickerText}>{t("profileSetup.addPhoto")}</Text>
          )}
        </Pressable>

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>
          {t("editProfile.name")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
        <TextInput
          style={styles.input}
          placeholder={t("editProfile.displayNamePlaceholder")}
          value={name}
          onChangeText={setName}
        />
        <Text style={styles.nameLockNote}>{t("editProfile.nameLockNote")}</Text>

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>
          {t("profileSetup.email")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
        <TextInput
          style={styles.input}
          placeholder={t("profileSetup.emailPlaceholder")}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="email-address"
          autoComplete="email"
        />
        <Text style={styles.nameLockNote}>{t("profileSetup.emailHint")}</Text>

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>{t("profileSetup.iAm")}</Text>
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

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>
          {t("profileSetup.birthDate")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
        <View style={styles.dateRow}>
          <View style={styles.dateDropdown}>
            <SelectDropdown
              label={t("profileSetup.year")}
              placeholder={t("profileSetup.year")}
              options={YEAR_OPTIONS}
              value={birthYear}
              onChange={setBirthYear}
            />
          </View>
          <View style={styles.dateDropdown}>
            <SelectDropdown
              label={t("profileSetup.month")}
              placeholder={t("profileSetup.month")}
              options={MONTH_OPTIONS}
              value={birthMonth}
              onChange={setBirthMonth}
            />
          </View>
          <View style={styles.dateDropdown}>
            <SelectDropdown
              label={t("profileSetup.day")}
              placeholder={t("profileSetup.day")}
              options={DAY_OPTIONS}
              value={birthDay}
              onChange={setBirthDay}
            />
          </View>
        </View>
        {ageFromBirthDate != null && (
          <Text style={styles.ageHint}>{t("editProfile.age", { age: ageFromBirthDate })}</Text>
        )}

        <View style={styles.fieldGap}>
          <HeightInput required valueCm={heightCm} onChange={setHeightCm} />
        </View>
      </View>

      <Text style={styles.sectionTitle}>{t("editProfile.sectionAboutMe")}</Text>
      <View style={styles.card}>
        <Text style={styles.fieldLabel}>
          {t("editProfile.bio")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
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
        <Text style={styles.fieldLabel}>{t("profileSetup.interestedIn")}</Text>
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

        <View style={[styles.switchRow, styles.fieldGap]}>
          <View style={styles.switchTextWrap}>
            <Text style={styles.switchLabel}>{t("editProfile.languageExchangeLabel")}</Text>
            <Text style={styles.switchHint}>{t("editProfile.languageExchangeHint")}</Text>
          </View>
          <Switch value={openToLanguageExchange} onValueChange={setOpenToLanguageExchange} trackColor={{ true: colors.navy }} />
        </View>

        <View style={styles.fieldGap}>
          <LocationPicker
            required
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
        <MultiChipSelect
          label={t("editProfile.kContentLabel")}
          options={kContentOptions}
          translatePrefix="kcontent"
          values={kContentTags}
          onChange={setKContentTags}
          max={MAX_K_CONTENT_TAGS}
        />
      </View>

      {errorBox}

      <Pressable style={styles.primaryButton} onPress={handleSubmit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryButtonText}>{t("profileSetup.continue")}</Text>}
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 24, backgroundColor: colors.white, flexGrow: 1 },
  title: { fontSize: 24, fontWeight: "700", marginBottom: 4, marginTop: 24, color: colors.navy },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: colors.navy, marginTop: 28, marginBottom: 10 },
  card: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 16,
  },
  fieldGap: { marginTop: 16 },
  errorBox: { marginBottom: 12, marginTop: 12 },
  errorText: { color: colors.danger, lineHeight: 20 },
  requiredStar: { color: colors.danger },
  photoPicker: {
    width: 140,
    height: 180,
    borderRadius: 12,
    backgroundColor: colors.creamDeep,
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "center",
    overflow: "hidden",
  },
  photo: { width: "100%", height: "100%" },
  photoPickerText: { color: colors.muted },
  fieldLabel: { fontSize: 14, fontWeight: "600", marginBottom: 8, color: colors.muted },
  fieldLabelSpaced: { marginTop: 16 },
  nameLockNote: { fontSize: 12.5, color: colors.muted, marginTop: -4, marginBottom: 4, lineHeight: 18 },
  ageHint: { fontSize: 12.5, color: colors.accentDark, fontWeight: "600", marginTop: 4 },
  multiline: { minHeight: 70, textAlignVertical: "top" },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
  },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  dateRow: { flexDirection: "row", gap: 8 },
  dateDropdown: { flex: 1 },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12 },
  switchTextWrap: { flex: 1 },
  switchLabel: { fontSize: 14, fontWeight: "600", color: colors.ink },
  switchHint: { fontSize: 12, color: colors.muted, marginTop: 3, lineHeight: 16 },
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
    marginTop: 16,
    marginBottom: 24,
  },
  primaryButtonText: { color: "#fff", fontSize: 16, fontWeight: "600" },
});
