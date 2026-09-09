"""Deterministic, template-driven icebreaker suggestions — no LLM call, no
external API/cost. Compares the viewer's and their match's structured
profile fields (K-content tags first, then general interests, then
language-exchange/shared-language) and returns a small typed result; the
*text* of the suggestion is entirely a mobile i18n concern (chat.icebreaker.*
keys interpolating interests.<key>/kcontent.<key> labels the client already
has translated) so this service never needs its own translation dict."""

import random

from app.models.profile import Profile


def _shared_tags(a: str | None, b: str | None) -> list[str]:
    if not a or not b:
        return []
    return sorted(set(a.split(",")) & set(b.split(",")))


def get_icebreaker(viewer_profile: Profile, peer_profile: Profile) -> dict:
    shared_kcontent = _shared_tags(viewer_profile.k_content_tags, peer_profile.k_content_tags)
    if shared_kcontent:
        return {"type": "shared_kcontent", "key": random.choice(shared_kcontent)}

    shared_interests = _shared_tags(viewer_profile.interests, peer_profile.interests)
    if shared_interests:
        return {"type": "shared_interest", "key": random.choice(shared_interests)}

    if viewer_profile.open_to_language_exchange and peer_profile.open_to_language_exchange:
        return {"type": "shared_language_exchange", "key": None}

    shared_languages = _shared_tags(viewer_profile.languages, peer_profile.languages)
    if shared_languages:
        return {"type": "shared_language", "key": random.choice(shared_languages)}

    return {"type": "generic", "key": None}
