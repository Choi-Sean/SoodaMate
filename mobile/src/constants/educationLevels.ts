// Replaces the old free-text "Education" input with a fixed degree-level
// picker (Bachelor's/Master's/PhD/etc.) — same "no mystery textboxes"
// reasoning as interests/languages.
export const EDUCATION_KEYS = [
  "high_school",
  "some_college",
  "associate",
  "bachelor",
  "master",
  "phd",
  "trade_school",
  "prefer_not_to_say",
] as const;
