# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Mainstreet is a 24-hour hackathon build for a NemoClaw-powered autonomous sales team. Four claws (Scout, Designer, Pitcher, Closer) coordinate through Supabase to find local auto repair shops, generate website mockups, draft personalized outreach emails, and handle inbound replies. A Next.js dashboard provides real-time visibility into the workflow.

**Core constraint**: This is a demo-first hackathon build. Prioritize reliability over perfect architecture. Avoid auth, billing, settings pages, or production-scale abstractions.

## Quick Start

```bash
# Python environment
python -m venv .venv
source .venv/bin/activate
pip install -r agents/requirements.txt

# Dashboard
cd dashboard && npm install

# Copy environment template
cp .env.example .env

# Python validation
python -m agents.scripts.preflight_check --skip-live

# Run individual claws
python -m agents.scout.claw --once
python -m agents.designer.claw --once
python -m agents.pitcher.claw --once
python -m agents.closer.claw --once

# Run all claws continuously
agents/scripts/start_all_claws.sh

# Run dashboard
cd dashboard && npm run dev
```

## Architecture

### High-Level Design

```
NemoClaw / OpenShell Sandbox
  ├── Scout claw      → finds leads, scores websites, extracts pain points
  ├── Designer claw   → generates 3 Tailwind mockups, picks winner
  ├── Pitcher claw    → generates 4 email angles, queues for approval
  └── Closer claw     → classifies replies, books meetings
        │
        ├─ Python tool layer (Apify, Nemotron, Resend, Google Calendar, etc.)
        │
        v
    Supabase (Queue + Memory + Audit Log)
        │
        v
    Next.js 14 Dashboard (Real-time feeds, metrics, lead details)
```

**Key principle**: Claws do NOT call each other directly. Supabase is the queue, shared memory, and audit log. Every meaningful action writes to the `actions` table.

### Codebase Structure

```
agents/                          Python 3.11 NemoClaw claws
  ├── scout/                     Lead scraping, website scoring, pain extraction
  ├── designer/                  Mockup generation and winner selection
  ├── pitcher/                   Email generation and approval workflow
  ├── closer/                    Reply classification, meeting booking
  ├── shared/                    Nemotron client, Supabase helpers, logger, types
  ├── integrations/              Apify, Resend, Google Calendar, Vercel stubs
  ├── scripts/                   preflight_check, seed_demo_data, claw runners
  ├── prompts/                   Shared prompts used by claws
  └── nemoclaw.json              NemoClaw runtime config

dashboard/                       Next.js 14 App Router
  ├── app/                       Pages and API routes
  │   ├── page.tsx              Main dashboard with metrics and claw cards
  │   ├── leads/[id]/page.tsx   Lead detail + all associated activity
  │   ├── claws/[name]/page.tsx Claw-specific status, logs, memory, queue
  │   └── api/
  │       ├── inbound-email/    Resend webhook for inbound emails
  │       ├── discord-reply/    Discord approval command parsing
  │       └── trigger-demo/     Manual demo flow trigger
  ├── components/               Reusable UI (MetricsBar, LeadsTable, ActivityFeed)
  ├── lib/                       Supabase clients and helpers
  └── tailwind.config.ts         UI styling (no custom theme)

workers/                         Long-running bridge processes
  ├── discord_bridge.py          Listens for approval commands in Discord
  ├── inbound_email_worker.py    Placeholder for email ingestion
  └── vapi_webhook.py            Stretch goal: voice reply handling

docs/                           Planning and status
  ├── PROGRESS.md               Current implementation status
  ├── Mainstreet_NemoClaw_Codex_Execution_Spec.md  Full task list
  ├── DEMO_RUNBOOK.md           Step-by-step demo instructions
  └── FALLBACK_PLAN.md          Offline/demo-data paths

AGENTS.md                       Hackathon rules and constraints
SETUP.md                        Team setup commands for Brev/Ubuntu
```

## Key Patterns

### Heartbeat Pattern (Each Claw)

