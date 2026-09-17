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
] as const;
