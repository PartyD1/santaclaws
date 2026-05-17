# Santa Claws

AI agents that turn local business leads into live website mockups and personalized outreach.

Santa Claws is a hackathon project built around a simple idea: a small team of autonomous agents should be able to find local businesses, build polished website mockups for them, draft outreach, and show every step in a live dashboard.

The project uses NemoClaw as the runtime story, Nemotron for reasoning, Supabase for persistent shared memory, and a Next.js dashboard for the demo surface.

## Demo Story

> NemoClaw gives us secure always-on claws. Supabase gives them shared memory. Nemotron gives them reasoning.

Santa Claws is not one giant script. It is a small agent team with clear roles:

| Claw | Role | What it does |
| --- | --- | --- |
| Rudolph Scout | Lead finder | Finds local businesses, enriches rows, and qualifies email-ready leads. |
| Workshop Elves | Designer | Builds professional website mockups and deploys the winner to Vercel. |
| Snowball Pitcher | Outreach | Writes personalized emails and inserts the exact Vercel mockup link. |
| Cookie Closer | Follow-up | Handles inbound email replies, drafts responses, and moves warm leads toward meetings. |

The dashboard shows the live pipeline, logs, generated sites, outreach, replies, and persistent memory.

## How It Works

```text
Lead discovery
  -> website mockup
  -> personalized pitch
  -> approval or autonomous send
  -> reply handling
  -> meeting workflow
```

The agents communicate through Supabase, not direct calls. Supabase acts as:

- a work queue
- persistent memory
- an audit log
- the dashboard data source

Each heartbeat claims one unit of work, updates the database, and writes a human-readable action log.

## Architecture

```text
NemoClaw / OpenShell-compatible runtime
  |
  |-- Rudolph Scout
  |-- Workshop Elves
  |-- Snowball Pitcher
  `-- Cookie Closer
        |
        v
Python tool layer
  |
  |-- Apify for lead discovery
  |-- Nemotron for reasoning and generation
  |-- Vercel for mockup deployment
  |-- Resend or SMTP for email
  |-- Discord for approvals and controls
  |-- Google Calendar path for meetings
  `-- Supabase for memory, queues, and logs
        |
        v
Next.js dashboard
```

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| Agents | Python |
| Runtime story | NemoClaw with OpenClaw-compatible agent files |
| Model | Nemotron 3 Nano Omni 30B reasoning |
| Database and memory | Supabase Postgres |
| Lead discovery | Apify Google Places actor |
| Mockup hosting | Vercel |
| Email | Resend or SMTP |
| Controls | Discord bot |
| Demo compute | Brev Ubuntu instance |

## Repository Tour

```text
.
|-- agents/        Python claws, tools, prompts, integrations, and scripts
|-- dashboard/     Next.js dashboard and API routes
|-- docs/          Execution spec, runbooks, progress log, and fallback notes
|-- nemoclaw/      NemoClaw and OpenShell setup notes
|-- workers/       Discord and webhook workers
|-- SETUP.md       Team command reference for Brev and the demo
`-- README.md      Project overview
```

Useful docs:

- [Team setup commands](SETUP.md)
- [Execution spec](docs/Mainstreet_NemoClaw_Codex_Execution_Spec.md)
- [Progress log](docs/PROGRESS.md)
- [Demo runbook](docs/DEMO_RUNBOOK.md)
- [Dashboard notes](dashboard/README.md)

## Core Database Tables

| Table | Purpose |
| --- | --- |
| `leads` | Businesses found by Scout and moved through the pipeline. |
| `generated_sites` | Designer mockups, winner metadata, and Vercel URLs. |
| `outreach` | Pitcher drafts, approvals, send status, and email bodies. |
| `actions` | Human-readable agent activity logs for the dashboard. |
| `approvals` | Discord or fallback approval decisions. |
| `inbound` | Inbound email replies for Closer. |
| `meetings` | Booked or demo-fallback meetings. |
| `agent_memory` | Durable agent memory patterns. |

## Quick Start

Clone and enter the repo:

```bash
git clone https://github.com/PartyD1/santaclaws.git mainstreet
cd mainstreet
```

Create the Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r agents/requirements.txt
```

Create the root environment file:

```bash
cp .env.example .env
nano .env
```

Install dashboard dependencies:

```bash
cd dashboard
npm install
```

Apply the Supabase schema from:

```text
agents/scripts/setup_supabase.sql
```

Run it in the Supabase SQL editor.

## Environment

The Python agents read from the root `.env`.

Common variables:

```bash
NEMOTRON_BASE_URL=https://inference.local/v1
NEMOTRON_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
NVIDIA_API_KEY=

SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

APIFY_TOKEN=
VERCEL_TOKEN=
VERCEL_TEAM_ID=
VERCEL_PROJECT_ID=
VERCEL_PROJECT_NAME=santa-claws

RESEND_API_KEY=
OUTREACH_FROM_ADDRESS=
EMAIL_PROVIDER=resend

DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
DISCORD_APPROVAL_CHANNEL_ID=

AUTONOMOUS_MODE=false
SCOUT_DEMO_FALLBACK=true
SCOUT_TEST_EMAIL=
```

The dashboard uses `dashboard/.env.local`:

```bash
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
```

## Run The Pipeline

From the repo root:

```bash
source .venv/bin/activate
```

Run one heartbeat at a time:

```bash
python -m agents.scripts.openclaw_run scout --once
python -m agents.scripts.openclaw_run designer --once
python -m agents.scripts.openclaw_run pitcher --once
python -m agents.scripts.openclaw_run closer --once
```

Run every claw once:

```bash
python -m agents.scripts.openclaw_run all --once
```

Run the Discord bot:

```bash
python -m workers.discord_bridge
```

Discord commands:

```text
HELP
RUN SCOUT
RUN DESIGNER
RUN PITCHER
RUN CLOSER
RUN ALL
APPROVE <outreach_id>
SKIP <outreach_id>
EDIT <outreach_id> <new body>
```

Run the dashboard:

```bash
cd dashboard
npm run dev
```

The dashboard runs at:

```text
http://localhost:3002
```

## Brev Demo Flow

```bash
brev shell santaclaws1
cd ~/mainstreet
git pull
source .venv/bin/activate
```

Start the dashboard:

```bash
cd ~/mainstreet/dashboard
npm run dev
```

In another Brev shell, run agents:

```bash
cd ~/mainstreet
source .venv/bin/activate
python -m agents.scripts.openclaw_run scout --once
python -m agents.scripts.openclaw_run designer --once
python -m agents.scripts.openclaw_run pitcher --once
```

## Validation

Python:

```bash
python -m compileall agents workers
python -m agents.scripts.preflight_check --skip-live
```

Dashboard:

```bash
cd dashboard
npm run typecheck
npm run build
```

Latest validation notes live in [docs/PROGRESS.md](docs/PROGRESS.md).

## What We Learned

The hardest part of Santa Claws was not making one model call. It was making a multi-agent system reliable enough to demo.

We learned that agentic products need:

- persistent memory
- clear queues
- visible logs
- exact external links
- careful environment loading
- simple human controls

The dashboard became just as important as the agents because it made the autonomous work legible.

## Hackathon Notes

This repo is optimized for demo reliability. It intentionally avoids auth, billing, settings pages, and heavy production abstractions. The goal is to show a working autonomous workflow with persistent memory, real generated sites, and visible agent behavior.

For teammate commands, use [SETUP.md](SETUP.md).
