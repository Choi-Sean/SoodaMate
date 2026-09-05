import httpx

from app.core.auth_provider_base import ExternalIdentity, OAuthProviderVerifier

KAKAO_USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"


class KakaoVerifier(OAuthProviderVerifier):
    async def verify(self, token: str) -> ExternalIdentity:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    KAKAO_USER_INFO_URL, headers={"Authorization": f"Bearer {token}"}
                )
            except httpx.HTTPError as exc:
                raise ValueError(f"could not reach Kakao: {exc}") from exc

        if resp.status_code != 200:
            raise ValueError(f"invalid Kakao access_token (status {resp.status_code})")

        payload = resp.json()
        kakao_account = payload.get("kakao_account") or {}

        return ExternalIdentity(
            provider_user_id=str(payload["id"]),
            email=kakao_account.get("email"),
            raw_claims=payload,
        )


kakao_verifier = KakaoVerifier()
