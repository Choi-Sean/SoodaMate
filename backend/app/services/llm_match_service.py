import json
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.message import Message
from app.models.profile import Profile
from app.utils.mbti import compatible_types

CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
# Haiku, not Sonnet/Opus — this runs synchronously inside an AI Match request
# (the user is waiting on it) and only has to do a bounded ranking pick
# among a handful of candidates, not open-ended reasoning; cheap/fast is the
# right tradeoff for a per-request, potentially high-volume call.
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
# Bounds cost/latency/prompt size regardless of how many people are waiting
# — the deterministic score (services.blind_chat_service._compatibility_score)
# already picked a reasonable shortlist before this ever runs.
MAX_CANDIDATES = 8
MAX_TONE_MESSAGES = 15
MAX_MESSAGE_CHARS = 200


async def _recent_sent_message_tone(db: AsyncSession, user_id: uuid.UUID) -> list[str]:
    """A short sample of how this person actually writes, from their own
    past chats (any match, not just blind ones) — used only to help the LLM
    judge personality fit, never stored/logged beyond this one request, and
    never shown to anyone. Truncated hard per-message and in count so one
    chatty user can't blow up the prompt."""
    rows = (
        await db.execute(
            select(Message.content)
            .where(
                Message.sender_id == user_id,
                Message.message_type == "text",
                Message.content != "",
            )
            .order_by(Message.sent_at.desc())
            .limit(MAX_TONE_MESSAGES)
        )
    ).scalars().all()
    return [c[:MAX_MESSAGE_CHARS] for c in rows]


def _profile_summary(profile: Profile) -> str:
    parts = [
        f"bio: {profile.bio}" if profile.bio else None,
        f"mbti: {profile.mbti}" if profile.mbti else None,
        f"interests: {profile.interests}" if profile.interests else None,
        f"k-content: {profile.k_content_tags}" if profile.k_content_tags else None,
        f"languages: {profile.languages}" if profile.languages else None,
        f"occupation: {profile.occupation}" if profile.occupation else None,
    ]
    return "; ".join(p for p in parts if p) or "(no profile details)"


async def pick_best_candidate(
    db: AsyncSession,
    viewer_profile: Profile,
    candidates: list[tuple[Profile, float | None, list[str]]],
) -> int | None:
    """candidates: (profile, avg_rating_received, top_feedback_tags) for up
    to MAX_CANDIDATES already-eligible people, pre-sorted by the
    deterministic score (best first) by the caller. Returns the chosen
    candidate's index into that same list, or None if the API isn't
    configured, the call fails, or the response can't be parsed as a valid
    index — callers must fall back to the deterministic top pick in every
    None case, never treat it as "nobody's compatible"."""
    if not settings.anthropic_api_key or not candidates:
        return None

    shortlist = candidates[:MAX_CANDIDATES]
    tone = await _recent_sent_message_tone(db, viewer_profile.user_id)

    candidate_lines = []
    for i, (profile, avg_rating, top_tags) in enumerate(shortlist):
        feedback_bit = (
            f"; past-partner rating: {avg_rating}/5, noted for: {', '.join(top_tags)}"
            if avg_rating
            else ""
        )
        candidate_lines.append(f"[{i}] {_profile_summary(profile)}{feedback_bit}")

    mbti_types = compatible_types(viewer_profile.mbti)
    mbti_hint = (
        f"Viewer's most MBTI-compatible type: {mbti_types[0]} "
        "(a positive signal to weigh, not a hard rule)\n"
        if mbti_types
        else ""
    )
    user_prompt = (
        f"Viewer profile: {_profile_summary(viewer_profile)}\n"
        + mbti_hint
        + "Viewer's recent chat messages (writing style/tone sample):\n"
        + "\n".join(f"- {m}" for m in tone[:MAX_TONE_MESSAGES])
        + "\n\nCandidates:\n"
        + "\n".join(candidate_lines)
    )

    system_prompt = (
        "You are picking the single best-compatibility match for a dating app's anonymous "
        "'blind chat' feature, from a shortlist that already passed hard filters (age/gender/"
        "distance/block). Judge personality and conversational fit from the profile details "
        "(including MBTI compatibility when known) and the viewer's own message tone versus each "
        "candidate's profile and any past-partner feedback. Respond with ONLY a JSON object of "
        "the form {\"index\": N} where N is the candidate's [N] number. No other text."
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                CLAUDE_API_URL,
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 100,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
    except httpx.HTTPError:
        return None

    if resp.status_code >= 400:
        return None

    try:
        text = resp.json()["content"][0]["text"]
        index = int(json.loads(text)["index"])
    except (KeyError, IndexError, ValueError, json.JSONDecodeError):
        return None

    if not 0 <= index < len(shortlist):
        return None
    return index
