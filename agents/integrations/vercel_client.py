"""Vercel deployment helper for Designer mockups."""

from __future__ import annotations

import os
import re
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


VERCEL_DEPLOYMENTS_URL = "https://api.vercel.com/v13/deployments"


class VercelError(RuntimeError):
    """Raised when Vercel deployment fails."""


class VercelConfigError(VercelError):
    """Raised when Vercel credentials are missing."""


def _load_env() -> None:
    """Load `.env` when available."""

    if load_dotenv is not None:
        load_dotenv()


def _token() -> str:
    """Return Vercel token from env."""

    _load_env()
    token = os.environ.get("VERCEL_TOKEN", "").strip()
    if not token:
        raise VercelConfigError("VERCEL_TOKEN is required for Vercel mockup deployment.")
    return token


def _safe_slug(slug: str) -> str:
    """Normalize a Vercel deployment name."""

    value = re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")
    return value[:80] or "mainstreet-mockup"


def _project_name() -> str:
    """Return the stable Vercel project used for all mockup deployments."""

    _load_env()
    return (
        os.environ.get("VERCEL_PROJECT_ID", "").strip()
        or os.environ.get("VERCEL_PROJECT_NAME", "").strip()
        or "mainstreet-mockups"
    )


def deploy_html_as_site(html: str, slug: str) -> str:
    """Deploy HTML to Vercel and return the public URL."""

    if "<html" not in html.lower():
        raise VercelError("deploy_html_as_site requires a complete HTML document.")

    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise VercelConfigError("The `httpx` package is not installed. Run `pip install -r agents/requirements.txt`.") from exc

    params: dict[str, str] = {}
    team_id = os.environ.get("VERCEL_TEAM_ID", "").strip()
    if team_id:
        params["teamId"] = team_id

    safe_slug = _safe_slug(slug)
    payload: dict[str, Any] = {
        "name": _project_name(),
        "project": _project_name(),
        "files": [
            {"file": "index.html", "data": html},
            {"file": f"mockups/{safe_slug}/index.html", "data": html},
        ],
        "public": True,
        "meta": {"mainstreet_public_mockup": "true", "mainstreet_mockup_slug": safe_slug},
        "projectSettings": {"framework": None},
        "target": "production",
    }
    response = httpx.post(
        VERCEL_DEPLOYMENTS_URL,
        params=params,
        json=payload,
        headers={"Authorization": f"Bearer {_token()}"},
        timeout=60.0,
    )
    if not 200 <= response.status_code < 300:
        raise VercelError(f"Vercel deploy failed with HTTP {response.status_code}: {response.text[:300]}")
    data = response.json()
    url = data.get("url")
    if not url:
        raise VercelError("Vercel response did not include a deployment URL.")
    return f"https://{url}" if not str(url).startswith("http") else str(url)
