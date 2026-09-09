import { useEffect, useState } from "react";
import { ActivityIndicator, Modal, Pressable, ScrollView, Switch, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useTranslation } from "react-i18next";

import { getMyProfile, setAgeFilter, setBasicFilters, setPremiumFilters } from "../api/profiles";
import { useAuthStore } from "../store/authStore";
import { env } from "../config/env";
import { showAlert } from "../utils/alert";
import { openExternalUrl } from "../utils/openExternalUrl";
import MultiChipSelect from "./MultiChipSelect";
import MultiSelectDropdown from "./MultiSelectDropdown";
import RangeSlider from "./RangeSlider";
import SingleSlider from "./SingleSlider";
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
} from "../constants/demographicOptions";
import { INTEREST_KEYS, LANGUAGE_KEYS } from "../constants/interestsAndLanguages";
import { K_CONTENT_KEYS } from "../constants/kContentTags";
import { colors } from "../theme";
import { formatHeightCm, formatDistanceKm } from "../utils/units";

interface Props {
  visible: boolean;
  onClose: () => void;
}

/** Free (Basic tab): age and distance range/cap, ethnicity, languages,
 * interests, photo-verified-only, language-exchange-only, and the two "if
 * I run out" fallback toggles. Premium (Advanced tab): height, religion,
 * political view, exercise, smoking, cannabis, relationship goal, wants/
 * has kids. Height is still saved via setBasicFilters (a free endpoint —
 * see routers/profiles.py::set_basic_filters) even though its control now
 * lives on this premium-gated tab; moving it here is a pure UI decision,
 * not a backend one, so no schema change was needed for it. */
