"""Email sending service with template support."""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from edcraft_backend.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails with template support."""

    def __init__(self) -> None:
        # Set up Jinja2 template environment
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def send_verification_email(
        self, to_email: str, name: str, verification_token: str
    ) -> None:
        """Send email verification email."""
        verification_url = (
            f"{settings.frontend_url}/auth/verify-email?token={verification_token}"
        )

        subject = "Verify your EdCraft email address"

        # Render HTML template
        html_template = self.jinja_env.get_template("verify_email.html")
        html_body = html_template.render(
            name=name,
            verification_url=verification_url,
            expiry_hours=settings.email.verification_token_expire_hours,
        )

        # Render plain text template
        text_template = self.jinja_env.get_template("verify_email.txt")
        text_body = text_template.render(
            name=name,
            verification_url=verification_url,
            expiry_hours=settings.email.verification_token_expire_hours,
        )

        await self._send_email(to_email, subject, html_body, text_body)

    async def _send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> None:
        """Send email via SMTP or log to console in dev mode."""
        if not settings.email.enabled:
            # Development mode: just log the email
            logger.info(
                f"\n{'='*60}\n"
                f"EMAIL (Development Mode - Not Sent)\n"
                f"{'='*60}\n"
                f"To: {to_email}\n"
                f"Subject: {subject}\n"
                f"{'='*60}\n"
                f"{text_body}\n"
                f"{'='*60}\n"
            )
            return

        # Production mode: send via SMTP
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            import aiosmtplib

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = (
                f"{settings.email.from_name} <{settings.email.from_email}>"
            )
            message["To"] = to_email

            # Attach both plain text and HTML versions
            part1 = MIMEText(text_body, "plain")
            part2 = MIMEText(html_body, "html")
            message.attach(part1)
            message.attach(part2)

            await aiosmtplib.send(
                message,
                hostname=settings.email.smtp_host,
                port=settings.email.smtp_port,
                username=settings.email.smtp_user,
                password=settings.email.smtp_password,
                start_tls=True,
            )
            logger.info(f"Email sent successfully to {to_email}")

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            from edcraft_backend.exceptions import EmailSendError

            raise EmailSendError(f"Failed to send email: {str(e)}") from e
