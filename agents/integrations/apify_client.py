"""Apify Google Places integration for Scout."""

from __future__ import annotations

import os
import time
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


APIFY_ACTOR = "compass/crawler-google-places"
APIFY_TIMEOUT_SECONDS = 120.0


class ApifyError(RuntimeError):
    """Raised when Apify scraping fails."""


class ApifyConfigError(ApifyError):
    """Raised when Apify configuration is missing."""


def _load_env() -> None:
    """Load `.env` when available."""

    if load_dotenv is not None:
        load_dotenv()


def _token() -> str:
    """Return the Apify API token from env."""

    _load_env()
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        raise ApifyConfigError("APIFY_TOKEN is required for Scout lead scraping.")
    return token


def _actor_url() -> str:
    """Build the run-sync dataset endpoint for the configured actor."""

    actor_id = APIFY_ACTOR.replace("/", "~")
    return f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"


def scrape_google_places(
    search_query: str,
    location: str,
    max_results: int = 20,
    include_emails: bool = True,
    only_no_website: bool = False,
) -> list[dict[str, Any]]:
    """Scrape Google Places results through Apify.

    Args:
        search_query: Business type to search, e.g. `auto repair`.
        location: City/state, e.g. `Santa Cruz, CA`.
        max_results: Maximum places to crawl.
        include_emails: Ask Apify to scrape contact fields.
        only_no_website: Filter to places without websites when supported.

    Returns:
        Raw Apify dataset items.
    """

    if not search_query.strip():
        raise ApifyError("search_query cannot be empty.")
    if not location.strip():
        raise ApifyError("location cannot be empty.")

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise ApifyConfigError("The `httpx` package is not installed. Run `pip install -r agents/requirements.txt`.") from exc

    payload: dict[str, Any] = {
        "searchStringsArray": [search_query],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": max(1, int(max_results)),
        "scrapeContacts": include_emails,
        "scrapeReviewsCount": 10,
    }
    if only_no_website:
        payload["website"] = "withoutWebsite"

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = httpx.post(
                _actor_url(),
                params={"token": _token()},
                json=payload,
                timeout=APIFY_TIMEOUT_SECONDS,
            )
            if 200 <= response.status_code < 300:
                data = response.json()
                if not isinstance(data, list):
                    raise ApifyError(f"Apify returned {type(data).__name__}, expected list.")
                return data
            if response.status_code >= 500:
                raise ApifyError(f"Apify transient HTTP {response.status_code}: {response.text[:200]}")
            raise ApifyError(f"Apify rejected scrape with HTTP {response.status_code}: {response.text[:200]}")
        except (httpx.RequestError, ApifyError) as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(2)
                continue
            break

    raise ApifyError(f"Apify scrape failed after retry: {last_error}") from last_error
