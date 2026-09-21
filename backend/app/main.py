import json
import logging
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    account,
    ads,
    admin,
    auth,
    blind_chat,
    calls,
    couple_stories,
    devices,
    discovery,
    inquiries,
    interactions,
    matches,
    messages,
    moments,
    payments,
    profiles,
    safety,
    uploads,
    verification,
    ws_chat,
)

logger = logging.getLogger(__name__)

# The chat WebSocket authenticates with ?token=<access token> (browsers/RN can't
# set headers on a socket upgrade), and uvicorn logs every request line — so a
# live bearer token would sit in the platform logs for anyone with log access.
# Redact it on the way into the log records.
_TOKEN_QUERY = re.compile(r"([?&]token=)[^&\s\"']+", re.IGNORECASE)


class _RedactTokens(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _TOKEN_QUERY.sub(r"\1[redacted]", record.msg)
        if record.args:
            record.args = tuple(_TOKEN_QUERY.sub(r"\1[redacted]", a) if isinstance(a, str) else a for a in record.args)
        return True


for _logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    logging.getLogger(_logger_name).addFilter(_RedactTokens())

_DEV_SECRET = "dev-secret-key-not-for-production"
_DEV_DB_MARKER = "ChangeMe123!"


def validate_production_settings(cfg) -> None:
    """Refuse to boot in production with settings that would make the API
    forgeable. A forgeable JWT secret means anyone can mint a token for any
    user id (including the admin's), so failing loudly at startup beats
    quietly running open."""
    problems = []
    if cfg.secret_key == _DEV_SECRET or len(cfg.secret_key) < 16:
        problems.append("SECRET_KEY is unset, the built-in development default, or shorter than 16 characters")
    if _DEV_DB_MARKER in cfg.database_url:
        problems.append("DATABASE_URL is still the built-in development default")
    if "*" in cfg.cors_origin_list:
        problems.append("CORS_ORIGINS must list explicit origins, not '*'")
    if problems:
        raise RuntimeError("Refusing to start with unsafe production settings: " + "; ".join(problems))


class _BodyTooLarge(Exception):
    pass


class SecurityMiddleware:
    """Pure-ASGI (so it never interferes with WebSockets): refuses oversized
    request bodies before they are parsed, and adds baseline security headers
    to every HTTP response."""

    def __init__(self, app, max_body_bytes: int, production: bool) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.production = production

    async def _reject(self, send, status_code: int, detail: str) -> None:
        body = json.dumps({"detail": detail}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": self._headers([(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]),
            }
        )
        await send({"type": "http.response.body", "body": body})

    def _headers(self, existing: list) -> list:
        names = {k.lower() for k, _ in existing}
        extra = [
            (b"x-content-type-options", b"nosniff"),
            (b"referrer-policy", b"no-referrer"),
            (b"x-frame-options", b"DENY"),
            (b"cache-control", b"no-store"),
        ]
        if self.production:
            extra.append((b"strict-transport-security", b"max-age=31536000; includeSubDomains"))
            extra.append((b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"))
        return existing + [(k, v) for k, v in extra if k not in names]

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = dict(scope.get("headers") or []).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > self.max_body_bytes:
            await self._reject(send, 413, "request body too large")
            return

        received = 0
        started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body_bytes:
                    raise _BodyTooLarge()
            return message

        async def send_with_headers(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                message = {**message, "headers": self._headers(list(message.get("headers", [])))}
            await send(message)

        try:
            await self.app(scope, limited_receive, send_with_headers)
        except _BodyTooLarge:
            if not started:
                await self._reject(send, 413, "request body too large")


def create_app(production: bool | None = None) -> FastAPI:
    prod = settings.is_production if production is None else production
    # The interactive docs / OpenAPI schema are a free map of every endpoint
    # for an attacker — only served outside production.
    fastapi_app = FastAPI(
        title="SooDaMate API",
        version="0.1.0",
        docs_url=None if prod else "/docs",
        redoc_url=None if prod else "/redoc",
        openapi_url=None if prod else "/openapi.json",
    )

    # Added first = inner: CORS (added next) wraps it, so even a 413 carries the
    # CORS headers a browser needs to read it.
    fastapi_app.add_middleware(SecurityMiddleware, max_body_bytes=settings.max_json_body_bytes, production=prod)
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for module in (
        auth,
        profiles,
        uploads,
        discovery,
        interactions,
        matches,
        messages,
        devices,
        safety,
        ws_chat,
        account,
        payments,
        verification,
        calls,
        admin,
        couple_stories,
        moments,
        blind_chat,
        inquiries,
        ads,
    ):
        fastapi_app.include_router(module.router)

    @fastapi_app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return fastapi_app


if settings.is_production:
    validate_production_settings(settings)

app = create_app()
