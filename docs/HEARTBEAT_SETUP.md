# Heartbeat Setup Guide

How to add an agent to the OpenClaw-compatible heartbeat system and run it automatically.

---

## How It Works

Each agent runs a `heartbeat()` function on a timed loop. The loop is driven by `openclaw_run.py`, which reads configuration from two places:

1. **`agents/nemoclaw.json`** — registers the agent with the OpenClaw runtime (name, entrypoint, interval, description)
2. **`agents/{name}/HEARTBEAT.md`** — per-agent file declaring the same interval and entrypoint

At startup, `openclaw_run.py` loads each agent's 5 context files, resolves the `heartbeat()` callable, and spawns a thread that calls it on the declared interval. If `heartbeat()` raises an exception, the error is logged and the thread retries on the next interval.

---

## Adding a New Agent

### 1. Create the agent directory

```
agents/
  myagent/
    __init__.py
    claw.py
    SOUL.md
    AGENTS.md
    TOOLS.md
    HEARTBEAT.md
    MEMORY.md
    tools/
```

All 5 `.md` files are required — the runtime will refuse to start without them.

### 2. Write the heartbeat function in `claw.py`

```python
def heartbeat() -> dict:
    """Run one MyAgent heartbeat."""
    # 1. Claim work from Supabase
    # 2. Run tools
    # 3. Log action to actions table
    # 4. Update row in database
    return {"status": "ok"}

def main() -> int:
    """CLI entrypoint."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        heartbeat()
        return 0
    from agents.scripts.openclaw_run import _run_loop
    from agents.shared.openclaw_runtime import load_openclaw_context
    ctx = load_openclaw_context("myagent")
    _run_loop(ctx, heartbeat)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

### 3. Write `HEARTBEAT.md`

```
# MyAgent Heartbeat

interval: 60s
entrypoint: claw.py:heartbeat
```

- `interval` — seconds between heartbeats (suffix `s` required)
- `entrypoint` — `<filename>:<function>` within the agent's package

### 4. Fill in the other context files

| File | Purpose |
|------|---------|
| `SOUL.md` | Agent identity and personality |
| `AGENTS.md` | Operational instructions |
| `TOOLS.md` | List of tools the agent can call |
| `MEMORY.md` | Persistent memory (max ~200 lines) |

These are passed as prompt context to Nemotron on each heartbeat.

### 5. Register in `agents/nemoclaw.json`

Add an entry to the `agents` array:

```json
{
  "name": "myagent",
  "entrypoint": "claw.py:heartbeat",
  "interval": "60s",
  "description": "One-line description of what this agent does"
}
```

This is the single source of truth OpenClaw uses to discover agents. The `VALID_CLAWS` set in `openclaw_runtime.py` is derived from this file at import time — no code change needed.

---

## Running Agents

### One heartbeat (debugging)

```bash
python -m agents.scripts.openclaw_run myagent --once
# or via the claw directly:
python -m agents.myagent.claw --once
```

### Continuous loop (single agent)

```bash
python -m agents.scripts.openclaw_run myagent
```

### All agents in one process

```bash
python -m agents.scripts.openclaw_run all
```

### All agents in the background

```bash
agents/scripts/start_all_claws.sh
# PID → logs/all_claws.pid
# Log → logs/all_claws.log
```

### Stop background agents

```bash
agents/scripts/stop_all_claws.sh
```

### Check if running

```bash
kill -0 $(cat logs/all_claws.pid) && echo running || echo stopped
tail -f logs/all_claws.log
```

---

## How the Runtime Resolves the Entrypoint

Given `entrypoint: claw.py:heartbeat` for an agent named `myagent`:

1. Split on `:` → file `claw.py`, function `heartbeat`
2. Strip `.py` → module name `claw`
3. Import `agents.myagent.claw`
4. Call `getattr(module, "heartbeat")`

This means the entrypoint must be importable as `agents.{name}.{file_without_py}:{function}`.

---

## Key Files

| File | Role |
|------|------|
| `agents/nemoclaw.json` | Agent registry — add new agents here |
| `agents/shared/openclaw_runtime.py` | Loads context files, validates agents, exposes `VALID_CLAWS` and `list_agents()` |
| `agents/scripts/openclaw_run.py` | CLI runner — supports single agent or `all` |
| `agents/scripts/start_all_claws.sh` | Background launcher with PID tracking |
| `agents/scripts/stop_all_claws.sh` | Graceful shutdown |
