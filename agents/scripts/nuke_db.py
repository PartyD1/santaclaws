"""Guarded demo-data cleanup helper.

This intentionally does not wipe the database. For the hackathon demo, the only
safe reset operation is clearing rows created by `seed_demo_data.py`.
"""

from __future__ import annotations

import argparse

from agents.scripts.seed_demo_data import clear_demo_data
from agents.shared.supabase_client import get_client


def main() -> int:
    """CLI entrypoint for a guarded cleanup."""

    parser = argparse.ArgumentParser(description="Clear Mainstreet demo fallback data.")
    parser.add_argument("--demo-only", action="store_true", help="Clear only rows with the DEMO - prefix.")
    parser.add_argument("--yes", action="store_true", help="Confirm the guarded cleanup.")
    args = parser.parse_args()

    if not args.demo_only or not args.yes:
        print("Refusing to reset data. Use --demo-only --yes to clear only seeded demo rows.")
        return 1

    removed = clear_demo_data(get_client())
    print(f"Cleared demo data for {removed} lead(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
