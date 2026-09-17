import { useState } from "react";
import { ActivityIndicator, Image, Pressable, ScrollView, Switch, Text, TextInput, View, StyleSheet } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
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
import PhotoCropEditor from "../../components/PhotoCropEditor";
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
import { BLIND_CHAT_CATEGORY_KEYS } from "../../constants/blindChatCategories";
import type { Gender, InterestedIn } from "../../types";
import { colors } from "../../theme";

const GENDERS: Gender[] = ["male", "female", "other"];
const INTERESTS: InterestedIn[] = ["male", "female", "all"];
const MAX_INTERESTS = 5;
const MAX_K_CONTENT_TAGS = 6;
const MAX_PHOTOS = 6;

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

// Which fields currently have a validation problem — drives the red
// highlight on each field in addition to the text error list, since a long
// form makes "which of these six things is wrong" hard to spot from text
// alone.
interface FieldErrors {
  photo?: boolean;
  name?: boolean;
  email?: boolean;
  birthDate?: boolean;
  bio?: boolean;
  location?: boolean;
  categories?: boolean;
}

interface Props {
  onComplete: () => void;
}

interface PhotoItem {
  uri: string;
  width: number;
  height: number;
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
  const [photos, setPhotos] = useState<PhotoItem[]>([]);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
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
  const [preferredCategories, setPreferredCategories] = useState<string[]>([]);

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});

  // Derived, never stored directly — always rebuilt from the three dropdowns
  // so there's a single source of truth (same convention as the phone-number
  // formatting on PhoneAuthScreen).
  const birthDate = birthYear && birthMonth && birthDay ? `${birthYear}-${birthMonth}-${birthDay}` : "";

  function clearFieldError(field: keyof FieldErrors) {
    setFieldErrors((prev) => (prev[field] ? { ...prev, [field]: false } : prev));
  }

  async function pickPhotos() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setErrors([t("profileSetup.photoPermission")]);
      return;
    }
    const remaining = MAX_PHOTOS - photos.length;
    if (remaining <= 0) return;
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsMultipleSelection: true,
      selectionLimit: remaining,
    });
    if (!result.canceled && result.assets.length > 0) {
      const picked = result.assets.map((a) => ({ uri: a.uri, width: a.width, height: a.height }));
      setPhotos((prev) => [...prev, ...picked].slice(0, MAX_PHOTOS));
      clearFieldError("photo");
    }
  }

  function removePhoto(uri: string) {
    setPhotos((prev) => prev.filter((p) => p.uri !== uri));
  }

  // No upload call to make yet at this point (photos aren't presigned/
  // confirmed until handleSubmit) — just swap the two entries in local
  // state, same left/right-arrow convention as ProfilePhotosGrid's
  // post-signup reorder, minus the network round-trip.
  function movePhoto(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= photos.length) return;
    setPhotos((prev) => {
      const next = prev.slice();
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function handleCropConfirm(result: { uri: string; width: number; height: number }) {
    setPhotos((prev) => {
      if (editingIndex == null) return prev;
      const next = prev.slice();
      next[editingIndex] = result;
      return next;
    });
    setEditingIndex(null);
  }

  function validate(): { messages: string[]; fields: FieldErrors } {
    const messages: string[] = [];
    const fields: FieldErrors = {};
    if (photos.length === 0) {
      messages.push(t("profileSetup.needPhoto"));
      fields.photo = true;
    }
    if (!name.trim()) {
      messages.push(t("profileSetup.nameRequired"));
      fields.name = true;
    }
    if (!isValidEmail(email)) {
      messages.push(t("profileSetup.invalidEmail"));
      fields.email = true;
    }
    if (!birthDate) {
      messages.push(t("profileSetup.birthDateRequired"));
      fields.birthDate = true;
    }
    if (!bio.trim()) {
      messages.push(t("profileSetup.bioRequired"));
      fields.bio = true;
    }
    if (locationLat == null || locationLng == null) {
      messages.push(t("profileSetup.needLocation"));
      fields.location = true;
    }
    if (preferredCategories.length === 0) {
      messages.push(t("profileSetup.categoriesRequired"));
      fields.categories = true;
    }
    return { messages, fields };
  }

  async function handleSubmit() {
    const { messages, fields } = validate();
    if (messages.length > 0) {
      setErrors(messages);
      setFieldErrors(fields);
      return;
    }

    setErrors([]);
    setFieldErrors({});
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
        preferred_categories: preferredCategories,
      });

      const contentType = "image/jpeg";
      await Promise.all(
        photos.map(async ({ uri }, position) => {
          const { upload_url, gcs_object_path } = await presignUpload(contentType, position);
          await uploadToPresignedUrl(upload_url, uri, contentType);
          await confirmPhoto(gcs_object_path, position);
        })
      );

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
  const categoryOptions = BLIND_CHAT_CATEGORY_KEYS as unknown as readonly string[];

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
        <Text style={styles.photoHint}>{t("profileSetup.photoHint", { max: MAX_PHOTOS })}</Text>
        <View style={[styles.photoGrid, fieldErrors.photo && styles.photoGridError]}>
          {photos.map((photo, index) => (
            <View key={photo.uri} style={styles.photoTileWrap}>
              <View style={styles.photoTile}>
                <Image source={{ uri: photo.uri }} style={styles.photoTileImage} />
                <Pressable style={styles.photoRemoveBadge} onPress={() => removePhoto(photo.uri)}>
                  <Text style={styles.photoRemoveBadgeText}>✕</Text>
                </Pressable>
                <Pressable style={styles.photoEditBadge} onPress={() => setEditingIndex(index)}>
                  <Ionicons name="crop" size={12} color="#fff" />
                </Pressable>
                {index === 0 && (
                  <View style={styles.photoPrimaryBadge}>
                    <Text style={styles.photoPrimaryBadgeText}>{t("photos.primary")}</Text>
                  </View>
                )}
              </View>
              {photos.length > 1 && (
                <View style={styles.moveRow}>
                  <Pressable
                    style={styles.moveButton}
                    onPress={() => movePhoto(index, -1)}
                    disabled={index === 0}
                    hitSlop={4}
                  >
                    <Ionicons name="chevron-back" size={14} color={index === 0 ? colors.border : colors.navy} />
                  </Pressable>
                  <Pressable
                    style={styles.moveButton}
                    onPress={() => movePhoto(index, 1)}
                    disabled={index === photos.length - 1}
                    hitSlop={4}
                  >
                    <Ionicons
                      name="chevron-forward"
                      size={14}
                      color={index === photos.length - 1 ? colors.border : colors.navy}
                    />
                  </Pressable>
                </View>
              )}
            </View>
          ))}
          {photos.length < MAX_PHOTOS && (
            <Pressable style={[styles.photoTile, styles.photoAddTile]} onPress={pickPhotos}>
              <Text style={styles.photoAddTileText}>+</Text>
            </Pressable>
          )}
        </View>

        <PhotoCropEditor
          visible={editingIndex != null}
          uri={editingIndex != null ? photos[editingIndex]?.uri ?? null : null}
          naturalWidth={editingIndex != null ? photos[editingIndex]?.width ?? 0 : 0}
          naturalHeight={editingIndex != null ? photos[editingIndex]?.height ?? 0 : 0}
          onCancel={() => setEditingIndex(null)}
          onConfirm={handleCropConfirm}
        />

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>
          {t("editProfile.name")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
        <TextInput
          style={[styles.input, fieldErrors.name && styles.inputError]}
          placeholder={t("editProfile.displayNamePlaceholder")}
          value={name}
          onChangeText={(v) => {
            setName(v);
            clearFieldError("name");
          }}
        />
        <Text style={styles.nameLockNote}>{t("editProfile.nameLockNote")}</Text>

        <Text style={[styles.fieldLabel, styles.fieldLabelSpaced]}>
          {t("profileSetup.email")}
          <Text style={styles.requiredStar}> *</Text>
        </Text>
        <TextInput
          style={[styles.input, fieldErrors.email && styles.inputError]}
          placeholder={t("profileSetup.emailPlaceholder")}
          value={email}
          onChangeText={(v) => {
            setEmail(v);
            clearFieldError("email");
          }}
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
              onPress={() => {
                setGender(g);
                // A sensible starting point for "interested in" — not a
                // lock, the user can still tap a different chip below.
                setInterestedIn(g === "male" ? "female" : g === "female" ? "male" : "all");
              }}
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
              onChange={(v) => {
                setBirthYear(v);
                clearFieldError("birthDate");
              }}
              error={fieldErrors.birthDate}
            />
          </View>
          <View style={styles.dateDropdown}>
            <SelectDropdown
              label={t("profileSetup.month")}
              placeholder={t("profileSetup.month")}
              options={MONTH_OPTIONS}
              value={birthMonth}
              onChange={(v) => {
                setBirthMonth(v);
                clearFieldError("birthDate");
              }}
              error={fieldErrors.birthDate}
            />
          </View>
          <View style={styles.dateDropdown}>
            <SelectDropdown
              label={t("profileSetup.day")}
              placeholder={t("profileSetup.day")}
              options={DAY_OPTIONS}
              value={birthDay}
              onChange={(v) => {
                setBirthDay(v);
                clearFieldError("birthDate");
              }}
              error={fieldErrors.birthDate}
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
          style={[styles.input, styles.multiline, fieldErrors.bio && styles.inputError]}
          placeholder={t("editProfile.bioPlaceholder")}
          value={bio}
          onChangeText={(v) => {
            setBio(v);
            clearFieldError("bio");
          }}
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

        <View style={styles.fieldGap}>
          <Text style={styles.fieldLabel}>
            {t("profileSetup.preferredCategoriesLabel")}
            <Text style={styles.requiredStar}> *</Text>
          </Text>
          <Text style={styles.photoHint}>{t("profileSetup.preferredCategoriesHint")}</Text>
          <MultiChipSelect
            label=""
            options={categoryOptions}
            translatePrefix="blindChatCategories"
            values={preferredCategories}
            onChange={(vals) => {
              setPreferredCategories(vals);
              clearFieldError("categories");
            }}
            error={fieldErrors.categories}
          />
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
            error={fieldErrors.location}
            lat={locationLat}
            lng={locationLng}
            onChange={(lat, lng) => {
              setLocationLat(lat);
              setLocationLng(lng);
              clearFieldError("location");
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

const PHOTO_TILE_SIZE = 96;

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
  photoHint: { fontSize: 12, color: colors.muted, marginBottom: 10 },
  photoGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: "transparent",
    padding: 2,
  },
  photoGridError: { borderColor: colors.danger },
  photoTileWrap: { alignItems: "center" },
  moveRow: { flexDirection: "row", gap: 4, marginTop: 4 },
  moveButton: {
    width: 22,
    height: 18,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  photoTile: {
    width: PHOTO_TILE_SIZE,
    height: PHOTO_TILE_SIZE,
    borderRadius: 10,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
  },
  photoTileImage: { width: "100%", height: "100%" },
  photoAddTile: { alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: colors.border, borderStyle: "dashed" },
  photoAddTileText: { fontSize: 30, color: colors.muted },
  photoRemoveBadge: {
    position: "absolute",
    top: 4,
    right: 4,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "rgba(11,59,99,0.7)",
    alignItems: "center",
    justifyContent: "center",
  },
  photoRemoveBadgeText: { color: "#fff", fontSize: 11 },
  photoEditBadge: {
    position: "absolute",
    top: 4,
    left: 4,
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: "rgba(226,145,77,0.9)",
    alignItems: "center",
    justifyContent: "center",
  },
  photoPrimaryBadge: {
    position: "absolute",
    bottom: 4,
    left: 4,
    backgroundColor: "rgba(226,145,77,0.9)",
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 6,
  },
  photoPrimaryBadgeText: { color: "#fff", fontSize: 9, fontWeight: "700" },
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
  nameLockNote: { fontSize: 12.5, color: colors.muted, marginTop: 6, lineHeight: 18 },
  ageHint: { fontSize: 12.5, color: colors.accentDark, fontWeight: "600", marginTop: 4 },
  multiline: { minHeight: 70, textAlignVertical: "top" },
  input: {
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
  },
  inputError: { borderColor: colors.danger },
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
