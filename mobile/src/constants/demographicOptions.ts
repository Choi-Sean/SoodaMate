// Stored/filtered on by the raw key (language-independent) — the label
// shown to the user comes from i18n via `profileSetup.race.<key>` /
// `profileSetup.religion.<key>` (see locales/*.json).
export const RACE_ETHNICITY_KEYS = [
  "east_asian",
  "southeast_asian",
  "south_asian",
  "middle_eastern",
  "black",
  "white",
  "hispanic_latino",
  "mixed",
  "other",
  "prefer_not_to_say",
] as const;

export const RELIGION_KEYS = [
  "none",
  "christian",
  "catholic",
  "buddhist",
  "muslim",
  "other",
  "prefer_not_to_say",
] as const;

export const POLITICAL_VIEW_KEYS = [
  "liberal",
  "moderate",
  "conservative",
  "not_political",
  "other",
  "prefer_not_to_say",
] as const;

export const SMOKING_KEYS = ["never", "sometimes", "regularly", "prefer_not_to_say"] as const;

export const CANNABIS_KEYS = ["never", "sometimes", "regularly", "prefer_not_to_say"] as const;

export const EXERCISE_FREQUENCY_KEYS = ["never", "sometimes", "often", "daily"] as const;

export const RELATIONSHIP_GOAL_KEYS = ["friends", "long_term", "marriage", "short_term", "not_sure"] as const;

export const WANTS_KIDS_KEYS = [
  "yes",
  "no",
  "maybe",
  "have_want_more",
  "have_dont_want_more",
  "prefer_not_to_say",
] as const;

export const HAS_KIDS_KEYS = ["yes", "no", "prefer_not_to_say"] as const;
