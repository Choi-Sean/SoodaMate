from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Mirrors OAuthProviderVerifier's shape (app/core/auth_provider_base.py)
    — a swappable interface so verification_service.py never needs to know
    whether it's SMTP, SendGrid, SES, etc."""

    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> None: ...
