"""Run a NemoClaw claw through its OpenClaw-compatible HEARTBEAT.md."""

from __future__ import annotations

import argparse
import importlib
import threading
import time
from collections.abc import Callable
from typing import Any

from agents.shared.openclaw_runtime import VALID_CLAWS, OpenClawContext, list_agents, load_openclaw_context


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
        try:
            heartbeat()
        except Exception as exc:
            print(f"[{context.claw_name}] heartbeat error (will retry in {context.interval_seconds}s): {exc}")
        time.sleep(context.interval_seconds)


def _run_all(once: bool = False) -> int:
    """Load and run all registered agents concurrently."""

    agents = list_agents()
    if not agents:
        print("No agents found in nemoclaw.json.")
        return 1

    contexts = []
    for agent_cfg in agents:
        ctx = load_openclaw_context(agent_cfg["name"])
        contexts.append(ctx)
        print(
            f"OpenClaw-compatible context loaded for {ctx.claw_name}: "
            f"{ctx.entrypoint} every {ctx.interval_seconds}s."
        )

    if once:
        for ctx in contexts:
            heartbeat = _entrypoint_callable(ctx)
            heartbeat()
        return 0

    threads = []
    for ctx in contexts:
        heartbeat = _entrypoint_callable(ctx)
        t = threading.Thread(target=_run_loop, args=(ctx, heartbeat), name=ctx.claw_name, daemon=True)
        t.start()
        threads.append(t)

    print(f"All {len(threads)} agents running. Press Ctrl+C to stop.")
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print("\nShutting down all agents.")
    return 0


def main() -> int:
    """CLI entrypoint."""

    all_choices = sorted(VALID_CLAWS) + ["all"]
    parser = argparse.ArgumentParser(description="Run a NemoClaw claw via OpenClaw-compatible context files.")
    parser.add_argument("claw", choices=all_choices, help="Claw name to run, or 'all' to run every registered agent.")
    parser.add_argument("--once", action="store_true", help="Run one heartbeat and exit.")
    args = parser.parse_args()

    if args.claw == "all":
        return _run_all(once=args.once)

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
