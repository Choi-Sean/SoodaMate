from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ExternalIdentity:
    """Normalized identity returned by any OAuth provider verifier."""

    provider_user_id: str
    email: str | None
    raw_claims: dict
    # True only when the provider itself vouches that the user controls `email`.
    # An unverified email must never be used to find (and merge into) an account.
    email_verified: bool = False


class OAuthProviderVerifier(ABC):
    """Common interface every external auth provider (Google, Apple, future
    phone-OTP, etc.) implements. auth_service only ever talks to this
    interface, so adding a new provider never requires touching issuance
    logic — just a new verifier + one router endpoint."""

    @abstractmethod
    async def verify(self, token: str) -> ExternalIdentity: ...
