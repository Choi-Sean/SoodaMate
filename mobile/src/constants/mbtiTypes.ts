// Display label comes from i18n via `mbti.type.<key>`, same convention as
// every other enum-like constant in this app (interests, K-content tags, ...).
export const MBTI_TYPE_KEYS = [
  "ISTJ", "ISFJ", "INFJ", "INTJ",
  "ISTP", "ISFP", "INFP", "INTP",
  "ESTP", "ESFP", "ENFP", "ENTP",
  "ESTJ", "ESFJ", "ENFJ", "ENTJ",
] as const;

export type MbtiType = (typeof MBTI_TYPE_KEYS)[number];

// Mirrors backend/app/utils/mbti.py's MBTI_COMPATIBILITY exactly (kept in
// sync by hand — small, stable, 16-entry table) — used only to show "your
// ideal match" copy on the quiz result screen; the actual blind-chat
// filtering happens server-side against the backend's own copy.
export const MBTI_COMPATIBLE_TYPE: Record<MbtiType, MbtiType> = {
  ISTJ: "ESTP", ESTP: "ISTJ",
  ISFJ: "ESFP", ESFP: "ISFJ",
  INFJ: "ENFP", ENFP: "INFJ",
  INTJ: "ENTP", ENTP: "INTJ",
  ISTP: "ESTJ", ESTJ: "ISTP",
  ISFP: "ESFJ", ESFJ: "ISFP",
  INFP: "ENFJ", ENFJ: "INFP",
  INTP: "ENTJ", ENTJ: "INTP",
};
