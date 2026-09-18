// Mirrors backend/app/models/blind_chat_feedback.py::BLIND_CHAT_FEEDBACK_TAG_KEYS.
// Signal only — never shown to the rated person, folded into future AI
// Match ranking as an aggregate (see llm_match_service.py), never used for
// moderation (that's report/block's job, a separate flow). "other" is the
// one key that also reveals a free-text comment box in the feedback modal.
export const BLIND_CHAT_FEEDBACK_TAG_KEYS = [
  "kind",
  "great_conversation",
  "similar_interests",
  "awkward",
  "uncomfortable",
  "no_show",
  "other",
] as const;
