from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    account,
    auth,
    calls,
    devices,
    discovery,
    interactions,
    matches,
    messages,
    payments,
    profiles,
    safety,
    uploads,
    verification,
    ws_chat,
)

app = FastAPI(title="SuDa Date API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(uploads.router)
app.include_router(discovery.router)
app.include_router(interactions.router)
app.include_router(matches.router)
app.include_router(messages.router)
app.include_router(devices.router)
app.include_router(safety.router)
app.include_router(ws_chat.router)
app.include_router(account.router)
app.include_router(payments.router)
app.include_router(verification.router)
app.include_router(calls.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
