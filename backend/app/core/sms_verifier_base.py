from abc import ABC, abstractmethod


class SmsVerifier(ABC):
    """Mirrors EmailSender's shape (app/core/email_sender_base.py) — a
    swappable interface so sms_verification_service.py never needs to know
    it's talking to Twilio Verify specifically. Unlike email verification,
    code generation/storage/expiry is delegated entirely to the provider
    (Twilio Verify is itself stateful), so there's no local code/hash to
    manage — just start a check and later confirm one."""

    @abstractmethod
    async def start(self, phone_number: str) -> None: ...

    @abstractmethod
    async def check(self, phone_number: str, code: str) -> bool: ...
