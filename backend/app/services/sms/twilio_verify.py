import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.core.sms_verifier_base import SmsVerifier

TWILIO_VERIFY_API_BASE = "https://verify.twilio.com/v2"


class TwilioVerifySmsVerifier(SmsVerifier):
    """Raw REST calls (like apple.py/google.py's own httpx use) rather than
    the `twilio` SDK — Verify's API surface here is two POSTs, not worth a
    new dependency for."""

    def _service_url(self, path: str) -> str:
        return f"{TWILIO_VERIFY_API_BASE}/Services/{settings.twilio_verify_service_sid}/{path}"

    def _auth(self) -> tuple[str, str]:
        return (settings.twilio_account_sid, settings.twilio_auth_token)

    async def start(self, phone_number: str) -> None:
        if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_verify_service_sid):
            # Same "not configured yet" 503 pattern as SmtpEmailSender.send —
            # an OTP that silently never arrives is worse than an honest error.
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "phone verification is not configured")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    self._service_url("Verifications"),
                    auth=self._auth(),
                    data={"To": phone_number, "Channel": "sms"},
                )
            except httpx.HTTPError as exc:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"could not reach Twilio: {exc}") from exc

        if resp.status_code >= 400:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "failed to send verification code")

    async def check(self, phone_number: str, code: str) -> bool:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(
                    self._service_url("VerificationCheck"),
                    auth=self._auth(),
                    data={"To": phone_number, "Code": code},
                )
            except httpx.HTTPError as exc:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"could not reach Twilio: {exc}") from exc

        if resp.status_code >= 400:
            # Twilio 404s a check made against an expired/never-started
            # verification — treat the same as "wrong code", not a crash.
            return False
        return resp.json().get("status") == "approved"


sms_verifier = TwilioVerifySmsVerifier()
