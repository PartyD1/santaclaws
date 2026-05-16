"""Small Vapi integration for the NemoClaw inbound voice stretch."""

from __future__ import annotations

import os
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_BASE_URL = "https://api.vapi.ai"


class VapiClientError(RuntimeError):
    """Base Vapi integration error."""


class VapiConfigError(VapiClientError):
    """Raised when Vapi stretch configuration is missing."""


def _load_env() -> None:
    """Load `.env` if python-dotenv is available."""

    if load_dotenv is not None:
        load_dotenv()


def _env(name: str, required: bool = True) -> str | None:
    """Read a Vapi environment value."""

    _load_env()
    value = os.environ.get(name, "").strip()
    if required and not value:
        raise VapiConfigError(f"{name} is required for the Vapi inbound voice stretch.")
    return value or None


def _client() -> Any:
    """Return an HTTP client configured for Vapi."""

    api_key = _env("VAPI_API_KEY")
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise VapiConfigError(
            "The `httpx` package is not installed. Run `pip install -r agents/requirements.txt`."
        ) from exc

    base_url = os.environ.get("VAPI_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    return httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
    )


def _raise_for_vapi(response: Any, action: str) -> None:
    """Raise a readable error for non-2xx Vapi responses."""

    if 200 <= int(response.status_code) < 300:
        return
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    raise VapiClientError(f"Vapi {action} failed with {response.status_code}: {detail}")


def _assistant_payload(webhook_url: str) -> dict[str, Any]:
    """Return the inbound-only assistant configuration."""

    return {
        "name": "Mainstreet NemoClaw Inbound Closer",
        "firstMessage": "Thanks for calling Mainstreet. What can I help you with?",
        "firstMessageMode": "assistant-speaks-first",
        "server": {"url": webhook_url, "timeoutSeconds": 20},
        "serverMessages": ["status-update", "transcript", "end-of-call-report"],
        "model": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the inbound voice front door for Mainstreet NemoClaw. "
                        "Keep replies short. Do not make outbound calls. Gather the caller's "
                        "question, interest level, and preferred callback details. If they ask "
                        "to schedule, say the team will follow up with times."
                    ),
                }
            ],
        },
        "endCallMessage": "Thanks, the Mainstreet team will follow up soon.",
    }


def create_inbound_assistant(webhook_url: str) -> dict[str, Any]:
    """Create a Vapi assistant that only handles inbound calls."""

    if not webhook_url.strip():
        raise VapiConfigError("VAPI_WEBHOOK_URL is required to create the Vapi assistant.")
    with _client() as client:
        response = client.post("/assistant", json=_assistant_payload(webhook_url.strip()))
    _raise_for_vapi(response, "assistant create")
    return response.json()


def _phone_identifier(client: Any, configured_value: str) -> str:
    """Resolve a configured phone number id or E.164 number to a Vapi phone-number id."""

    if not configured_value.startswith("+"):
        return configured_value
    response = client.get("/phone-number")
    _raise_for_vapi(response, "phone-number list")
    rows = response.json()
    if not isinstance(rows, list):
        raise VapiClientError("Vapi phone-number list returned unexpected data.")
    for row in rows:
        if isinstance(row, dict) and row.get("number") == configured_value:
            return str(row["id"])
    raise VapiClientError(f"Could not find Vapi phone number {configured_value}. Use its id in VAPI_PHONE_NUMBER.")


def attach_assistant_to_phone(assistant_id: str, phone_number: str | None = None) -> dict[str, Any]:
    """Attach the inbound assistant to an existing Vapi phone number."""

    configured_phone = phone_number or _env("VAPI_PHONE_NUMBER")
    if not configured_phone:
        raise VapiConfigError("VAPI_PHONE_NUMBER is required to attach the Vapi assistant.")
    if not assistant_id.strip():
        raise VapiConfigError("assistant_id is required.")

    with _client() as client:
        phone_id = _phone_identifier(client, configured_phone)
        response = client.patch(f"/phone-number/{phone_id}", json={"assistantId": assistant_id})
    _raise_for_vapi(response, "phone-number update")
    return response.json()


def configure_inbound_assistant() -> str:
    """Create/configure the inbound-only assistant and return the public phone number.

    Required env:
        VAPI_API_KEY
        VAPI_PHONE_NUMBER
        VAPI_WEBHOOK_URL
    """

    webhook_url = _env("VAPI_WEBHOOK_URL")
    assistant = create_inbound_assistant(str(webhook_url))
    assistant_id = str(assistant.get("id") or "")
    if not assistant_id:
        raise VapiClientError("Vapi assistant create did not return an id.")
    phone = attach_assistant_to_phone(assistant_id)
    return str(phone.get("number") or _env("VAPI_PHONE_NUMBER"))


def smoke_test() -> bool:
    """Print a clear Vapi configuration smoke-test result."""

    try:
        phone = configure_inbound_assistant()
        print(f"OK: Vapi inbound assistant configured for {phone}.")
        return True
    except VapiClientError as exc:
        print(f"SKIP: Vapi inbound stretch is not configured: {exc}")
        return False
    except Exception as exc:  # pragma: no cover - keeps CLI diagnostics clear.
        print(f"FAIL: Unexpected Vapi smoke-test error: {exc}")
        return False


if __name__ == "__main__":
    raise SystemExit(0 if smoke_test() else 0)
