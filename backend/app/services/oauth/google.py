from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings
from app.core.auth_provider_base import ExternalIdentity, OAuthProviderVerifier

_transport_request = google_requests.Request()


class GoogleVerifier(OAuthProviderVerifier):
    async def verify(self, token: str) -> ExternalIdentity:
        # google-auth's verify_oauth2_token is sync (does a blocking HTTP
        # call to fetch Google's public certs, cached after the first call);
        # fine to call directly here since it's not on a hot path.
        try:
            claims = google_id_token.verify_oauth2_token(
                token, _transport_request, audience=settings.google_oauth_client_id
            )
        except ValueError as exc:
            raise ValueError(f"invalid Google id_token: {exc}") from exc

        return ExternalIdentity(
            provider_user_id=claims["sub"],
            email=claims.get("email"),
            raw_claims=claims,
        )


google_verifier = GoogleVerifier()
