"""SMTP email integration for Pitcher.

This is intentionally small and stdlib-only so a personal Gmail, Outlook, or
custom mailbox can be used for demo sending without adding dependencies.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any
from uuid import uuid4

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_PORT = 587


class SMTPEmailError(RuntimeError):
    """Raised when SMTP sending fails."""


class SMTPEmailConfigError(SMTPEmailError):
    """Raised when required SMTP configuration is missing."""


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _env(name: str, default: str = "") -> str:
    """Return a stripped environment value."""

    _load_env()
    return os.environ.get(name, default).strip()


def _bool_env(name: str, default: bool) -> bool:
    """Read a boolean env flag."""

    value = _env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _port() -> int:
    """Return the configured SMTP port."""

    value = _env("SMTP_PORT", str(DEFAULT_PORT))
    try:
        return int(value)
    except ValueError as exc:
        raise SMTPEmailConfigError("SMTP_PORT must be an integer.") from exc


def _from_address(explicit: str | None = None) -> str:
    """Return the outbound sender address."""

    value = (
        explicit
        or _env("SMTP_FROM_ADDRESS")
        or _env("OUTREACH_FROM_ADDRESS")
        or _env("SMTP_USERNAME")
    )
    if not value:
        raise SMTPEmailConfigError("SMTP_FROM_ADDRESS or OUTREACH_FROM_ADDRESS is required for SMTP sending.")
    return value


def _message(
    to: str,
    subject: str,
    html: str,
    text: str | None,
    from_addr: str | None,
    reply_to: str | None,
) -> EmailMessage:
    """Build a multipart email message."""

    sender = _from_address(from_addr)
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to

    plain = text or "This email requires an HTML-capable email client."
    msg.set_content(plain)
    msg.add_alternative(html, subtype="html")
    return msg


def send_email(
    to: str,
    subject: str,
    html: str,
    from_addr: str | None = None,
    reply_to: str | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    """Send one email through an SMTP account."""

    if not to or "@" not in to:
        raise SMTPEmailError("A valid recipient email address is required.")
    if not subject.strip():
        raise SMTPEmailError("Email subject is required.")
    if not html.strip():
        raise SMTPEmailError("Email HTML is required.")

    host = _env("SMTP_HOST")
    username = _env("SMTP_USERNAME")
    password = _env("SMTP_PASSWORD")
    if not host:
        raise SMTPEmailConfigError("SMTP_HOST is required for SMTP sending.")
    if not username:
        raise SMTPEmailConfigError("SMTP_USERNAME is required for SMTP sending.")
    if not password:
        raise SMTPEmailConfigError("SMTP_PASSWORD is required for SMTP sending.")

    port = _port()
    use_ssl = _bool_env("SMTP_USE_SSL", False)
    use_tls = _bool_env("SMTP_USE_TLS", not use_ssl)
    msg = _message(to, subject, html, text, from_addr, reply_to)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=30.0) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30.0) as server:
                if use_tls:
                    server.starttls()
                server.login(username, password)
                server.send_message(msg)
    except smtplib.SMTPException as exc:
        raise SMTPEmailError(f"SMTP send failed: {exc}") from exc
    except OSError as exc:
        raise SMTPEmailError(f"SMTP connection failed: {exc}") from exc

    return {
        "id": f"smtp-{uuid4()}",
        "provider": "smtp",
        "from": msg["From"],
    }
