from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExternalIdentity:
    """Normalized identity returned by any OAuth provider verifier."""

    provider_user_id: str
    email: str | None
    raw_claims: dict


class OAuthProviderVerifier(ABC):
    """Common interface every external auth provider (Google, Kakao, future
    phone-OTP, etc.) implements. auth_service only ever talks to this
    interface, so adding a new provider never requires touching issuance
    logic — just a new verifier + one router endpoint."""

    @abstractmethod
    async def verify(self, token: str) -> ExternalIdentity: ...