All claws follow this pattern:

```python
def main(once: bool = False):
    """One claw heartbeat iteration."""
    # 1. Load env, init Supabase
    # 2. Claim one unit of work (e.g., next_scout_target, next_designer_lead)
    # 3. Run tool(s) (score_website, generate_mockup, etc.)
    # 4. Log action to actions table (always, even on failure)
    # 5. Update row in database
    # 6. Sleep and repeat (unless --once flag)
```

Entry points:
- `python -m agents.{scout,designer,pitcher,closer}.claw --once` (single heartbeat)
- `agents/scripts/start_all_claws.sh` (all claws in background via openclaw_run.py)

### Supabase as Queue + Memory

**Database tables**:
- `leads` — business data, website score, qualification status, enrichment
- `generated_sites` — HTML mockups, chosen variant, deploy URLs
- `outreach` — drafted and sent emails, approval status
- `approvals` — human decisions from Discord (approve/edit/skip)
- `inbound` — email/voice replies awaiting Closer handling
- `meetings` — booked or demo-fallback meetings
- `actions` — every claw action (started/succeeded/failed/skipped) with logs
- `agent_memory` — persisted claw memory for Nemotron context
- `config` — runtime knobs (niche, city, autonomous_mode, quiet_hours)

All helpers in `agents/shared/supabase_client.py` assume thin direct table queries, no ORM.

### Nemotron Integration

- Located in `agents/shared/nemotron_client.py`
- OpenAI-compatible client (uses openai Python package)
- Default model: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`
- Default route: `https://inference.local/v1` (NemoClaw/OpenShell gateway)
- For structured output, prefix system message with: `"Return only valid JSON. Do not include markdown fences."`
- Two helpers: `chat_json()` for text→JSON, `chat_vision()` for image analysis

### Action Logging

Every claw action MUST log to `actions` table for dashboard visibility:

```python
from agents.shared.logger import logger

logger.log(
    claw_name="scout",
    action_type="scrape_leads",
    status="succeeded",           # or "failed", "skipped", "started"
    message="Found 5 new leads",
    lead_id=str(lead_uuid),      # optional
    result={"count": 5}          # optional
)
```

The dashboard displays `human_readable_log` field in real time.

## Common Commands

### Development & Validation

```bash
# Type check dashboard
cd dashboard && npm run typecheck

# Build dashboard (validates)
cd dashboard && npm run build

# Compile all Python (catches syntax errors)
python -m compileall agents integrations workers

# Run preflight checker (checks env, packages, Supabase)
python -m agents.scripts.preflight_check

# Skip Supabase check (local-only validation)
python -m agents.scripts.preflight_check --skip-live

# Seed demo data (for testing without live services)
python -m agents.scripts.seed_demo_data --clear
```

### Running Claws

```bash
# Single heartbeat (useful for debugging)
python -m agents.scout.claw --once
python -m agents.designer.claw --once
python -m agents.pitcher.claw --once
python -m agents.closer.claw --once

# All claws in background (via openclaw_run.py orchestrator)
agents/scripts/start_all_claws.sh

# Stop all background claws
agents/scripts/stop_all_claws.sh

# Discord approval worker (standalone, independent of claws)
python -m workers.discord_bridge
```

### Dashboard

```bash
cd dashboard

# Dev server (hot reload)
npm run dev

# Check for TypeScript errors
npm run typecheck

# Production build
npm run build

# Production server
npm start
```

## Environment Variables

