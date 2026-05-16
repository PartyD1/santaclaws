"""Lightweight OpenAI-compatible client for Nemotron via NemoClaw/OpenShell.

This module is intentionally small for the hackathon build: one JSON chat
helper, one vision chat helper, and a smoke test. It does not do queues,
streaming, or long-lived agent abstractions.
"""

from __future__ import annotations

import json
import os
from typing import Any, Final

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


DEFAULT_MODEL: Final[str] = "nvidia/nemotron-3-super-120b-a12b"
DEFAULT_BASE_URL: Final[str] = "https://inference.local/v1"
JSON_SYSTEM_PREFIX: Final[str] = "Return only valid JSON. Do not include markdown fences."


class NemotronClientError(RuntimeError):
    """Base exception for NemoClaw/Nemotron client failures."""


class NemotronConfigError(NemotronClientError):
    """Raised when required Nemotron environment configuration is missing."""


class NemotronJSONError(NemotronClientError):
    """Raised when Nemotron does not return parseable JSON after retries."""


def _load_env() -> None:
    """Load local `.env` values if python-dotenv is installed."""

    if load_dotenv is not None:
        load_dotenv()


def _base_url() -> str:
    """Return the configured OpenAI-compatible base URL."""

    _load_env()
    return os.environ.get("NEMOTRON_BASE_URL", DEFAULT_BASE_URL).strip()


def _model_name(model: str | None = None) -> str:
    """Return the explicit model, configured model, or hackathon default."""

    _load_env()
    return (model or os.environ.get("NEMOTRON_MODEL") or DEFAULT_MODEL).strip()


def _api_key(base_url: str) -> str:
    """Return an API key, using the NemoClaw gateway placeholder when allowed."""

    _load_env()
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if api_key:
        return api_key
    if "inference.local" in base_url:
        return "openshell"
    raise NemotronConfigError(
        "NVIDIA_API_KEY is required when NEMOTRON_BASE_URL is outside the "
        "NemoClaw/OpenShell inference route."
    )


def _client() -> Any:
    """Build an OpenAI-compatible client configured for Nemotron."""

    try:
        from openai import OpenAI
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise NemotronConfigError(
            "The `openai` package is not installed. Run `pip install -r agents/requirements.txt`."
        ) from exc

    base_url = _base_url()
    return OpenAI(base_url=base_url, api_key=_api_key(base_url))


def _json_system(system: str) -> str:
    """Prefix the caller's system prompt with the JSON-only contract."""

    system = system.strip()
    return f"{JSON_SYSTEM_PREFIX}\n\n{system}" if system else JSON_SYSTEM_PREFIX


def _extract_text(response: Any) -> str:
    """Extract assistant text from an OpenAI-compatible chat completion."""

    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError) as exc:
        raise NemotronJSONError("Nemotron response did not include message content.") from exc

    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [
            part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(text_parts).strip()
    raise NemotronJSONError(f"Unexpected Nemotron content type: {type(content).__name__}.")


def _parse_json(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object from Nemotron text."""

    try:
        value = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise NemotronJSONError(f"Nemotron returned malformed JSON: {exc.msg}") from exc

    if not isinstance(value, dict):
        raise NemotronJSONError("Nemotron returned valid JSON, but not a JSON object.")
    return value


def _retry_user_prompt(user: str, last_error: Exception) -> str:
    """Build the retry prompt for malformed JSON responses."""

    return (
        f"{user}\n\n"
        "Previous output violated the JSON-only contract. "
        f"Parse error: {last_error}. Return one valid JSON object only."
    )


def chat_json(system: str, user: str, model: str | None = None, retries: int = 1) -> dict[str, Any]:
    """Call Nemotron and return a validated JSON object.

    Args:
        system: System instructions for the model.
        user: User prompt for the model.
        model: Optional model override. Defaults to `NEMOTRON_MODEL`.
        retries: Number of malformed-JSON retries after the first attempt.

    Raises:
        NemotronConfigError: If configuration or SDK dependencies are missing.
        NemotronJSONError: If the final response cannot be parsed as a JSON object.
    """

    client = _client()
    model_name = _model_name(model)
    attempts = max(0, retries) + 1
    prompt = user
    last_error: Exception | None = None

    for attempt in range(attempts):
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": _json_system(system)},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        raw_text = _extract_text(response)
        try:
            return _parse_json(raw_text)
        except NemotronJSONError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            prompt = _retry_user_prompt(user, exc)

    raise NemotronJSONError(f"Nemotron failed to return valid JSON after {attempts} attempt(s).") from last_error


def chat_vision(system: str, user: str, image_b64: str) -> dict[str, Any]:
    """Call a vision-capable Nemotron route and return a validated JSON object.

    Args:
        system: System instructions for the model.
        user: Text prompt to send alongside the PNG screenshot.
        image_b64: Base64-encoded PNG image bytes.

    Raises:
        NemotronConfigError: If configuration or SDK dependencies are missing.
        NemotronJSONError: If the final response cannot be parsed as a JSON object.
    """

    client = _client()
    model_name = _model_name()
    prompt = user
    last_error: Exception | None = None

    for attempt in range(2):
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": _json_system(system)},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                    ],
                },
            ],
            response_format={"type": "json_object"},
        )
        raw_text = _extract_text(response)
        try:
            return _parse_json(raw_text)
        except NemotronJSONError as exc:
            last_error = exc
            if attempt == 1:
                break
            prompt = _retry_user_prompt(user, exc)

    raise NemotronJSONError("Nemotron vision failed to return valid JSON after 2 attempt(s).") from last_error


def smoke_test() -> bool:
    """Run a tiny Nemotron JSON smoke test and print a clear result."""

    try:
        result = chat_json(
            system="You are a smoke test for the Mainstreet NemoClaw runtime.",
            user='Return exactly {"ok": true}.',
            retries=1,
        )
        if result.get("ok") is True:
            print("OK: Nemotron JSON smoke test passed.")
            return True
        print(f"FAIL: Nemotron JSON smoke test returned unexpected JSON: {result}")
        return False
    except NemotronClientError as exc:
        print(f"FAIL: Nemotron JSON smoke test failed: {exc}")
        return False
    except Exception as exc:  # pragma: no cover - keeps CLI diagnostics clear.
        print(f"FAIL: Unexpected Nemotron smoke test error: {exc}")
        return False


def test_nemotron() -> bool:
    """Backward-compatible Task 8 smoke-test entrypoint."""

    return smoke_test()


if __name__ == "__main__":
    raise SystemExit(0 if smoke_test() else 1)
