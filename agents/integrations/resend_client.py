"""Minimal Resend integration for the Pitcher NemoClaw tool."""

from __future__ import annotations

import os
import time
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


RESEND_EMAILS_URL = "https://api.resend.com/emails"
DEFAULT_FROM_ADDRESS = "Mainstreet <hello@mainstreet.local>"


class ResendError(RuntimeError):
    """Raised when Resend returns an error response."""


class ResendConfigError(ResendError):
    """Raised when required Resend configuration is missing."""


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _api_key() -> str:
    """Return the configured Resend API key."""

    _load_env()
    value = os.environ.get("RESEND_API_KEY", "").strip()
    if not value:
        raise ResendConfigError("RESEND_API_KEY is required to send outreach email.")
    return value


def _from_address(explicit: str | None = None) -> str:
    """Return the sender address for outbound outreach."""

    _load_env()
    return (explicit or os.environ.get("OUTREACH_FROM_ADDRESS") or DEFAULT_FROM_ADDRESS).strip()


def send_email(
    to: str,
    subject: str,
    html: str,
    from_addr: str | None = None,
    reply_to: str | None = None,
    text: str | None = None,
) -> dict[str, Any]:
    """Send one email through Resend and return `{"id": message_id}`.

    Retries once for transient network and 5xx failures.
    """

    if not to or "@" not in to:
        raise ResendError("A valid recipient email address is required.")
    if not subject.strip():
        raise ResendError("Email subject is required.")
    if not html.strip():
        raise ResendError("Email HTML is required.")

    api_key = _api_key()

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise ResendConfigError("The `httpx` package is not installed. Run `pip install -r agents/requirements.txt`.") from exc

    payload: dict[str, Any] = {
        "from": _from_address(from_addr),
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    if text:
        payload["text"] = text

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = httpx.post(
                RESEND_EMAILS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=30.0,
            )
            if 500 <= response.status_code < 600 and attempt == 0:
                time.sleep(1)
                continue
            if not 200 <= response.status_code < 300:
                raise ResendError(f"Resend send failed with HTTP {response.status_code}: {response.text[:300]}")
            data = response.json()
            message_id = data.get("id")
            if not message_id:
                raise ResendError("Resend response did not include an email id.")
            return {"id": str(message_id), "provider": "resend"}
        except httpx.HTTPError as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
                continue
            break

    raise ResendError(f"Resend send failed after retry: {last_error}") from last_error
