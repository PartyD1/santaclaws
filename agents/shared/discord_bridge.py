"""Outbound Discord webhook bridge for Mainstreet NemoClaw claws."""

from __future__ import annotations

import os
from typing import Any, Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


DISCORD_CONTENT_LIMIT = 2000
SAFE_CONTENT_LIMIT = 1900
REQUEST_TIMEOUT_SECONDS = 10.0


class DiscordBridgeError(RuntimeError):
    """Base exception for outbound Discord bridge failures."""


class DiscordConfigError(DiscordBridgeError):
    """Raised when Discord webhook configuration is missing."""


class DiscordPostError(DiscordBridgeError):
    """Raised when Discord rejects or cannot receive a webhook post."""


class DiscordTransientPostError(DiscordPostError):
    """Raised for retryable Discord webhook failures."""


def _load_env() -> None:
    """Load `.env` when python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _webhook_url() -> str:
    """Return the configured Discord webhook URL."""

    _load_env()
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        raise DiscordConfigError("DISCORD_WEBHOOK_URL is required for outbound Discord posts.")
    return url


def _truncate_content(content: str) -> str:
    """Safely truncate content below Discord's 2000-character limit."""

    normalized = content.strip()
    if len(normalized) <= SAFE_CONTENT_LIMIT:
        return normalized
    return f"{normalized[: SAFE_CONTENT_LIMIT - 3]}..."


def _build_payload(content: str, embed: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Build a Discord webhook payload."""

    if not content.strip() and embed is None:
        raise DiscordPostError("Discord post requires content or an embed.")

    payload: dict[str, Any] = {}
    if content.strip():
        payload["content"] = _truncate_content(content)
    if embed is not None:
        payload["embeds"] = [embed]
    return payload


def _post_once(url: str, payload: dict[str, Any]) -> int:
    """Send one Discord webhook request and return the HTTP status code."""

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise DiscordConfigError(
            "The `httpx` package is not installed. Run `pip install -r agents/requirements.txt`."
        ) from exc

    try:
        response = httpx.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
    except httpx.RequestError as exc:
        raise DiscordTransientPostError(f"Discord webhook network error: {exc}") from exc

    if 200 <= response.status_code < 300:
        return response.status_code
    if response.status_code >= 500:
        raise DiscordTransientPostError(
            f"Discord webhook transient HTTP {response.status_code}: {response.text[:200]}"
        )
    raise DiscordPostError(f"Discord webhook rejected post with HTTP {response.status_code}: {response.text[:200]}")


def post(content: str, embed: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Post a message to the configured Discord webhook.

    Args:
        content: Human-readable message from a NemoClaw claw.
        embed: Optional Discord embed dictionary.

    Returns:
        A small result dictionary with `ok`, `status_code`, and `truncated`.

    Raises:
        DiscordConfigError: If env/dependencies are missing.
        DiscordPostError: If Discord cannot receive the post after one retry.
    """

    url = _webhook_url()
    payload = _build_payload(content, embed)
    truncated = "content" in payload and len(content.strip()) > len(payload["content"])
    last_error: DiscordPostError | None = None

    for attempt in range(2):
        try:
            status_code = _post_once(url, payload)
            print(f"Discord webhook post succeeded with HTTP {status_code}.")
            return {"ok": True, "status_code": status_code, "truncated": truncated}
        except DiscordTransientPostError as exc:
            last_error = exc
            if attempt == 0:
                print(f"Discord webhook post failed once; retrying. Reason: {exc}")
                continue
            print(f"Discord webhook post failed after retry. Reason: {exc}")
        except DiscordPostError as exc:
            print(f"Discord webhook post failed without retry. Reason: {exc}")
            raise

    raise DiscordPostError("Discord webhook post failed after retry.") from last_error


def smoke_test() -> bool:
    """Send a tiny smoke-test message if `DISCORD_WEBHOOK_URL` is configured."""

    _load_env()
    if not os.environ.get("DISCORD_WEBHOOK_URL", "").strip():
        print("SKIP: DISCORD_WEBHOOK_URL is not set; Discord smoke test not sent.")
        return True

    try:
        result = post("NemoClaw smoke test: outbound Discord bridge is online.")
        print(f"OK: Discord smoke test sent: {result}")
        return True
    except DiscordBridgeError as exc:
        print(f"FAIL: Discord smoke test failed: {exc}")
        return False


if __name__ == "__main__":
    raise SystemExit(0 if smoke_test() else 1)
