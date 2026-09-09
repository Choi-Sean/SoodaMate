"""Real-time chat translation via Google Cloud Translation v2
(https://cloud.google.com/translate/docs/reference/rest/v2/translate) — a
plain API-key-authenticated REST endpoint, no service account/OAuth needed.

Best-effort and silent: an unconfigured key, a network hiccup, or any API
error all just return None rather than raising — sending a chat message
must never fail because translation isn't set up or is briefly down, same
convention as push_service's unconfigured-Firebase no-op. Callers (routers/
ws_chat.py) treat None as "no translation available," not an error, and
still deliver the original message either way."""

import httpx

from app.config import settings

_ENDPOINT = "https://translation.googleapis.com/language/translate/v2"


async def translate(text: str, target_lang: str, source_lang: str | None = None) -> str | None:
    if not settings.google_translate_api_key or not text:
        return None
    if source_lang and source_lang == target_lang:
        return None

    params = {"key": settings.google_translate_api_key, "q": text, "target": target_lang, "format": "text"}
    if source_lang:
        params["source"] = source_lang

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(_ENDPOINT, params=params)
            resp.raise_for_status()
            data = resp.json()
        return data["data"]["translations"][0]["translatedText"]
    except Exception:
        return None
