import httpx
from jose import jwt
from jose.exceptions import JOSEError  # base class covering JWTError, JWSError, etc.

from app.config import settings
from app.core.auth_provider_base import ExternalIdentity, OAuthProviderVerifier

APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


class AppleVerifier(OAuthProviderVerifier):
    """Verifies the identityToken from expo-apple-authentication's
    signInAsync() — a JWT signed by Apple, not an opaque access token like
    Kakao's, so verification is local (fetch Apple's public JWKS, check
    signature/issuer/audience/expiry) rather than a userinfo API call."""

    async def verify(self, token: str) -> ExternalIdentity:
        try:
            unverified_header = jwt.get_unverified_header(token)
        except JOSEError as exc:
            raise ValueError(f"invalid Apple identityToken: {exc}") from exc

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(APPLE_KEYS_URL)
            except httpx.HTTPError as exc:
                raise ValueError(f"could not reach Apple: {exc}") from exc

        jwks = (resp.json() or {}).get("keys", [])
        key = next((k for k in jwks if k.get("kid") == unverified_header.get("kid")), None)
        if key is None:
            raise ValueError("no matching Apple signing key")

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=settings.apple_bundle_id,
                issuer=APPLE_ISSUER,
            )
        except JOSEError as exc:
            raise ValueError(f"invalid Apple identityToken: {exc}") from exc

        return ExternalIdentity(
            # Apple only includes `email` in the identityToken on the user's
            # very first Sign in with Apple for this app; later sign-ins omit
            # it, which is fine — login_or_signup_with_provider already
            # treats a missing identity.email as normal (pure-OAuth users
            # aren't required to have one).
            provider_user_id=claims["sub"],
            email=claims.get("email"),
            raw_claims=claims,
        )


apple_verifier = AppleVerifier()
