"""Smoke-check external services before the Mainstreet NemoClaw demo."""

from __future__ import annotations

import argparse
import time
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]

from agents.integrations import apify_client
from agents.shared import nemotron_client


def _load_env() -> None:
    """Load `.env` values if python-dotenv is installed."""

    if load_dotenv is not None:
        load_dotenv()


def check_nemotron(rounds: int = 3) -> dict[str, Any]:
    """Run small JSON calls and estimate usable Nemotron latency."""

    timings: list[float] = []
    errors: list[str] = []
    for index in range(max(1, rounds)):
        started = time.perf_counter()
        try:
            result = nemotron_client.chat_json(
                system="You are a NemoClaw rate-limit smoke test. Return JSON only.",
                user=f'Return exactly {{"ok": true, "round": {index + 1}}}.',
                retries=1,
            )
            if result.get("ok") is not True:
                errors.append(f"round {index + 1}: unexpected JSON {result}")
        except Exception as exc:
            errors.append(f"round {index + 1}: {exc}")
        finally:
            timings.append(time.perf_counter() - started)

    successful = max(0, rounds - len(errors))
    avg_seconds = sum(timings) / len(timings)
    estimated_rpm = int(60 / avg_seconds) if successful and avg_seconds > 0 else 0
    return {
        "service": "nemotron",
        "successful": successful,
        "attempted": rounds,
        "avg_seconds": round(avg_seconds, 2),
        "estimated_single_worker_rpm": estimated_rpm,
        "errors": errors,
    }


def check_apify() -> dict[str, Any]:
    """Run a one-result Apify Google Places smoke check."""

    try:
        rows = apify_client.scrape_google_places(
            search_query="auto repair",
            location="Santa Cruz, CA",
            max_results=1,
            include_emails=False,
        )
        return {"service": "apify", "ok": True, "rows": len(rows), "errors": []}
    except Exception as exc:
        return {"service": "apify", "ok": False, "rows": 0, "errors": [str(exc)]}


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Check Nemotron and Apify readiness for Mainstreet NemoClaw.")
    parser.add_argument("--nemotron-rounds", type=int, default=3)
    parser.add_argument("--skip-apify", action="store_true")
    args = parser.parse_args()

    _load_env()
    results = [check_nemotron(max(1, args.nemotron_rounds))]
    if not args.skip_apify:
        results.append(check_apify())

    failed = False
    for result in results:
        errors = result.get("errors") or []
        status = "OK" if not errors and result.get("ok", True) is not False else "SKIP"
        if errors:
            failed = True
        print(f"{status}: {result}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
