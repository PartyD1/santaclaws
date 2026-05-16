# Santa Claws

Santa Claws is a 24-hour hackathon build for a four-claw autonomous sales workshop powered by NemoClaw, Nemotron, Supabase, and a live Next.js dashboard.

The demo target is local service businesses in Santa Cruz County. The system finds businesses with weak or missing websites, generates redesign mockups, drafts personalized outreach, routes approvals through Discord, and handles interested replies through the Santa Claws closer agent.

## Current State

The repo has the core demo pipeline implemented through Section 10 Task 41 of the execution spec:

- Rudolph Scout tools and heartbeat for scraping, website scoring, and review pain extraction.
- Workshop Elves tools and heartbeat for generating mockup variants, self-critiquing, picking a winner, and deploying via Vercel or Supabase Storage fallback.
- Snowball Pitcher tools and heartbeat for generating email angles, self-critiquing, queuing approval, and sending through Resend.
- Cookie Closer tools and heartbeat for classifying inbound replies, proposing meeting times, drafting replies, and booking Google Calendar meetings or demo fallback meetings.
- Supabase schema, shared client helpers, action logger, dataclasses, memory updater, and demo data seeder.
- Next.js dashboard with metrics, leads table, activity feed, lead detail pages, and inbound email webhook.
- Start/stop scripts for running all claws locally.

Manual setup tasks are still open for the live demo: NemoClaw onboarding, Supabase project creation, Resend DNS, Vercel project setup, Discord setup, Google Calendar credentials, and optional Vapi stretch work. See [docs/PROGRESS.md](docs/PROGRESS.md) for the exact checklist and validation history.

## Demo Story

The concise story for judges:

> NemoClaw gives us secure always-on claws; Supabase gives them shared memory; Nemotron gives them reasoning.

The claws do not call each other directly. Supabase is the queue, the shared memory layer, and the audit log. Every meaningful action writes a row to `actions`, which is what the dashboard shows in real time.

Happy path for one lead:

1. Rudolph Scout finds and qualifies a local service lead.
2. The Workshop Elves create mockup variants and pick the best redesign.
3. Snowball Pitcher drafts and critiques outreach, then queues it for approval.
4. A human approves in Discord, or `AUTONOMOUS_MODE=true` auto-approves.
5. Snowball Pitcher sends the email through Resend.
6. Inbound replies land in Supabase.
7. Cookie Closer classifies the reply, proposes times, drafts a response, and books a meeting.

## Repository Layout

```text
.
|-- agents/                 Python 3.11 NemoClaw claws, tools, prompts, shared helpers
|-- dashboard/              Next.js 14 App Router dashboard and webhooks
|-- docs/                   Execution spec and live progress notes
|-- integrations/           Top-level integration clients kept for compatibility
|-- nemoclaw/               NemoClaw/OpenShell setup notes and runtime policy docs
|-- workers/                Long-running bridge workers
|-- .env.example            Environment variable template
|-- docker-compose.yml      Placeholder for optional local services
`-- README.md               This project guide
```

Important docs:

- [Execution spec](docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md)
- [Progress log](docs/PROGRESS.md)
- [Agents README](agents/README.md)
- [Dashboard README](dashboard/README.md)
- [NemoClaw README](nemoclaw/README.md)

## Architecture

```text
NemoClaw / OpenShell sandbox
  |-- Rudolph Scout
  |-- Workshop Elves
  |-- Snowball Pitcher
  `-- Cookie Closer
        |
        v
Python tool layer
  |-- Apify
  |-- Nemotron
  |-- Supabase
  |-- Resend
  |-- Vercel / Supabase Storage
  |-- Discord
  `-- Google Calendar
        |
        v
Supabase Postgres + Realtime
        |
        v
Next.js dashboard
```

Core tables:

- `leads`: scraped businesses, enrichment, qualification, and workflow flags.
- `actions`: claw activity log for the dashboard.
- `generated_sites`: HTML mockups, chosen winner, critique scores, hosted URLs.
- `outreach`: drafted and sent emails.
- `approvals`: human approval decisions from Discord or fallback flows.
- `inbound`: inbound email or voice replies awaiting Closer handling.
- `meetings`: booked or demo-fallback meetings.
- `config`: runtime knobs such as target niche/city and autonomous mode.

## Prerequisites

- Python 3.11.
- Node.js 18+ and npm.
- Supabase project with the schema from [agents/scripts/setup_supabase.sql](agents/scripts/setup_supabase.sql).
- NemoClaw/OpenShell sandbox for the real runtime story.
- NVIDIA/Nemotron credentials or a NemoClaw-routed inference endpoint.
- Optional live integrations: Apify, Resend, Vercel, Discord, Google Calendar, Vapi.

The local code is written to fail clearly or use demo fallbacks when credentials are missing, but the full live demo needs the external services configured.

## Environment

Start from the template:

```bash
cp .env.example .env
```

Python claws read these main variables:

```bash
NEMOCLAW_SANDBOX_NAME=mainstreet
NEMOTRON_BASE_URL=https://inference.local/v1
NEMOTRON_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
NVIDIA_API_KEY=

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

