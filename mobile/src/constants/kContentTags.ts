// Curated K-content taste tags (K-drama / K-pop / webtoon / K-movie &
// variety) — same pattern as interestsAndLanguages.ts's INTEREST_KEYS: a
// flat, non-editable key list with the display label (emoji + translated
// title) coming from i18n via `kcontent.<key>`. A separate curated list
// from INTEREST_KEYS on purpose, so the two pickers (and the icebreaker
// suggestions built on top of them — see chat.icebreaker.* i18n keys) can
// evolve independently.
export const K_CONTENT_KEYS = [
  // K-drama
  "crash_landing_on_you",
  "squid_game",
  "reply_1988",
  "goblin",
  "itaewon_class",
  "hospital_playlist",
  "business_proposal",
  "the_glory",
  // K-pop
  "bts",
  "blackpink",
  "newjeans",
  "seventeen",
  "stray_kids",
  "twice",
  "ive",
  "aespa",
  // Webtoon
  "solo_leveling",
  "true_beauty",
  "tower_of_god",
  "lookism",
  // K-movie & variety
  "parasite",
  "physical_100",
  "running_man",
  "extreme_job",
] as const;
