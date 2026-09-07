"""Push notification text per language — a small, hand-maintained mirror of
(a subset of) the mobile app's i18n locale files. FCM notification text has
to be a plain string baked in at send time on the server; the client's own
i18next instance never gets a chance to translate it the way in-app text
does, so this is the one place server-side "content" needs its own
translations. Only en/ko are hand-translated (mirroring what's actually
been requested); an unsupported preferred_language (es/zh/ja, or anything
unrecognized) falls back to English — same convention as the mobile app's
own i18next fallbackLng="en"."""

SUPPORTED_PUSH_LANGUAGES = ("en", "ko")

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "match_title": "It's a match! 🎉",
        "match_body": "You have a new match on SooDa Mate",
        "like_title": "New like! 💛",
        "like_body": "Someone liked you on SooDa Mate",
        "superlike_title": "Super Like! ⭐",
        "superlike_body": "Someone super liked you on SooDa Mate",
        "message_body": "sent you a message",
        "verification_approved_title": "You're verified! ✅",
        "verification_approved_body": "Your verification badge is now live on your profile.",
        "verification_rejected_title": "Verification needs another try",
        "verification_rejected_body": "Your submission wasn't approved — open the app to see why.",
    },
    "ko": {
        "match_title": "매칭 성사! 🎉",
        "match_body": "수다메이트에서 새로운 매칭이 생겼어요",
        "like_title": "새로운 좋아요! 💛",
        "like_body": "누군가 회원님을 좋아요 눌렀어요",
        "superlike_title": "슈퍼좋아요! ⭐",
        "superlike_body": "누군가 회원님을 슈퍼좋아요 눌렀어요",
        "message_body": "메시지를 보냈어요",
        "verification_approved_title": "인증 완료! ✅",
        "verification_approved_body": "프로필에 인증 뱃지가 표시됐어요.",
        "verification_rejected_title": "인증을 다시 시도해주세요",
        "verification_rejected_body": "제출한 인증이 승인되지 않았어요 — 앱에서 사유를 확인해보세요.",
    },
}


def t(lang: str | None, key: str) -> str:
    resolved = lang if lang in _STRINGS else "en"
    return _STRINGS[resolved].get(key, _STRINGS["en"][key])
