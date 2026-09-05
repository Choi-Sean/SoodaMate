import asyncio
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.core.email_sender_base import EmailSender


class SmtpEmailSender(EmailSender):
    """Plain stdlib smtplib wrapped in a thread executor — low-volume
    transactional mail (verification codes) doesn't justify pulling in a new
    async-SMTP dependency."""

    async def send(self, to: str, subject: str, body: str) -> None:
        if not settings.smtp_host:
            raise RuntimeError("SMTP is not configured")

        message = EmailMessage()
        message["From"] = settings.smtp_from_address
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)


email_sender = SmtpEmailSender()
