// Deliberately broad (8 keys), not the ~26-tag granularity of
// INTEREST_KEYS — blind chat pairs two people waiting on the *same*
// category *right now*, so finer categories would fragment an already
// small queue and make matches rarer. Trimmed from an earlier 11-key list
// (dropped: pets, books, language_exchange — the least-used, most-niche
// ones, per product decision) since even 11 was already fragmenting the
// queue more than it needed to. Display label (emoji + translated name)
// comes from i18n via `blindChatCategories.<key>`, same convention as
// interests/K-content tags. Also now the required signup-time selection
// (ProfileSetupScreen's "preferredCategories" field) — see Profile.
// preferred_categories on the backend.
export const BLIND_CHAT_CATEGORY_KEYS = [
  "travel",
  "movies_tv",
  "music",
  "fitness",
  "food",
  "gaming",
  "kpop",
  "free_talk",
  // No "mbti_match" any more: regular matching ignores MBTI entirely (it
  // used to be a hard filter opted into via this picker — two same-type
  // users could never pair). Only AI Match weighs MBTI, automatically, from
  // the profile — nothing to pick here. Profiles/queue entries saved before
  // this may still hold the old key; callers drop unknown keys (see
  // knownBlindChatCategories).
] as const;

/** Drops any saved category key that's no longer in the picker (e.g. the
 * retired "mbti_match") so it can't linger as an unrenderable chip or get
 * re-sent to the backend. */
export function knownBlindChatCategories(keys: readonly string[] | null | undefined): string[] {
  const known = new Set<string>(BLIND_CHAT_CATEGORY_KEYS);
  return (keys ?? []).filter((k) => known.has(k));
}
