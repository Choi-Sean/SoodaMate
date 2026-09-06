import { useEffect, useState } from "react";
import { ActivityIndicator, Alert, Linking, Modal, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { getMyProfile, setAgeFilter, setPremiumFilters } from "../api/profiles";
import { useAuthStore } from "../store/authStore";
import { env } from "../config/env";
import MultiChipSelect from "./MultiChipSelect";
import NumberStepper from "./NumberStepper";
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
import { colors } from "../theme";

interface Props {
  visible: boolean;
  onClose: () => void;
}

/** Free: age range only. Premium: age range plus every other filterable
 * dimension (everything with a fixed option set — free-text fields like
 * occupation/education/hometown aren't filterable). */
export default function FilterModal({ visible, onClose }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const { data: profile } = useQuery({ queryKey: ["myProfile"], queryFn: getMyProfile, enabled: visible });
  const isPremium = profile?.is_premium_member ?? false;

  const [minAge, setMinAge] = useState(18);
  const [maxAge, setMaxAge] = useState(99);
  const [heightMin, setHeightMin] = useState(140);
  const [heightMax, setHeightMax] = useState(210);
  const [raceFilter, setRaceFilter] = useState<string[]>([]);
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
  // change saved elsewhere (e.g. EditProfileScreen's race/religion chips)
  // isn't stale here.
  useEffect(() => {
    if (!visible || !profile) return;
    setMinAge(profile.min_age_pref);
    setMaxAge(profile.max_age_pref);
    setHeightMin(profile.premium_filters.height_min ?? 140);
    setHeightMax(profile.premium_filters.height_max ?? 210);
    setRaceFilter(profile.race_filter);
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
    Linking.openURL(shopUrl);
  }

  async function handleSave() {
    setSaving(true);
    try {
      await setAgeFilter(minAge, maxAge);
      if (isPremium) {
        await setPremiumFilters({
          race_filter: raceFilter,
          religion_filter: religionFilter,
          political_view_filter: politicalViewFilter,
          exercise_frequency_filter: exerciseFrequencyFilter,
          smoking_filter: smokingFilter,
          cannabis_filter: cannabisFilter,
          relationship_goal_filter: relationshipGoalFilter,
          wants_kids_filter: wantsKidsFilter,
          has_kids_filter: hasKidsFilter,
          height_min: heightMin,
          height_max: heightMax,
        });
      }
      await queryClient.invalidateQueries({ queryKey: ["myProfile"] });
      // New filters only matter to a fresh fetch, not the already-loaded deck.
      await queryClient.invalidateQueries({ queryKey: ["candidates"] });
      await queryClient.invalidateQueries({ queryKey: ["recommended"] });
      onClose();
    } catch (e: any) {
      Alert.alert(t("common.somethingWentWrong"), e?.response?.data?.detail ?? e?.message ?? "");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.title}>{t("filters.title")}</Text>
          <Pressable onPress={onClose} hitSlop={8}>
            <Ionicons name="close" size={26} color={colors.ink} />
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.content}>
          <View style={styles.card}>
            <NumberStepper label={t("filters.minAge")} value={minAge} min={18} max={maxAge} onChange={setMinAge} />
            <NumberStepper label={t("filters.maxAge")} value={maxAge} min={minAge} max={99} onChange={setMaxAge} />
          </View>

          {isPremium ? (
            <>
              <View style={styles.card}>
                <NumberStepper
                  label={t("filters.minHeight")}
                  value={heightMin}
                  min={50}
                  max={heightMax}
                  formatValue={(v) => t("profileDetail.heightValue", { cm: v })}
                  onChange={setHeightMin}
                />
                <NumberStepper
                  label={t("filters.maxHeight")}
                  value={heightMax}
                  min={heightMin}
                  max={272}
                  formatValue={(v) => t("profileDetail.heightValue", { cm: v })}
                  onChange={setHeightMax}
                />
              </View>

              <View style={styles.card}>
                <MultiChipSelect label={t("profileSetup.raceEthnicity")} options={RACE_ETHNICITY_KEYS} translatePrefix="profileSetup.race" values={raceFilter} onChange={setRaceFilter} />
                <MultiChipSelect label={t("profileSetup.religion")} options={RELIGION_KEYS} translatePrefix="profileSetup.religionOption" values={religionFilter} onChange={setReligionFilter} />
                <MultiChipSelect label={t("profileSetup.politicalView")} options={POLITICAL_VIEW_KEYS} translatePrefix="profileSetup.politicalViewOption" values={politicalViewFilter} onChange={setPoliticalViewFilter} />
                <MultiChipSelect label={t("profileSetup.exerciseFrequency")} options={EXERCISE_FREQUENCY_KEYS} translatePrefix="profileSetup.exerciseFrequencyOption" values={exerciseFrequencyFilter} onChange={setExerciseFrequencyFilter} />
                <MultiChipSelect label={t("profileSetup.smoking")} options={SMOKING_KEYS} translatePrefix="profileSetup.smokingOption" values={smokingFilter} onChange={setSmokingFilter} />
                <MultiChipSelect label={t("profileSetup.cannabis")} options={CANNABIS_KEYS} translatePrefix="profileSetup.cannabisOption" values={cannabisFilter} onChange={setCannabisFilter} />
                <MultiChipSelect label={t("profileSetup.relationshipGoal")} options={RELATIONSHIP_GOAL_KEYS} translatePrefix="profileSetup.relationshipGoalOption" values={relationshipGoalFilter} onChange={setRelationshipGoalFilter} />
                <MultiChipSelect label={t("profileSetup.wantsKids")} options={WANTS_KIDS_KEYS} translatePrefix="profileSetup.wantsKidsOption" values={wantsKidsFilter} onChange={setWantsKidsFilter} />
                <MultiChipSelect label={t("profileSetup.hasKids")} options={HAS_KIDS_KEYS} translatePrefix="profileSetup.hasKidsOption" values={hasKidsFilter} onChange={setHasKidsFilter} />
              </View>
            </>
          ) : (
            <View style={styles.lockedCard}>
              <Ionicons name="lock-closed" size={28} color={colors.accentDark} />
              <Text style={styles.lockedTitle}>{t("filters.premiumLockedTitle")}</Text>
              <Text style={styles.lockedBody}>{t("filters.premiumLockedBody")}</Text>
              <Pressable style={styles.upgradeButton} onPress={openShop}>
                <Text style={styles.upgradeButtonText}>{t("filters.upgrade")}</Text>
              </Pressable>
            </View>
          )}
        </ScrollView>

        <View style={styles.footer}>
          <Pressable style={styles.saveButton} onPress={handleSave} disabled={saving}>
            {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>{t("filters.apply")}</Text>}
          </Pressable>
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
    paddingTop: 56,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  title: { fontSize: 20, fontWeight: "800", color: colors.navy },
  content: { padding: 20, gap: 16 },
  card: {
    backgroundColor: colors.white,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    padding: 16,
  },
  lockedCard: {
    backgroundColor: colors.creamDeep,
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    gap: 8,
  },
  lockedTitle: { fontSize: 16, fontWeight: "800", color: colors.navy, marginTop: 4 },
  lockedBody: { fontSize: 13, color: colors.muted, textAlign: "center", marginBottom: 8 },
  upgradeButton: { backgroundColor: colors.accent, borderRadius: 999, paddingVertical: 12, paddingHorizontal: 28 },
  upgradeButtonText: { color: "#fff", fontWeight: "700" },
  footer: { padding: 20, borderTopWidth: 1, borderTopColor: colors.border },
  saveButton: { backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  saveButtonText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
