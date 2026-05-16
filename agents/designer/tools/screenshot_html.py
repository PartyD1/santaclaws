"""Designer tool for screenshotting generated HTML with Playwright."""

from __future__ import annotations

import base64


class ScreenshotError(RuntimeError):
    """Raised when HTML screenshotting fails."""


def run(html: str) -> bytes:
    """Render HTML in headless Chromium and return PNG bytes."""

    if not html.strip():
        raise ScreenshotError("html cannot be empty.")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - local setup issue.
        raise ScreenshotError(
            "Playwright is not installed. Run `pip install -r agents/requirements.txt` and `playwright install chromium`."
        ) from exc

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.set_content(html, wait_until="networkidle")
            png = page.screenshot(full_page=True, type="png")
            browser.close()
            return png
    except Exception as exc:
        raise ScreenshotError(f"failed to screenshot HTML: {exc}") from exc


def run_b64(html: str) -> str:
    """Render HTML and return base64-encoded PNG bytes."""

    return base64.b64encode(run(html)).decode("ascii")
