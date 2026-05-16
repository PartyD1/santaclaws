"""Resend inbound email worker status helper.

Resend posts directly to the Next.js route at
`dashboard/app/api/inbound-email/route.ts`. This worker remains as a harmless
CLI pointer for operators who look in `workers/` during the demo.
"""

from __future__ import annotations


def status() -> dict[str, str]:
    """Return the active inbound email handling path."""

    return {
        "status": "handled_by_dashboard_route",
        "route": "dashboard/app/api/inbound-email/route.ts",
        "runbook": "Configure Resend inbound webhook to POST /api/inbound-email.",
    }


def main() -> int:
    """Print the inbound email worker status."""

    print(status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
