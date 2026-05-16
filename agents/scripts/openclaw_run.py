"""Run a NemoClaw claw through its OpenClaw-compatible HEARTBEAT.md."""

from __future__ import annotations

import argparse
import importlib
import time
from collections.abc import Callable
from typing import Any

from agents.shared.openclaw_runtime import VALID_CLAWS, OpenClawContext, load_openclaw_context


def _entrypoint_callable(context: OpenClawContext) -> Callable[[], Any]:
    """Resolve `claw.py:heartbeat` into a Python callable."""

    file_part, function_name = context.entrypoint.split(":", 1)
    module_name = file_part.removesuffix(".py").replace("/", ".")
    module = importlib.import_module(f"agents.{context.claw_name}.{module_name}")
    function = getattr(module, function_name, None)
    if not callable(function):
        raise RuntimeError(f"{context.entrypoint} did not resolve to a callable.")
    return function


def _run_loop(context: OpenClawContext, heartbeat: Callable[[], Any]) -> None:
    """Run a claw forever at the interval declared in HEARTBEAT.md."""

    while True:
        heartbeat()
        time.sleep(context.interval_seconds)


def main() -> int:
    """CLI entrypoint."""

    parser = argparse.ArgumentParser(description="Run a NemoClaw claw via OpenClaw-compatible context files.")
    parser.add_argument("claw", choices=sorted(VALID_CLAWS), help="Claw name to run.")
    parser.add_argument("--once", action="store_true", help="Run one heartbeat and exit.")
    args = parser.parse_args()

    context = load_openclaw_context(args.claw)
    heartbeat = _entrypoint_callable(context)
    print(
        f"OpenClaw-compatible context loaded for {context.claw_name}: "
        f"{context.entrypoint} every {context.interval_seconds}s."
    )
    if args.once:
        heartbeat()
        return 0
    _run_loop(context, heartbeat)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
