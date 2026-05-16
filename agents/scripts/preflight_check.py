"""Preflight readiness check for the Mainstreet NemoClaw demo runtime."""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
from dataclasses import dataclass
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency validation catches this.
    load_dotenv = None  # type: ignore[assignment]


REQUIRED_ENV = [
    "NEMOTRON_BASE_URL",
    "NEMOTRON_MODEL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
]
OPTIONAL_ENV = [
    "APIFY_TOKEN",
    "RESEND_API_KEY",
    "OUTREACH_FROM_ADDRESS",
    "DISCORD_WEBHOOK_URL",
    "VERCEL_TOKEN",
    "GCAL_CLIENT_ID",
]
REQUIRED_PACKAGES = ["openai", "supabase", "dotenv", "httpx"]
REQUIRED_TABLES = [
    "leads",
    "actions",
    "generated_sites",
    "outreach",
    "inbound",
    "meetings",
    "approvals",
    "config",
    "agent_memory",
]


@dataclass
class Check:
    """One preflight check result."""

    name: str
    ok: bool
    detail: str
    required: bool = True

    @property
    def status(self) -> str:
        """Return a short status label."""

        if self.ok:
            return "OK"
        return "FAIL" if self.required else "WARN"


def _load_env() -> None:
    """Load local `.env` values when python-dotenv is installed."""

    if load_dotenv is not None:
        load_dotenv()


def _masked(value: str | None) -> str:
    """Return a non-secret display value."""

    if not value:
        return "missing"
    if len(value) <= 10:
        return "set"
    return f"{value[:4]}...{value[-4:]}"


def _check_python() -> Check:
    """Check Python version."""

    version = platform.python_version()
    major, minor, *_ = platform.python_version_tuple()
    ok = int(major) == 3 and int(minor) >= 11
    detail = f"Python {version}"
    if not ok:
        detail += " detected; project target is Python 3.11+"
    return Check("python", ok, detail)


def _check_packages() -> list[Check]:
    """Check required Python packages without importing them."""

    checks = []
    for package in REQUIRED_PACKAGES:
        checks.append(
            Check(
                f"package:{package}",
                importlib.util.find_spec(package) is not None,
                "installed" if importlib.util.find_spec(package) is not None else "missing",
            )
        )
    return checks


def _check_env() -> list[Check]:
    """Check required and optional environment variables."""

    checks = []
    for name in REQUIRED_ENV:
        value = os.environ.get(name, "").strip()
        checks.append(Check(f"env:{name}", bool(value), _masked(value)))
    for name in OPTIONAL_ENV:
        value = os.environ.get(name, "").strip()
        checks.append(Check(f"env:{name}", bool(value), _masked(value), required=False))
    return checks


def _supabase_client() -> Any:
    """Build a Supabase client from the current environment."""

    from supabase import create_client

    url = os.environ["SUPABASE_URL"].strip()
    key = os.environ["SUPABASE_SERVICE_KEY"].strip()
    return create_client(url, key)


def _check_tables() -> list[Check]:
    """Check that expected Supabase tables are queryable."""

    try:
        client = _supabase_client()
    except Exception as exc:
        return [Check("supabase:connect", False, str(exc))]

    checks = [Check("supabase:connect", True, "service client created")]
    for table in REQUIRED_TABLES:
        try:
            client.table(table).select("*").limit(1).execute()
            checks.append(Check(f"table:{table}", True, "queryable"))
        except Exception as exc:
            checks.append(Check(f"table:{table}", False, str(exc)))
    return checks


def _print(checks: list[Check]) -> None:
    """Print human-readable preflight output."""

    for check in checks:
        print(f"{check.status}: {check.name} - {check.detail}")


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Check Mainstreet NemoClaw runtime readiness.")
    parser.add_argument("--skip-live", action="store_true", help="Skip live Supabase table checks.")
    args = parser.parse_args()

    _load_env()
    checks = [_check_python(), *_check_packages(), *_check_env()]
    if not args.skip_live:
        checks.extend(_check_tables())

    _print(checks)
    return 1 if any(not check.ok and check.required for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
