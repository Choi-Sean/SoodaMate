import type { ReactNode } from "react";
import { Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import type { Candidate } from "../types";
import { colors } from "../theme";

type IconName = keyof typeof Ionicons.glyphMap;

function InfoPill({ icon, label }: { icon: IconName; label: string }) {
  return (
    <View style={styles.pill}>
      <Ionicons name={icon} size={14} color={colors.accentDark} />
      <Text style={styles.pillText}>{label}</Text>
    </View>
  );
}

// No left icon - used for interests/languages, whose translated labels
// already carry their own emoji (interests) or don't need one (languages),
// matching how the same tags render as chips in Edit Profile.
function TextPill({ label }: { label: string }) {
  return (
    <View style={styles.pill}>
      <Text style={styles.pillText}>{label}</Text>
    </View>
  );
}

function InfoRow({ icon, text }: { icon: IconName; text: string }) {
  return (
    <View style={styles.factRow}>
      <Ionicons name={icon} size={17} color={colors.muted} style={styles.factIcon} />
      <Text style={styles.factText}>{text}</Text>
    </View>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{title}</Text>
      {children}
    </View>
  );
}

/** Bumble-style "About me"/"Looking for" pill cards + Hinge-style plain
 * fact rows, below the photo/video carousel — the scroll-down half of a
 * profile card. Renders nothing for a section whose fields are all empty,
 * so a bare-bones profile doesn't show a wall of empty cards. */
export default function ProfileInfoSections({ candidate }: { candidate: Candidate }) {
  const { t } = useTranslation();

  const facts: { icon: IconName; text: string }[] = [];
  if (candidate.height_cm) facts.push({ icon: "resize-outline", text: t("profileDetail.heightValue", { cm: candidate.height_cm }) });
  if (candidate.occupation) facts.push({ icon: "briefcase-outline", text: candidate.occupation });
  // education is a fixed-key dropdown now (Edit Profile) - older free-text
  // data from before that existed just falls back to showing itself as-is.
  if (candidate.education)
    facts.push({
      icon: "school-outline",
      text: t(`profileSetup.educationOption.${candidate.education}`, { defaultValue: candidate.education }),
    });
  // hometown is free text (a place name someone typed/picked) - unlike the
  // fixed-key fields above, there's no key to translate: it shows in
  // whichever language it was entered, same as a bio or occupation would.
  if (candidate.hometown) facts.push({ icon: "home-outline", text: candidate.hometown });

  const about: { icon: IconName; label: string }[] = [];
  if (candidate.race_ethnicity)
    about.push({ icon: "earth-outline", label: t(`profileSetup.race.${candidate.race_ethnicity}`, { defaultValue: candidate.race_ethnicity }) });
  if (candidate.religion)
    about.push({ icon: "book-outline", label: t(`profileSetup.religionOption.${candidate.religion}`, { defaultValue: candidate.religion }) });
  if (candidate.political_view)
    about.push({ icon: "flag-outline", label: t(`profileSetup.politicalViewOption.${candidate.political_view}`, { defaultValue: candidate.political_view }) });
  if (candidate.smoking)
    about.push({ icon: "flame-outline", label: t(`profileSetup.smokingOption.${candidate.smoking}`, { defaultValue: candidate.smoking }) });
  if (candidate.cannabis)
    about.push({ icon: "leaf-outline", label: t(`profileSetup.cannabisOption.${candidate.cannabis}`, { defaultValue: candidate.cannabis }) });
  if (candidate.exercise_frequency)
    about.push({ icon: "barbell-outline", label: t(`profileSetup.exerciseFrequencyOption.${candidate.exercise_frequency}`, { defaultValue: candidate.exercise_frequency }) });

  const lookingFor: { icon: IconName; label: string }[] = [];
  if (candidate.relationship_goal)
    lookingFor.push({ icon: "heart-outline", label: t(`profileSetup.relationshipGoalOption.${candidate.relationship_goal}`, { defaultValue: candidate.relationship_goal }) });
  if (candidate.wants_kids)
    lookingFor.push({ icon: "people-outline", label: t(`profileSetup.wantsKidsOption.${candidate.wants_kids}`, { defaultValue: candidate.wants_kids }) });
  if (candidate.has_kids)
    lookingFor.push({ icon: "people-outline", label: t(`profileSetup.hasKidsOption.${candidate.has_kids}`, { defaultValue: candidate.has_kids }) });

  return (
    <View style={styles.container}>
      {facts.length > 0 && (
        <View style={styles.factsCard}>
          {facts.map((f, i) => (
            <InfoRow key={i} icon={f.icon} text={f.text} />
          ))}
        </View>
      )}

      {candidate.bio && (
        <Section title={t("profileDetail.bio")}>
          <Text style={styles.bioText}>{candidate.bio}</Text>
        </Section>
      )}

      {about.length > 0 && (
        <Section title={t("profileDetail.about")}>
          <View style={styles.pillWrap}>
            {about.map((a, i) => (
              <InfoPill key={i} icon={a.icon} label={a.label} />
            ))}
          </View>
        </Section>
      )}

      {lookingFor.length > 0 && (
        <Section title={t("profileDetail.lookingFor")}>
          <View style={styles.pillWrap}>
            {lookingFor.map((l, i) => (
              <InfoPill key={i} icon={l.icon} label={l.label} />
            ))}
          </View>
        </Section>
      )}

      {candidate.interests.length > 0 && (
        <Section title={t("profileDetail.interests")}>
          <View style={styles.pillWrap}>
            {candidate.interests.map((interest, i) => (
              // Known keys (picked via Edit Profile's curated list) resolve
              // to "🥾 Hiking" etc. via interests.<key> - anything else
              // (older free-text data from before that picker existed)
              // just falls back to showing the raw stored text.
              <TextPill key={i} label={t(`interests.${interest}`, { defaultValue: interest })} />
            ))}
          </View>
        </Section>
      )}

      {candidate.languages.length > 0 && (
        <Section title={t("profileDetail.languages")}>
          <View style={styles.pillWrap}>
            {candidate.languages.map((lang, i) => (
              <TextPill key={i} label={t(`languages.${lang}`, { defaultValue: lang })} />
            ))}
          </View>
        </Section>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: 16, gap: 14 },
  factsCard: {
    backgroundColor: colors.white,
    borderRadius: 18,
    paddingVertical: 4,
    borderWidth: 1,
    borderColor: colors.border,
  },
  factRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  factIcon: { width: 24 },
  factText: { color: colors.ink, fontSize: 15, flexShrink: 1 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 18,
    borderWidth: 1,
    borderColor: colors.border,
  },
  cardTitle: { fontSize: 15, fontWeight: "800", color: colors.navy, marginBottom: 12 },
  bioText: { color: colors.ink, fontSize: 15, lineHeight: 22 },
  pillWrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: colors.creamDeep,
    borderRadius: 20,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  pillText: { color: colors.ink, fontSize: 13, fontWeight: "600" },
});