APIFY_TOKEN=
SCOUT_NICHES=dentist,plumber,electrician,landscaper,roofing contractor,HVAC contractor,pet groomer,auto detailing
RESEND_API_KEY=
OUTREACH_FROM_ADDRESS=
VERCEL_TOKEN=
VERCEL_TEAM_ID=
VERCEL_PROJECT_ID=
VERCEL_PROJECT_NAME=mainstreet-mockups
DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
DISCORD_APPROVAL_CHANNEL_ID=
GCAL_CLIENT_ID=
GCAL_CLIENT_SECRET=
GCAL_REFRESH_TOKEN=

AUTONOMOUS_MODE=false
IGNORE_QUIET_HOURS=true
DESIGNER_USE_NEMOTRON_HTML=false
```

The dashboard needs browser-safe Supabase variables in `dashboard/.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
```

`NEXT_PUBLIC_*` is used for read-only dashboard data. `SUPABASE_SERVICE_KEY` is used by server routes such as the inbound email webhook.

## Setup

Install Python dependencies from the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r agents/requirements.txt
```

Install dashboard dependencies:

```bash
cd dashboard
npm install
```

Apply the Supabase schema by running [agents/scripts/setup_supabase.sql](agents/scripts/setup_supabase.sql) in the Supabase SQL editor. Ensure Realtime is enabled for the tables listed in that file.

For screenshot-based Designer critique, install the Chromium browser used by Playwright:

```bash
python -m playwright install chromium
```

Run the preflight checker before starting a demo run:

```bash
python -m agents.scripts.preflight_check
```

Use `--skip-live` when you only want local Python/package/env diagnostics and do not want to query Supabase:

```bash
python -m agents.scripts.preflight_check --skip-live
```

## Running Locally

Run one claw heartbeat at a time:

```bash
python -m agents.scout.claw --once
python -m agents.designer.claw --once
python -m agents.pitcher.claw --once
python -m agents.closer.claw --once
```

Run all claws continuously:

```bash
agents/scripts/start_all_claws.sh
```

Stop all claws:

```bash
agents/scripts/stop_all_claws.sh
```

Run the Discord approval worker:

```bash
python -m workers.discord_bridge
```

Seed demo fallback data:

```bash
python -m agents.scripts.seed_demo_data
```

Use `--clear` to remove existing demo-prefixed rows before reseeding:

```bash
python -m agents.scripts.seed_demo_data --clear
```

Run the dashboard:

```bash
cd dashboard
npm run dev
```

Then open the local Next.js URL printed by the command, usually `http://localhost:3000`.

## Validation

Python validation:

```bash
python -m agents.scripts.preflight_check
python -m compileall agents integrations workers
python -m agents.scout.claw --once
python -m agents.designer.claw --once
python -m agents.pitcher.claw --once
python -m agents.closer.claw --once
```

Dashboard validation:

```bash
cd dashboard
npm run typecheck
npm run build
```

The latest known validation results are tracked in [docs/PROGRESS.md](docs/PROGRESS.md). Some live checks currently skip or fail clearly when local credentials and Python packages are missing.

## Operational Notes

- Keep the build scoped to the execution spec. No auth, billing, settings pages, queue systems, or production-scale abstractions.
- Use NemoClaw/Nemotron language for the product story. Only mention OpenClaw for compatibility inside NemoClaw/OpenShell.
- Treat Supabase as the queue. Each claw claims one unit of work per heartbeat and writes results back to the database.
- Keep every claw action visible through the `actions.human_readable_log` field. The dashboard depends on those logs for the live narrative.
- `AUTONOMOUS_MODE=true` is useful for unattended demo runs. Keep it `false` when you want Discord approval in the loop.
- `IGNORE_QUIET_HOURS=true` is currently configured for hackathon/demo usage.

## Known Gaps

- NemoClaw install/onboarding is still documented as expected flow, not verified final commands.
- The rate-limit check script is still a placeholder.
- Domain, Resend DNS, Supabase cloud project, Vercel, Discord, and Google Calendar setup remain manual blockers.
- `dashboard/app/api/discord-reply` and `dashboard/app/api/trigger-demo` are placeholders.
- Vapi voice handling is stretch scope.
- Local `docker-compose.yml` is a placeholder; production/demo persistence is expected to use Supabase cloud.

## Hackathon Guardrails

This repo is optimized for demo reliability, not perfect architecture. Keep diffs small, validate after each task, and update [docs/PROGRESS.md](docs/PROGRESS.md) whenever the project state changes.
