// Deliberately broad (10 keys), not the ~26-tag granularity of
// INTEREST_KEYS — blind chat pairs two people waiting on the *same*
// category *right now*, so finer categories would fragment an already
// small queue and make matches rarer. Display label (emoji + translated
// name) comes from i18n via `blindChatCategories.<key>`, same convention
// as interests/K-content tags.
export const BLIND_CHAT_CATEGORY_KEYS = [
  "travel",
  "movies_tv",
  "music",
  "fitness",
  "food",
  "gaming",
  "kpop",
  "pets",
  "books",
  "free_talk",
] as const;