**Python claws** (`.env`):
- `NEMOCLAW_SANDBOX_NAME=mainstreet` — NemoClaw sandbox name
- `NEMOTRON_BASE_URL=https://inference.local/v1` — Inference endpoint
- `NEMOTRON_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` — Model name
- `NVIDIA_API_KEY=` — For direct NVIDIA API calls (optional in NemoClaw)
- `SUPABASE_URL=` — Supabase project URL (required)
- `SUPABASE_ANON_KEY=` — Supabase anon key (required for reads)
- `SUPABASE_SERVICE_KEY=` — Supabase service key (required for writes)
- `APIFY_TOKEN=` — Apify actor token
- `RESEND_API_KEY=` — Resend email API key
- `OUTREACH_FROM_ADDRESS=` — Email sender address
- `VERCEL_TOKEN=` — Vercel deployment token (fallback: uses Supabase Storage)
- `DISCORD_WEBHOOK_URL=` — Webhook for summary posts
- `DISCORD_BOT_TOKEN=` — Bot token for approval commands
- `DISCORD_APPROVAL_CHANNEL_ID=` — Channel ID for approval messages
- `GCAL_CLIENT_ID=`, `GCAL_CLIENT_SECRET=`, `GCAL_REFRESH_TOKEN=` — Google Calendar
- `AUTONOMOUS_MODE=false` — Auto-approve pitches (default: human Discord approval)
- `IGNORE_QUIET_HOURS=true` — Ignore quiet hours (demo mode)

**Dashboard** (`dashboard/.env.local`):
- `NEXT_PUBLIC_SUPABASE_URL=` — Public Supabase URL (browser-safe)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY=` — Public anon key (browser-safe)
- `SUPABASE_URL=` — Supabase URL (server-side only)
- `SUPABASE_SERVICE_KEY=` — Service key (server-side only, for webhooks)

## Constraints & Hackathon Rules

From `AGENTS.md`:

1. **Demo reliability over perfect architecture** — Use fallbacks, skip features if needed.
2. **Section 10 tasks in order** — See `docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md`.
3. **Keep diffs small and scoped** — One task per commit.
4. **No auth, billing, settings, production abstractions** — Hackathon scope only.
5. **No scope expansion** unless spec explicitly says stretch.
6. **NemoClaw/Nemotron language** — Not "OpenClaw" unless compatibility.
7. **Validate after every task** — Use preflight_check and pytest.
8. **Update `docs/PROGRESS.md`** — Always record what was done.
9. **Implement fallbacks when blocked** — See FALLBACK_PLAN.md.

## Key Files to Read Before Making Changes

- `README.md` — Project overview and happy path
- `AGENTS.md` — Hackathon rules and constraints
- `SETUP.md` — Team setup commands
- `docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md` — Full execution spec and task list
- `docs/PROGRESS.md` — Current implementation status (update after changes)
- `agents/shared/SHARED_VALUES.md` — Design philosophy

## Important Implementation Notes

### Tool Structure

Each claw has a `tools/` subdirectory with independent functions:

```python
# tools/scrape_leads.py
def run(target: dict) -> int:
    """Returns count of inserted leads."""
```

Tools should be **pure functions** where possible — accept explicit args, return typed results, avoid global state.

### Error Handling

Claws must fail gracefully:
- Missing credentials → use demo fallback (e.g., deterministic fallback mockup)
- API failures → log, mark action as "failed", continue to next heartbeat
- Malformed data → log, mark as "skipped", do not crash

Example from Designer:
```python
try:
    mockup = generate_mockup(...)
except Exception as exc:
    logger.log(..., status="failed", message=str(exc))
    return fallback_mockup()  # Deterministic fallback
```

### Dashboard Real-Time Updates

- Dashboard reads `actions` table with Supabase Realtime subscriptions (with polling fallback).
- API routes are thin: `inbound-email` webhook validates and inserts; `discord-reply` parses commands.
- All rendering is client-side React with TypeScript strict mode.

### Demo Data

Run `python -m agents.scripts.seed_demo_data --clear` to reset the database with test leads, all prefixed with `DEMO` for easy filtering.

## When in Doubt

1. Check `docs/PROGRESS.md` for implementation status.
2. Review `docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md` for task scope.
3. Look at an existing claw (e.g., `agents/scout/claw.py`) for the heartbeat pattern.
4. Check `agents/shared/supabase_client.py` for common database queries.
5. Run `python -m agents.scripts.preflight_check` before and after changes.