export default function FilterModal({ visible, onClose }: Props) {
  const { t, i18n } = useTranslation();
  const useImperial = i18n.language === "en";
  const insets = useSafeAreaInsets();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile, enabled: visible });
  const isPremium = profile?.is_premium_member ?? false;

  const [tab, setTab] = useState<"basic" | "advanced">("basic");
  const [minAge, setMinAge] = useState(18);
  const [maxAge, setMaxAge] = useState(99);
  const [heightMin, setHeightMin] = useState(140);
  const [heightMax, setHeightMax] = useState(210);
  const [maxDistanceKm, setMaxDistanceKm] = useState(50);
  const [raceFilter, setRaceFilter] = useState<string[]>([]);
  const [languagesFilter, setLanguagesFilter] = useState<string[]>([]);
  const [interestsFilter, setInterestsFilter] = useState<string[]>([]);
  const [kContentFilter, setKContentFilter] = useState<string[]>([]);
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [languageExchangeOnly, setLanguageExchangeOnly] = useState(false);
  const [expandDistanceIfLow, setExpandDistanceIfLow] = useState(true);
  const [expandOthersIfLow, setExpandOthersIfLow] = useState(true);
  const [religionFilter, setReligionFilter] = useState<string[]>([]);
  const [politicalViewFilter, setPoliticalViewFilter] = useState<string[]>([]);
  const [exerciseFrequencyFilter, setExerciseFrequencyFilter] = useState<string[]>([]);
  const [smokingFilter, setSmokingFilter] = useState<string[]>([]);
  const [cannabisFilter, setCannabisFilter] = useState<string[]>([]);
  const [relationshipGoalFilter, setRelationshipGoalFilter] = useState<string[]>([]);
  const [wantsKidsFilter, setWantsKidsFilter] = useState<string[]>([]);
  const [hasKidsFilter, setHasKidsFilter] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  // Re-sync local state from the server every time the modal opens, so a
  // change saved elsewhere isn't stale here.
  useEffect(() => {
    if (!visible || !profile) return;
    setMinAge(profile.min_age_pref);
    setMaxAge(profile.max_age_pref);
    setHeightMin(profile.height_filter_min ?? 140);
    setHeightMax(profile.height_filter_max ?? 210);
    setMaxDistanceKm(profile.max_distance_km);
    setRaceFilter(profile.race_filter);
    setLanguagesFilter(profile.languages_filter);
    setInterestsFilter(profile.interests_filter);
    setKContentFilter(profile.k_content_filter);
    setVerifiedOnly(profile.verified_only);
    setLanguageExchangeOnly(profile.language_exchange_only);
    setExpandDistanceIfLow(profile.expand_distance_if_low);
    setExpandOthersIfLow(profile.expand_others_if_low);
    setReligionFilter(profile.religion_filter);
    setPoliticalViewFilter(profile.premium_filters.political_view_filter);
    setExerciseFrequencyFilter(profile.premium_filters.exercise_frequency_filter);
    setSmokingFilter(profile.premium_filters.smoking_filter);
    setCannabisFilter(profile.premium_filters.cannabis_filter);
    setRelationshipGoalFilter(profile.premium_filters.relationship_goal_filter);
    setWantsKidsFilter(profile.premium_filters.wants_kids_filter);
    setHasKidsFilter(profile.premium_filters.has_kids_filter);
  }, [visible, profile]);

  function openShop() {
    const shopUrl = env.marketingSiteUrl + "/shop.html?token=" + encodeURIComponent(accessToken ?? "");
    openExternalUrl(shopUrl);
  }

  const raceOptions = RACE_ETHNICITY_KEYS.map((key) => ({ key, label: t(`profileSetup.race.${key}`) }));
  const languageOptions = LANGUAGE_KEYS.map((key) => ({ key, label: t(`languages.${key}`) }));
  const interestOptions = INTEREST_KEYS.map((key) => ({ key, label: t(`interests.${key}`) }));
  const kContentOptions = K_CONTENT_KEYS.map((key) => ({ key, label: t(`kcontent.${key}`) }));

  async function handleSave() {
    setSaving(true);
    try {
      await setAgeFilter(minAge, maxAge);
      await setBasicFilters({
        max_distance_km: maxDistanceKm,
        race_filter: raceFilter,
        height_min: heightMin,
        height_max: heightMax,
        languages_filter: languagesFilter,
        interests_filter: interestsFilter,
        k_content_filter: kContentFilter,
        verified_only: verifiedOnly,
        language_exchange_only: languageExchangeOnly,
        expand_distance_if_low: expandDistanceIfLow,
        expand_others_if_low: expandOthersIfLow,
      });
      if (isPremium) {
        await setPremiumFilters({
          religion_filter: religionFilter,
          political_view_filter: politicalViewFilter,
          exercise_frequency_filter: exerciseFrequencyFilter,
          smoking_filter: smokingFilter,
          cannabis_filter: cannabisFilter,
          relationship_goal_filter: relationshipGoalFilter,
          wants_kids_filter: wantsKidsFilter,
          has_kids_filter: hasKidsFilter,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
      // New filters only matter to a fresh fetch, not the already-loaded deck.
      await queryClient.invalidateQueries({ queryKey: ["candidates"] });
      await queryClient.invalidateQueries({ queryKey: ["recommended"] });
      onClose();
    } catch (e: any) {
      showAlert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.container}>
        <View style={[styles.header, { paddingTop: insets.top + 10 }]}>
          <Pressable onPress={onClose} hitSlop={8}>
            <Ionicons name="close" size={26} color={colors.ink} />
          </Pressable>
          <Text style={styles.title}>{t("filters.title")}</Text>
          <View style={styles.headerSpacer} />
        </View>

        <View style={styles.tabRow}>
          <Pressable style={[styles.tabPill, tab === "basic" && styles.tabPillActive]} onPress={() => setTab("basic")}>
            <Text style={[styles.tabPillText, tab === "basic" && styles.tabPillTextActive]}>{t("filters.basicTab")}</Text>
          </Pressable>
          <Pressable style={[styles.tabPill, tab === "advanced" && styles.tabPillActive]} onPress={() => setTab("advanced")}>
            <Text style={[styles.tabPillText, tab === "advanced" && styles.tabPillTextActive]}>{t("filters.advancedTab")}</Text>
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.content}>
          {tab === "basic" ? (
            <>
              <View style={styles.card}>
                <RangeSlider
                  label={t("filters.ageLabel")}
                  min={18}
                  max={99}
                  valueMin={minAge}
                  valueMax={maxAge}
                  onChange={(lo, hi) => {
                    setMinAge(lo);
                    setMaxAge(hi);
                  }}
                />
                <SingleSlider
                  label={t("filters.distanceLabel")}
                  min={1}
                  max={500}
                  value={maxDistanceKm}
                  formatValue={(v) =>
                    useImperial ? t("filters.distanceUpToMi", { mi: formatDistanceKm(v) }) : t("filters.distanceUpToKm", { km: v })
                  }
                  onChange={setMaxDistanceKm}
                />

                <View style={styles.switchRow}>
                  <Text style={styles.switchLabel}>{t("filters.expandDistanceTitle")}</Text>
                  <Switch value={expandDistanceIfLow} onValueChange={setExpandDistanceIfLow} trackColor={{ true: colors.navy }} />
                </View>
                <View style={styles.switchRow}>
                  <Text style={styles.switchLabel}>{t("filters.expandOthersTitle")}</Text>
                  <Switch value={expandOthersIfLow} onValueChange={setExpandOthersIfLow} trackColor={{ true: colors.navy }} />
                </View>
                <Text style={styles.switchHint}>{t("filters.expandBody")}</Text>
              </View>

              <View style={styles.card}>
                <MultiSelectDropdown
                  label={t("filters.ethnicityLabel")}
                  placeholder={t("filters.ethnicityPlaceholder")}
                  options={raceOptions}
                  values={raceFilter}
                  onChange={setRaceFilter}
                />
                <MultiSelectDropdown
                  label={t("filters.languagesLabel")}
                  placeholder={t("filters.languagesPlaceholder")}
                  options={languageOptions}
                  values={languagesFilter}
                  onChange={setLanguagesFilter}
                />
                <MultiSelectDropdown
                  label={t("filters.interestsLabel")}
                  placeholder={t("filters.interestsPlaceholder")}
                  options={interestOptions}
                  values={interestsFilter}
                  onChange={setInterestsFilter}
                />
                <MultiSelectDropdown
                  label={t("filters.kContentLabel")}
                  placeholder={t("filters.kContentPlaceholder")}
                  options={kContentOptions}
                  values={kContentFilter}
                  onChange={setKContentFilter}
                />
                <View style={styles.switchRow}>
                  <Text style={styles.switchLabel}>{t("filters.verifiedOnlyLabel")}</Text>
                  <Switch value={verifiedOnly} onValueChange={setVerifiedOnly} trackColor={{ true: colors.navy }} />
                </View>
                <Text style={styles.switchHint}>{t("filters.verifiedOnlyBody")}</Text>

                <View style={styles.switchRow}>
                  <Text style={styles.switchLabel}>{t("filters.languageExchangeOnlyLabel")}</Text>
                  <Switch value={languageExchangeOnly} onValueChange={setLanguageExchangeOnly} trackColor={{ true: colors.navy }} />
                </View>
                <Text style={styles.switchHint}>{t("filters.languageExchangeOnlyBody")}</Text>
              </View>
            </>
          ) : isPremium ? (
            <View style={styles.card}>
              <RangeSlider
                label={t("filters.heightLabel")}
                min={50}
                max={272}
                valueMin={heightMin}
                valueMax={heightMax}
                step={useImperial ? 3 : 1}
                formatValue={(v) => (useImperial ? formatHeightCm(v) : t("profileDetail.heightValue", { cm: v }))}
                onChange={(lo, hi) => {
                  setHeightMin(lo);
                  setHeightMax(hi);
                }}
              />
              <MultiChipSelect label={t("profileSetup.religion")} options={RELIGION_KEYS} translatePrefix="profileSetup.religionOption" values={religionFilter} onChange={setReligionFilter} />
              <MultiChipSelect label={t("profileSetup.politicalView")} options={POLITICAL_VIEW_KEYS} translatePrefix="profileSetup.politicalViewOption" values={politicalViewFilter} onChange={setPoliticalViewFilter} />
              <MultiChipSelect label={t("profileSetup.exerciseFrequency")} options={EXERCISE_FREQUENCY_KEYS} translatePrefix="profileSetup.exerciseFrequencyOption" values={exerciseFrequencyFilter} onChange={setExerciseFrequencyFilter} />
              <MultiChipSelect label={t("profileSetup.smoking")} options={SMOKING_KEYS} translatePrefix="profileSetup.smokingOption" values={smokingFilter} onChange={setSmokingFilter} />
              <MultiChipSelect label={t("profileSetup.cannabis")} options={CANNABIS_KEYS} translatePrefix="profileSetup.cannabisOption" values={cannabisFilter} onChange={setCannabisFilter} />
              <MultiChipSelect label={t("profileSetup.relationshipGoal")} options={RELATIONSHIP_GOAL_KEYS} translatePrefix="profileSetup.relationshipGoalOption" values={relationshipGoalFilter} onChange={setRelationshipGoalFilter} />
              <MultiChipSelect label={t("profileSetup.wantsKids")} options={WANTS_KIDS_KEYS} translatePrefix="profileSetup.wantsKidsOption" values={wantsKidsFilter} onChange={setWantsKidsFilter} />
              <MultiChipSelect label={t("profileSetup.hasKids")} options={HAS_KIDS_KEYS} translatePrefix="profileSetup.hasKidsOption" values={hasKidsFilter} onChange={setHasKidsFilter} />
            </View>
          ) : (
            <View style={styles.lockedCard}>
              <Ionicons name="lock-closed" size={28} color={colors.accentDark} />
              <Text style={styles.lockedTitle}>{t("filters.premiumLockedTitle")}</Text>
              <Text style={styles.lockedBody}>{t("filters.premiumLockedBody")}</Text>
            </View>
          )}
        </ScrollView>

        <View style={styles.footer}>
          {tab === "advanced" && !isPremium ? (
            <Pressable style={styles.saveButton} onPress={openShop}>
              <Text style={styles.saveButtonText}>{t("filters.upgrade")}</Text>
            </Pressable>
          ) : (
            <Pressable style={styles.saveButton} onPress={handleSave} disabled={saving}>
              {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>{t("filters.apply")}</Text>}
            </Pressable>
          )}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  title: { fontSize: 18, fontWeight: "800", color: colors.navy },
  // Balances the close icon on the left so the centered title actually
  // sits in the header's true center rather than looking off-center.
  headerSpacer: { width: 26 },
  tabRow: { flexDirection: "row", justifyContent: "center", gap: 8, paddingBottom: 16, paddingHorizontal: 20 },
  tabPill: { borderRadius: 999, paddingVertical: 9, paddingHorizontal: 18, backgroundColor: colors.creamDeep },
  tabPillActive: { backgroundColor: colors.navy },
  tabPillText: { fontSize: 13.5, fontWeight: "700", color: colors.ink },
  tabPillTextActive: { color: "#fff" },
  content: { padding: 20, paddingTop: 14, gap: 16, borderTopWidth: 1, borderTopColor: colors.border },
  card: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 16,
  },
  switchRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: 14 },
  switchLabel: { fontSize: 14, fontWeight: "600", color: colors.ink, flex: 1, marginRight: 12 },
  switchHint: { fontSize: 12, color: colors.muted, marginTop: 6, lineHeight: 17 },
  lockedCard: {
    backgroundColor: colors.creamDeep,
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    gap: 8,
  },
  lockedTitle: { fontSize: 16, fontWeight: "800", color: colors.navy, marginTop: 4 },
  lockedBody: { fontSize: 13, color: colors.muted, textAlign: "center" },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: colors.border },
  saveButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  saveButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
