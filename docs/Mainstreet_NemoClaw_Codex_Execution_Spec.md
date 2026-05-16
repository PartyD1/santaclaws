
# Mainstreet — Codex Execution Spec

**A four-agent autonomous sales team built on NemoClaw + Nemotron 3 Super 120B, designed to ship in 24 hours.**

This document is the single source of truth for implementation. Codex should
execute Section 10 tasks in order. Sections 1–9 and 11–12 are reference for
when Codex needs context.

**Stack lock:** Python 3.11 for agents, tools, integrations. TypeScript +
Next.js 14 (App Router) for dashboard only. PostgreSQL via Supabase. No
auth on dashboard. Discord via webhook bridge.

**Runtime lock:** NemoClaw is the sandbox/runtime layer. It runs the claws in an OpenShell-managed, OpenClaw-compatible environment, routes inference to Nemotron, and provides the security/privacy story for the judges. The Python tools still live in this repo; they run from inside the NemoClaw sandbox.

**Demo target:** auto repair shops in Santa Cruz County. Live dashboard
showing 4 claws working in parallel, real generated mockup sites, real
email drafts queued for approval, real meetings booked on Google Calendar.

---

## SECTION 1 — SYSTEM ARCHITECTURE

### Overall shape

```
┌──────────────────────────────────────────────────────────────┐
│              NemoClaw Runtime / OpenShell Sandbox              │
│  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Scout   │  │  Designer  │  │ Pitcher  │  │  Closer  │   │
│  │  Claw    │  │   Claw     │  │  Claw    │  │  Claw    │   │
│  └────┬─────┘  └─────┬──────┘  └────┬─────┘  └────┬─────┘   │
│       │              │              │              │         │
│       └──────────────┴──────────────┴──────────────┘         │
│                            │                                  │
│              ┌─────────────┴──────────────┐                  │
│              │   Tool Layer (Python)       │                  │
│              │  apify, resend, vercel,     │                  │
│              │  vapi, gcal, supabase, etc  │                  │
│              └─────────────┬──────────────┘                  │
└────────────────────────────┼──────────────────────────────────┘
                             │
              ┌──────────────┴───────────────┐
              │       Supabase Postgres       │
              │  leads, actions, outreach,    │
              │  generated_sites, inbound,    │
              │  meetings, approvals          │
              └──────────────┬───────────────┘
                             │ Realtime
                             ▼
              ┌──────────────────────────────┐
              │   Next.js Dashboard (Vercel)  │
              │   reads via Supabase client   │
              └──────────────────────────────┘
                             ▲
                             │
              ┌──────────────┴───────────────┐
              │  Discord Webhook Bridge       │
              │  approval channel + alerts    │
              └──────────────────────────────┘
```

### NemoClaw-specific runtime notes

- NemoClaw is the outer runtime and demo story. It provides the OpenShell sandbox, policy controls, and managed inference route.
- The claws still use SOUL.md, AGENTS.md, TOOLS.md, HEARTBEAT.md, and MEMORY.md files because the workspace remains OpenClaw-compatible inside NemoClaw.
- In the demo, describe this as: **NemoClaw gives us secure always-on claws; Supabase gives them shared memory; Nemotron gives them reasoning.**
- All external API access from the sandbox should be explicitly allowed in the NemoClaw/OpenShell network policy: Supabase, Apify, Vercel, Resend, Discord, Google Calendar, and Vapi if enabled.
- For local development outside the sandbox, direct NVIDIA API calls are acceptable. For the real demo, prefer the NemoClaw/OpenShell inference route.

### Data flow (the happy path for one lead)

1. **Scout heartbeat (60s):** queries Apify for new businesses → writes to
   `leads` table with `qualification_status = 'pending'`
2. **Scout enrichment:** for each lead, calls `score_website` and
   `extract_pain_points` → updates `leads`, sets
   `qualification_status = 'qualified_for_mockup' | 'qualified_for_rebuild' |
   'skip'`
3. **Designer heartbeat (60s):** picks oldest lead with
   `qualification_status IN ('qualified_for_mockup', 'qualified_for_rebuild')`
   AND `worked_by_designer = false` → generates 3 variants → self-critiques
   → deploys to Vercel → writes to `generated_sites` → marks lead
4. **Pitcher heartbeat (60s):** picks oldest lead with
   `worked_by_designer = true AND worked_by_pitcher = false` → generates 4
   email variants → self-critiques → writes winner to `outreach` with
   `status = 'pending_approval'` → posts to Discord
5. **Human approves in Discord** (or `AUTONOMOUS_MODE=true` auto-approves) →
   bridge writes `approvals` row → Pitcher's next heartbeat sees it and calls
   `send_email`
6. **Reply arrives at inbound webhook** → writes to `inbound` table with
   `handled_at = NULL`
7. **Closer heartbeat (30s):** picks unhandled inbound → classifies → for
   "interested", calls `propose_meeting_times` → drafts reply → posts to
   Discord for approval → on approve, sends + books calendar event →
   writes to `meetings`

### Async workflow design

**No queue system.** No Celery, no Redis, no Temporal. The database IS the
queue. Each agent's heartbeat does:

```python
1. SELECT * FROM <table> WHERE <work_predicate> ORDER BY created_at LIMIT 1
2. UPDATE that row with a "claimed" marker (worked_by_X = true) inside a transaction
3. Do the work
4. Write results back
5. Log to actions table
6. End heartbeat
```

This is naive but it works for a hackathon with low concurrency. The
"claimed" flag prevents the same agent from picking up the same lead twice
across overlapping heartbeats. The work itself is idempotent enough that
even race conditions are recoverable.

### Heartbeat model

NemoClaw-managed, OpenClaw-compatible HEARTBEAT.md defines the heartbeat schedule per claw. We use:

- Scout: every 60 seconds
- Designer: every 60 seconds
- Pitcher: every 60 seconds
- Closer: every 30 seconds (inbound is time-sensitive)

Each heartbeat picks ONE lead and does its full workflow on it. We don't
batch within a heartbeat. This means one lead = one heartbeat cycle. With
500 leads in the DB, the queue drains in ~8 hours. That's fine for the
overnight demo run.

### How agents communicate

**Only through Supabase tables.** No direct agent-to-agent calls. No shared
in-memory state. No message bus. If Scout wants to tell Designer something,
it writes to `leads`. If Pitcher wants Closer to know the email body, it's
already in `outreach`.

This is enforceable: each agent only has DB access to specific tables (via
Supabase RLS or just by convention since we have no auth).

### Shared memory

- **Structured memory:** Supabase tables (leads, actions, outreach, etc.)
- **Unstructured per-agent memory:** `MEMORY.md` per agent — agent updates
  it at end of heartbeat if it noticed a pattern. Read at start of next
  heartbeat.

Memory budget: keep MEMORY.md under 200 lines per agent. If it grows beyond,
agent prunes by deleting older entries.

### Logs/events

Every meaningful agent action writes a row to `actions`:

- `claw_name` (string)
- `lead_id` (nullable)
- `action_type` (string, e.g., "scrape_batch", "score_website",
  "generate_variant", "send_email")
- `status` ("started" | "succeeded" | "failed" | "skipped")
- `started_at`, `finished_at`
- `result_json` (jsonb — flexible payload)
- `human_readable_log` (string — one sentence, narrative tone, for dashboard)

The `human_readable_log` field is the most important. It's what shows up on
the demo dashboard. Examples:

> "🔍 Scout scraped Joe's Auto Body. Score: 2/10 (no SSL, mobile-broken). Qualified for mockup."
> "🎨 Designer built 3 variants for Joe's. Retro-local won (8.4/10) — matches their 'since 1987' reviews."
> "✉️ Pitcher drafted 4 angles for Joe's. Specific-pain won (8.7/10). Queued for approval."

### Minimal viable architecture

If we're behind at H+12, the minimum that still tells the story:
- Scout + Designer + Pitcher only (Closer cut)
- Email queued for approval, but approval is a button in the dashboard, not
  Discord (Discord bridge cut)
- One mockup variant, no self-critique (cut the loops)
- Dashboard shows the leads table + action log only

This is still a working autonomous pipeline and a credible demo.

### What to fake/mock if behind

- **Closer inbound replies:** seed `inbound` table with 3 pre-written
  replies at start of demo. Demo "watch closer handle this reply" by
  clicking a button that inserts a row.
- **Vapi voice:** record a 30s screencap of a working call from earlier in
  the day, play during demo if live fails. Better: have a teammate phone
  the number from offstage.
- **Vercel deploys:** if Vercel API is flaky, write HTML directly to
  Supabase Storage public bucket — same effect, public URL.
- **Google Calendar:** if OAuth is broken, write to a fake `meetings` table
  and show on dashboard. Don't actually book.

---

## SECTION 2 — REPO STRUCTURE

Monorepo. One repo, two main folders, shared types crossing the language
boundary via codegen (or duplicated by hand if codegen is slow).

```
mainstreet/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml          # supabase local (optional, prod uses cloud)
│
├── nemoclaw/                   # NemoClaw/OpenShell setup notes and demo policy
│   ├── README.md
│   ├── install_and_onboard.sh
│   ├── network-policy.md       # allowed egress domains for sandbox
│   └── model-routing.md        # Nemotron route / provider notes
│
├── agents/                     # Python — NemoClaw claws inside the OpenShell sandbox
│   ├── pyproject.toml
│   ├── requirements.txt
│   ├── shared/
│   │   ├── SHARED_VALUES.md
│   │   ├── supabase_client.py  # singleton supabase client
│   │   ├── nemotron_client.py  # OpenAI-compatible wrapper
│   │   ├── logger.py           # writes to actions table
│   │   ├── discord_bridge.py   # webhook poster
│   │   └── types.py            # python dataclasses mirroring DB schema
│   │
│   ├── scout/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── TOOLS.md
│   │   ├── HEARTBEAT.md
│   │   ├── MEMORY.md           # starts empty, agent appends
│   │   ├── claw.py             # heartbeat entrypoint
│   │   └── tools/
│   │       ├── scrape_leads.py
│   │       ├── score_website.py
│   │       └── extract_pain_points.py
│   │
│   ├── designer/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── TOOLS.md
│   │   ├── HEARTBEAT.md
│   │   ├── MEMORY.md
│   │   ├── claw.py
│   │   └── tools/
│   │       ├── generate_mockup.py
│   │       ├── critique_mockup.py
│   │       ├── screenshot_html.py
│   │       ├── deploy_to_vercel.py
│   │       └── pick_winner.py
│   │
│   ├── pitcher/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── TOOLS.md
│   │   ├── HEARTBEAT.md
│   │   ├── MEMORY.md
│   │   ├── claw.py
│   │   └── tools/
│   │       ├── generate_email.py
│   │       ├── critique_email.py
│   │       └── send_email.py
│   │
│   ├── closer/
│   │   ├── SOUL.md
│   │   ├── AGENTS.md
│   │   ├── TOOLS.md
│   │   ├── HEARTBEAT.md
│   │   ├── MEMORY.md
│   │   ├── claw.py
│   │   └── tools/
│   │       ├── classify_reply.py
│   │       ├── propose_meeting_times.py
│   │       ├── book_meeting.py
│   │       ├── draft_reply.py
│   │       └── handle_vapi_call.py    # stretch goal
│   │
│   ├── prompts/                # standalone prompt strings, importable
│   │   ├── scout_extract_pain.txt
│   │   ├── designer_generate.txt
│   │   ├── designer_critique.txt
│   │   ├── designer_pick_winner.txt
│   │   ├── pitcher_generate_pain.txt
│   │   ├── pitcher_generate_compare.txt
│   │   ├── pitcher_generate_social.txt
│   │   ├── pitcher_generate_curiosity.txt
│   │   ├── pitcher_critique.txt
│   │   └── closer_classify.txt
│   │
│   ├── scripts/
│   │   ├── rate_limit_check.py        # Codex Task #1
│   │   ├── seed_demo_data.py          # populate fake inbound replies
│   │   ├── setup_supabase.sql         # full schema
│   │   ├── start_all_claws.sh         # boot all 4 in parallel
│   │   └── nuke_db.py                 # dev only
│   │
│   └── nemoclaw.json           # NemoClaw/OpenShell sandbox + routing notes
│
├── dashboard/                  # Next.js 14 App Router
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── .env.local.example
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # main dashboard
│   │   ├── leads/[id]/page.tsx        # lead detail
│   │   └── api/
│   │       ├── inbound-email/route.ts # Resend webhook
│   │       ├── discord-reply/route.ts # Discord bot webhook
│   │       └── trigger-demo/route.ts  # demo button
│   ├── components/
│   │   ├── ClawCard.tsx
│   │   ├── ActivityFeed.tsx
│   │   ├── MetricsBar.tsx
│   │   ├── LeadsTable.tsx
│   │   ├── LeadDetail.tsx
│   │   └── MockupPreview.tsx
│   ├── lib/
│   │   ├── supabase.ts                # browser client
│   │   ├── supabase-server.ts         # server client
│   │   ├── types.ts                   # mirrors agents/shared/types.py
│   │   └── realtime.ts                # subscription helpers
│   └── public/
│
├── integrations/               # Python — third-party API clients
│   ├── apify_client.py
│   ├── resend_client.py
│   ├── vercel_client.py
│   ├── vapi_client.py
│   ├── gcal_client.py
│   └── supabase_storage_client.py     # fallback for vercel
│
└── workers/                    # standalone background processes
    ├── discord_bridge.py       # listens on Discord, writes to approvals
    └── inbound_email_worker.py # cleans up inbound emails from Resend
```

**Why this shape:** clear boundaries (`agents/` is Python NemoClaw claws running inside the OpenShell sandbox,
`dashboard/` is TypeScript Next.js, `integrations/` is reusable Python
clients, `workers/` is standalone Python processes). No cross-imports
between dashboard and agents — they communicate only through the database.

---

## SECTION 3 — DATABASE DESIGN

### Tables

```sql
-- ==========================================
-- LEADS
-- ==========================================
create table leads (
  id uuid primary key default gen_random_uuid(),
  business_name text not null,
  address text,
  phone text,
  email text,
  website text,
  niche text not null,
  city text not null,
  google_rating numeric,
  review_count int default 0,
  review_texts text[],
  top_review_pain_points text[],
  website_score int,                  -- 0-10
  website_score_reasons text[],
  qualification_status text not null default 'pending',
    -- pending | qualified_for_mockup | qualified_for_rebuild
    -- | qualified_for_receptionist | skip
  qualification_reason text,
  worked_by_designer boolean default false,
  worked_by_pitcher boolean default false,
  do_not_contact boolean default false,
  scraped_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index idx_leads_qual_status on leads(qualification_status);
create index idx_leads_designer_queue on leads(qualification_status,
  worked_by_designer) where worked_by_designer = false;
create index idx_leads_pitcher_queue on leads(worked_by_designer,
  worked_by_pitcher) where worked_by_designer = true
  and worked_by_pitcher = false;
create index idx_leads_dedup on leads(business_name, address);

-- ==========================================
-- ACTIONS (audit log + dashboard feed)
-- ==========================================
create table actions (
  id uuid primary key default gen_random_uuid(),
  claw_name text not null,            -- scout | designer | pitcher | closer
  lead_id uuid references leads(id),
  action_type text not null,
  status text not null,               -- started | succeeded | failed | skipped
  started_at timestamptz default now(),
  finished_at timestamptz,
  result_json jsonb,
  human_readable_log text not null
);

create index idx_actions_recent on actions(started_at desc);
create index idx_actions_lead on actions(lead_id);
create index idx_actions_claw on actions(claw_name, started_at desc);

-- ==========================================
-- GENERATED_SITES
-- ==========================================
create table generated_sites (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) not null,
  variant text not null,              -- clean_modern | retro_local | premium
  vercel_url text,
  storage_url text,                   -- fallback if vercel fails
  html_content text not null,
  self_critique_score numeric,
  self_critique_iterations int default 1,
  critique_issues text[],
  is_chosen_winner boolean default false,
  pick_reasoning text,
  generated_at timestamptz default now()
);

create index idx_generated_sites_lead on generated_sites(lead_id);
create index idx_generated_sites_winner on generated_sites(lead_id)
  where is_chosen_winner = true;

-- ==========================================
-- OUTREACH
-- ==========================================
create table outreach (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) not null,
  to_address text,
  angle text not null,
    -- specific_pain | competitor_comparison | social_proof | curiosity
  subject text not null,
  body text not null,
  critique_score numeric,
  runner_up_variants jsonb,           -- {angle: {subject, body, score}}
  status text not null default 'pending_approval',
    -- pending_approval | approved | sent | skipped | failed
  drafted_at timestamptz default now(),
  approved_at timestamptz,
  sent_at timestamptz,
  resend_message_id text
);

create index idx_outreach_status on outreach(status);
create index idx_outreach_lead on outreach(lead_id);

-- ==========================================
-- INBOUND (replies + voice calls)
-- ==========================================
create table inbound (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id),
  channel text not null,              -- email | voice
  raw_content text not null,
  transcript text,                    -- voice only
  from_address text,                  -- email or phone
  classification text,
    -- interested | not_interested | has_question | has_objection
    -- | spam | uncertain
  classification_confidence int,
  classification_key_phrase text,
  received_at timestamptz default now(),
  handled_at timestamptz,
  handled_by text                     -- closer | human
);

create index idx_inbound_unhandled on inbound(received_at)
  where handled_at is null;
create index idx_inbound_lead on inbound(lead_id);

-- ==========================================
-- MEETINGS
-- ==========================================
create table meetings (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) not null,
  inbound_id uuid references inbound(id),
  scheduled_for timestamptz not null,
  google_event_id text,
  status text not null default 'booked',
    -- booked | completed | cancelled
  attendee_email text,
  booked_at timestamptz default now()
);

create index idx_meetings_lead on meetings(lead_id);
create index idx_meetings_scheduled on meetings(scheduled_for);

-- ==========================================
-- APPROVALS (humans deciding via Discord)
-- ==========================================
create table approvals (
  id uuid primary key default gen_random_uuid(),
  target_type text not null,          -- outreach | inbound_reply
  target_id uuid not null,
  decision text,                      -- approve | edit | skip | escalate
  edit_payload jsonb,                 -- {subject, body} if EDIT
  requested_at timestamptz default now(),
  decided_at timestamptz,
  decided_by text                     -- discord username
);

create index idx_approvals_pending on approvals(target_type, target_id)
  where decided_at is null;

-- ==========================================
-- CONFIG (runtime config for agents)
-- ==========================================
create table config (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz default now()
);

-- Seed values
insert into config (key, value) values
  ('target', '{"niche": "auto repair", "city": "Santa Cruz", "state": "CA"}'),
  ('autonomous_mode', 'false'),
  ('ignore_quiet_hours', 'true'),
  ('session_lead_cap', '500');

-- ==========================================
-- REALTIME
-- ==========================================
alter publication supabase_realtime add table leads;
alter publication supabase_realtime add table actions;
alter publication supabase_realtime add table generated_sites;
alter publication supabase_realtime add table outreach;
alter publication supabase_realtime add table inbound;
alter publication supabase_realtime add table meetings;
alter publication supabase_realtime add table approvals;
```

### Python types (agents/shared/types.py)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

QualStatus = Literal[
    "pending", "qualified_for_mockup", "qualified_for_rebuild",
    "qualified_for_receptionist", "skip"
]
ClawName = Literal["scout", "designer", "pitcher", "closer"]
ActionStatus = Literal["started", "succeeded", "failed", "skipped"]
Variant = Literal["clean_modern", "retro_local", "premium"]
Angle = Literal["specific_pain", "competitor_comparison",
                "social_proof", "curiosity"]
OutreachStatus = Literal["pending_approval", "approved", "sent",
                         "skipped", "failed"]
Classification = Literal["interested", "not_interested", "has_question",
                         "has_objection", "spam", "uncertain"]

@dataclass
class Lead:
    id: UUID
    business_name: str
    niche: str
    city: str
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    website: Optional[str]
    google_rating: Optional[float]
    review_count: int
    review_texts: list[str]
    top_review_pain_points: list[str]
    website_score: Optional[int]
    qualification_status: QualStatus
    worked_by_designer: bool
    worked_by_pitcher: bool
    do_not_contact: bool

# (similar dataclasses for Action, GeneratedSite, Outreach, Inbound, Meeting, Approval)
```

### TS types (dashboard/lib/types.ts) — mirror manually

Mirror the Python types as TS interfaces. Keep in sync by hand. There are
only ~7 types; codegen overhead isn't worth it for 24 hours.

### Important queries

```sql
-- Scout's queue check (find recent dedup count)
select count(*) from leads
where niche = $1 and city = $2 and scraped_at > now() - interval '1 hour';

-- Designer's next lead
select * from leads
where qualification_status in ('qualified_for_mockup', 'qualified_for_rebuild')
  and worked_by_designer = false
order by scraped_at asc
limit 1;

-- Pitcher's next lead
select l.*, gs.vercel_url, gs.storage_url
from leads l
left join generated_sites gs on gs.lead_id = l.id and gs.is_chosen_winner = true
where l.worked_by_designer = true and l.worked_by_pitcher = false
order by l.scraped_at asc
limit 1;

-- Closer's next inbound
select i.*, l.business_name from inbound i
left join leads l on l.id = i.lead_id
where i.handled_at is null
order by i.received_at asc
limit 1;

-- Dashboard activity feed (latest 50)
select * from actions order by started_at desc limit 50;

-- Dashboard metrics
select
  (select count(*) from leads) as total_leads,
  (select count(*) from leads where qualification_status != 'skip' and qualification_status != 'pending') as qualified,
  (select count(*) from generated_sites) as sites_generated,
  (select count(*) from outreach where status = 'sent') as sent,
  (select count(*) from inbound) as replies,
  (select count(*) from meetings) as meetings_booked;
```

---

## SECTION 4 — AGENT DESIGN

For each agent: MVP minimum, stretch additions, the exact contract.

### Scout Claw

**Responsibilities:** find businesses, score them, classify them, write to DB.

**Inputs:**
- `config.target` from Supabase (niche, city, state)
- `MEMORY.md` (read-only at start, append at end)

**Outputs:**
- Rows in `leads` with full qualification populated
- Rows in `actions`
- Optionally: Discord message proposing niche/city expansion

**Heartbeat (60s):**
```
1. Read MEMORY.md, parse patterns
2. Read config.target
3. Call scrape_leads(city, niche, limit=20)
4. For each new lead (dedup'd against existing rows):
   - score_website(url) or set score=0 if no URL
   - extract_pain_points(lead.id)
   - apply qualification rubric
   - update leads row
   - log action
5. If recent scrapes hit 90%+ dedup, post expansion proposal
6. Append MEMORY.md if pattern noticed
7. Post heartbeat summary
```

**Tool access:** apify, supabase (read+write leads/actions/config), discord webhook

**Failure handling:**
- Apify timeout → retry once → skip batch, log error
- score_website timeout → treat as score 0 with reason "site unreachable"
- 3 consecutive batch failures → halt, post to Discord, wait

**Rate limiting:**
- Max 20 leads per heartbeat
- Apify: 1 call per heartbeat (Apify itself rate-limits internally)
- Nemotron (extract_pain_points): 20 calls per heartbeat max

**State machine:** stateless. Every heartbeat is independent.

**MVP:** scrape + score (no pain point extraction). Pain points become
mockup/email inputs but Designer/Pitcher can fall back to generic reasoning.

**Stretch:** review-keyword clustering across leads to identify niche-wide
themes ("everyone complains about parking").

---

### Designer Claw

**Responsibilities:** generate 3 mockup variants, self-critique, deploy,
pick winner.

**Inputs:**
- Lead row from `leads`
- `MEMORY.md` (patterns about what wins)

**Outputs:**
- 3 rows in `generated_sites`, one with `is_chosen_winner = true`
- Lead updated: `worked_by_designer = true`

**Heartbeat (60s):**
```
1. Read MEMORY.md
2. SELECT next lead (designer queue)
3. UPDATE worked_by_designer = true (claim it now to prevent re-pickup
   even if generation fails halfway)
4. Build business brief from lead row
5. For each variant in [clean_modern, retro_local, premium]:
   a. Generate HTML (Nemotron)
   b. Screenshot via Playwright
   c. Critique (Nemotron, vision)
   d. If score < 8 and iterations < 5: regenerate with critique
   e. Deploy to Vercel (or Supabase Storage fallback)
   f. Insert into generated_sites
6. Call pick_winner(lead_id) — Nemotron picks based on business vibe
7. UPDATE chosen variant's is_chosen_winner = true
8. Log actions, append MEMORY.md
```

**Tool access:** nemotron (vision-capable), playwright, vercel, supabase storage, supabase

**Failure handling:**
- Nemotron returns invalid HTML → retry once → use last valid HTML if any,
  else mark variant failed
- Playwright fails → assume score 5, ship the variant unscored
- Vercel deploy fails → fallback to Supabase Storage public bucket
- All 3 variants fail → mark `worked_by_designer = true`, log failure, move on

**Rate limiting:**
- Max 3 variants × 5 iterations × 1 generation = 15 Nemotron calls per lead worst case
- Plus 15 critique calls = 30 total per lead
- At 60s heartbeat, that's ~30 RPM peak. Watch the rate limit.

**State machine:** stateless per lead. Within a lead: 3 parallel variant tracks.

**MVP:** 1 variant per lead, 1 critique pass, no iteration. Picks itself as
winner automatically. Cuts Nemotron load by 30x.

**Stretch:** image generation for hero photos (Nemotron Omni or DALL-E
fallback). Custom domains per mockup.

---

### Pitcher Claw

**Responsibilities:** draft 4 email angles, critique, pick winner, queue for
approval, send on approval.

**Inputs:**
- Lead with mockup ready
- Winning mockup URL
- `MEMORY.md`

**Outputs:**
- Row in `outreach`
- Discord post in approval channel
- On approval: actual email sent via Resend

**Heartbeat (60s):**
```
1. Read MEMORY.md
2. SELECT next lead (pitcher queue)
3. UPDATE worked_by_pitcher = true (claim)
4. Pull lead + winning mockup URL
5. Generate 4 emails in parallel (4 angles)
6. Critique each (Nemotron)
7. Pick winner (highest score, tiebreak via MEMORY)
8. INSERT outreach row with status='pending_approval' (or 'approved'
   if AUTONOMOUS_MODE)
9. Post to Discord approval channel
10. ALSO: check for any outreach rows with status='approved' AND
    sent_at IS NULL → send those via Resend
11. Log, append MEMORY
```

**Tool access:** nemotron, resend, supabase, discord webhook

**Failure handling:**
- Nemotron returns malformed JSON → retry once → use the angle's prompt
  output verbatim as body, generic subject
- Resend fails → retry once after 30s → mark outreach status='failed',
  Discord alert

**Rate limiting:**
- 4 generate + 4 critique = 8 Nemotron calls per lead
- Per heartbeat ~8 RPM steady state. Fine.

**State machine:** stateless per lead.

**MVP:** 1 angle (specific_pain), no critique, auto-approve. Still demos as
"agent personalized this email" because it pulls real business data.

**Stretch:** A/B testing across angles based on reply rates over time.

---

### Closer Claw

**Responsibilities:** handle inbound email replies, classify, draft
responses, book meetings.

**Inputs:**
- New rows in `inbound`
- `MEMORY.md`

**Outputs:**
- Updates to `inbound` (classification, handled_at)
- Drafted replies (queued for approval)
- Booked meetings in `meetings` table
- Calendar events via gcal

**Heartbeat (30s):**
```
1. SELECT unhandled inbound
2. Classify via Nemotron
3. UPDATE inbound with classification
4. Branch by classification:
   - interested → propose_meeting_times → draft reply with 3 slots
   - has_question → answer using lead data only → soft CTA
   - has_objection → draft response → ALWAYS surface for approval
   - not_interested → auto-send gracious ack, mark do_not_contact=true
   - spam → log, mark handled, skip
   - uncertain → surface to operator
5. Post to Discord (unless auto-handled spam/not_interested)
6. Check for newly-approved replies → send via Resend
7. Check for newly-approved meeting confirmations → book on calendar
```

**Tool access:** nemotron, resend, gcal, vapi (stretch), supabase, discord webhook

**Failure handling:**
- Classification fails → mark "uncertain", surface for human
- gcal OAuth expired → surface for human, ask them to re-auth
- Resend fails → retry once → mark failed, Discord alert

**Rate limiting:** trivial. ~1 Nemotron call per inbound, low volume.

**State machine:** mostly stateless. Voice calls (stretch) have multi-turn
state held by Vapi itself.

**MVP:** email-reply handling only. Calendar booking via gcal. **No Vapi.**

**Stretch:** Vapi inbound number, voice call handling, in-call calendar
booking with verbal confirmation.

---

## SECTION 5 — PROMPT ARCHITECTURE

### Principles

1. **Always return JSON.** Never let the model return prose if the result
   is structured. Use `response_format={"type": "json_object"}` if
   Nemotron supports it; otherwise instruct hard and validate hard.
2. **Few-shot for any classification.** 2-3 examples in the prompt.
3. **Truncate inputs aggressively.** Reviews → top 10. HTML → first 4000 chars
   for critique.
4. **One job per prompt.** No chained reasoning inside a single call. Use
   multiple calls.
5. **Reject invalid output.** If JSON.parse fails, retry once with
   "previous output was invalid JSON, return only the JSON object."

### System prompt convention (every Nemotron call)

```
You are a tool inside the Mainstreet agent system. You return ONLY valid
JSON in the exact schema requested. No prose. No markdown fences. No
explanations outside the JSON. If the input is insufficient to answer,
return JSON with {"error": "<reason>"}.
```

### Memory append convention

At end of heartbeat, agent asks itself (one Nemotron call):

```
You are {claw_name}. You just completed a heartbeat. Below is a summary of
what happened. Identify ONE pattern worth remembering — something specific
that would help you make a better decision next time. Examples of good
patterns: "retro variant wins for businesses with 'classic' in name",
"social_proof angle scores higher than curiosity for businesses with 100+
reviews". If nothing notable happened, return {"pattern": null}.

Heartbeat summary:
{summary}

Existing MEMORY.md (do not duplicate):
{current_memory}

Return JSON: {"pattern": "<one sentence or null>"}
```

If `pattern` is non-null, append to MEMORY.md with timestamp.

### Action logging convention

Every `actions` row has `human_readable_log` populated. Format:

```
{emoji} {claw} {verb} {object}. {key_detail}. {result}.
```

Examples:
- "🔍 Scout scraped Joe's Auto Body. Score 2/10, no SSL. Qualified for mockup."
- "🎨 Designer built 3 variants for Joe's Auto. Retro-local won (8.4/10)."
- "✉️ Pitcher drafted 4 angles for Joe's. Specific-pain won (8.7/10). Queued."
- "📞 Closer classified reply from Joe as 'interested'. Drafting meeting times."

### Designer generate prompt (prompts/designer_generate.txt)

```
Generate a single-file HTML website mockup for the business below.

Business:
- Name: {business_name}
- Type: {niche}
- City: {city}
- Address: {address}
- Phone: {phone}
- Hours: {hours}
- Google rating: {rating} ({review_count} reviews)
- Customer pain points to address: {pain_points}

Design variant: {variant_name}
Variant style guide: {variant_style_block}

REQUIREMENTS:
- Output ONE complete HTML file with Tailwind via CDN
- Mobile-responsive (test mental model: iPhone 12 width)
- One clear above-the-fold CTA: "Call {phone}" as tel: link
- Sections in order: hero, services, about, hours+location, contact
- Use ACTUAL business name and phone, not placeholders
- No lorem ipsum
- No stock-image URLs (use Tailwind background colors/gradients)

{previous_critique_block}

OUTPUT: Only the raw HTML. Start with <!DOCTYPE html>. No markdown fences.
```

Variant style blocks live in `prompts/variants_clean_modern.txt`, etc.

### Designer critique prompt (prompts/designer_critique.txt)

```
You are critiquing a mockup website. The screenshot below shows what the
mockup looks like. The business is {business_name}, a {niche} in {city}.

Score 1-10 from the perspective of the business owner opening this on their
phone. Score 8+ means "ready to send". Score 5-7 means "usable but has
issues". Score 1-4 means "do not send".

Return ONLY this JSON:
{
  "score": <int 1-10>,
  "issues": [<max 5 specific problems>],
  "suggestions": [<max 5 specific fixes>]
}
```

### Pitcher generate (per angle)

```
Write a cold email FROM the Mainstreet team TO {business_name}, a {niche}
in {city}.

Business context:
- Phone: {phone}, Hours: {hours}
- Google rating: {rating} ({review_count} reviews)
- Pain points: {pain_points}
- We built them a mockup: {mockup_url}

Angle: {angle_name}
Angle instructions: {angle_block}

HARD RULES:
- Subject under 50 chars, no emoji, no "Re:" tricks
- Body MAX 5 sentences
- One link only ({mockup_url})
- One ask only
- Banned phrases: "I hope this finds you well", "just following up",
  "circling back", "quick question", "leverage"
- Sign-off: "— Pitcher, working with the Mainstreet team"

Return ONLY JSON: {"subject": "...", "body": "..."}
```

### Closer classify

```
Classify this reply to a cold email. The original pitch offered a free
mockup website to {business_name}.

Reply:
"{raw_content}"

Categories:
- interested
- not_interested
- has_question
- has_objection
- spam
- uncertain (use if confidence < 7)

Return ONLY JSON:
{
  "classification": "<category>",
  "confidence": <1-10>,
  "key_phrase": "<verbatim phrase from reply>",
  "suggested_response_angle": "<one sentence>"
}
```

### Hallucination prevention

- Every prompt that references business data passes it explicitly in the
  prompt. Never let the model "remember" the business.
- For Pitcher: if a critical field (business_name, phone) is missing, the
  tool fails before calling Nemotron.
- For Closer: when answering questions, the prompt ends with "If you don't
  have a fact in the context above, do not invent it. Set classification to
  'uncertain' and key_phrase to 'missing context: <what was missing>'."

---

## SECTION 6 — API + TOOL DESIGN

Every tool follows this pattern (Python):

```python
def tool_name(arg1, arg2, ...) -> dict:
    """One-line description.

    Args:
        arg1: description
        arg2: description
    Returns:
        dict matching tools_TYPENAME_OUTPUT schema
    Raises:
        ToolError on unrecoverable failure (logged + propagated)
    """
    try:
        # implementation
    except SpecificException as e:
        logger.log_action(..., status="failed", error=str(e))
        raise ToolError(...)
```

### Apify (scrape_leads)

```python
# integrations/apify_client.py
APIFY_ACTOR = "compass/crawler-google-places"

def scrape_google_places(
    search_query: str,
    location: str,
    max_results: int = 20,
    include_emails: bool = True,
    only_no_website: bool = False,
) -> list[dict]:
    """
    Returns list of dicts with keys:
      title, address, phoneUnformatted, website, totalScore, reviewsCount,
      categoryName, openingHours, locatedIn, permanentlyClosed, emails
    """
    payload = {
        "searchStringsArray": [search_query],
        "locationQuery": location,
        "maxCrawledPlacesPerSearch": max_results,
        "scrapeContacts": include_emails,
    }
    # POST https://api.apify.com/v2/acts/{APIFY_ACTOR}/run-sync-get-dataset-items
    # Auth: ?token={APIFY_TOKEN}
    # Retry: once on 5xx, after 2s
    # Timeout: 120s
```

### Resend (send_email + inbound webhook)

```python
# integrations/resend_client.py

def send_email(
    to: str, subject: str, html: str,
    from_addr: str = None,  # defaults to OUTREACH_FROM_ADDRESS
    reply_to: str = None,
) -> dict:
    """Returns {'id': resend_message_id}"""
    # POST https://api.resend.com/emails
    # Auth: Bearer {RESEND_API_KEY}
    # Retry: once on 5xx
```

**Inbound webhook** lives in `dashboard/app/api/inbound-email/route.ts`:

```typescript
// POST /api/inbound-email
// Resend posts: { from, to, subject, html, text, headers, ... }
// We:
//   1. Try to match to a lead via the From address (lookup leads.email if we stored it,
//      else lookup outreach.lead_id by matching the From address in our DB)
//   2. INSERT into inbound table with channel='email'
//   3. Closer's heartbeat picks it up on next tick
// Return 200 OK fast.
```

### Vercel (deploy_to_vercel)

```python
# integrations/vercel_client.py

def deploy_html_as_site(html: str, slug: str) -> str:
    """
    Returns public URL on success.
    On failure, falls back to deploy_to_supabase_storage.

    Uses Vercel's Deployments API:
    POST https://api.vercel.com/v13/deployments
    {
      "name": slug,
      "files": [{"file": "index.html", "data": html}],
      "projectSettings": {"framework": null}
    }
    Auth: Bearer {VERCEL_TOKEN}
    Timeout: 60s
    """
```

**Supabase Storage fallback:**

```python
# integrations/supabase_storage_client.py
def upload_html(html: str, path: str) -> str:
    """Returns public URL. Bucket 'mockups' is public-read."""
```

### Vapi (stretch — closer)

```python
# integrations/vapi_client.py
def configure_inbound_assistant() -> str:
    """One-time setup. Returns the public phone number."""
    # POST /assistant with our system prompt + tool definitions
    # POST /phone-number to provision

# Vapi calls our webhook with each turn of the conversation.
# Webhook handler in workers/vapi_webhook.py:
#   - on call start: lookup lead by caller_phone, write to inbound with status='in_progress'
#   - on each tool call: route to closer's in-call tools
#   - on call end: write transcript to inbound.transcript, mark handled
```

### Google Calendar

```python
# integrations/gcal_client.py

def get_free_slots(
    duration_minutes: int = 30,
    days_ahead: int = 5,
    hours_range: tuple[int, int] = (9, 17),
    tz: str = "America/Los_Angeles",
) -> list[datetime]:
    """Returns 3 free slots, spread across different days."""
    # Uses freebusy.query

def create_event(
    title: str, description: str,
    start: datetime, duration_minutes: int,
    attendee_email: str,
) -> str:
    """Returns google_event_id."""
```

**OAuth setup:** one-time, person D runs a script to authorize, saves
refresh token to `.env` as `GCAL_REFRESH_TOKEN`. Code uses that to refresh
access tokens automatically.

### Supabase

```python
# agents/shared/supabase_client.py
from supabase import create_client, Client
sb: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Helpers
def next_designer_lead() -> Optional[Lead]: ...
def next_pitcher_lead() -> Optional[Lead]: ...
def next_inbound() -> Optional[Inbound]: ...
def log_action(claw, action_type, status, log_text, lead_id=None, result=None): ...
def claim_lead_for_designer(lead_id: UUID) -> bool: ...  # returns false if already claimed
def claim_lead_for_pitcher(lead_id: UUID) -> bool: ...
```

### Auth handling

- **Supabase:** SERVICE_KEY for all agent code (no RLS in hackathon mode)
- **Dashboard:** ANON_KEY only (read-only)
- **Apify:** token in env
- **Resend:** API key in env
- **Vercel:** token in env
- **Vapi:** key in env
- **Google Calendar:** OAuth refresh token in env, access token refreshed
  in-memory per process
- **Discord:** webhook URL for outbound, bot token for inbound (stretch)
- **Dashboard:** NO AUTH. It's a demo.

---

## SECTION 7 — DASHBOARD DESIGN

### Layout (single page, no routes except lead detail)

```
┌──────────────────────────────────────────────────────────────┐
│  MAINSTREET                          AUTONOMOUS  [toggle]    │
│  4 claws | Santa Cruz auto repair                            │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │ 🔍 Scout │ │ 🎨 Design│ │ ✉️ Pitch │ │ 📞 Closer│        │
│  │ scraping │ │ building │ │ drafting │ │ idle     │        │
│  │ Watsonvl │ │ Joe's    │ │ for Mike │ │          │        │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │
├──────────────────────────────────────────────────────────────┤
│  METRICS                                                      │
│  412 scraped | 287 qualified | 73 sites | 41 sent | 6 booked │
├──────────────────────────────────────────────────────────────┤
│  ACTIVITY  (live feed, scrolls)         ┃  LEADS              │
│                                          ┃                     │
│  🔍 Scout scraped Joe's Auto Body...     ┃  Joe's Auto    8/10│
│  🎨 Designer built 3 variants for Joe... ┃  Mike's Body   6/10│
│  ✉️ Pitcher queued specific-pain pitch...┃  Bob's Tires   4/10│
│  📞 Closer classified reply as interest..┃  ...               │
│                                          ┃                     │
│                                          ┃  [click for detail]│
└──────────────────────────────────────────────────────────────┘
```

### Lead detail page (`/leads/[id]`)

Shows:
- Lead summary card (business name, score, qualification)
- Mockup variants (3 thumbnails, winner highlighted, click to open URL)
- Outreach status (subject + body of winning email, runner-ups in collapsible)
- Inbound thread (if any replies)
- Meeting status (if booked)
- Full action timeline for this lead

### Realtime + polling

```typescript
// dashboard/lib/realtime.ts
export function subscribeToActions(callback: (action: Action) => void) {
  const channel = supabase
    .channel('actions-feed')
    .on('postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'actions' },
        (payload) => callback(payload.new as Action))
    .subscribe();

  // Fallback polling — fires every 5s in case realtime drops
  const poll = setInterval(async () => {
    const { data } = await supabase
      .from('actions').select('*')
      .order('started_at', { ascending: false }).limit(10);
    data?.forEach(callback);
  }, 5000);

  return () => { channel.unsubscribe(); clearInterval(poll); };
}
```

The polling fallback uses a `seen_ids` Set on the client side to dedup.

### Metrics queries

Single query, runs every 5s on the dashboard:

```typescript
async function getMetrics() {
  const [leads, sites, sent, replies, meetings] = await Promise.all([
    supabase.from('leads').select('id, qualification_status', { count: 'exact' }),
    supabase.from('generated_sites').select('id', { count: 'exact' }),
    supabase.from('outreach').select('id', { count: 'exact' }).eq('status', 'sent'),
    supabase.from('inbound').select('id', { count: 'exact' }),
    supabase.from('meetings').select('id', { count: 'exact' }),
  ]);
  // ...
}
```

### "Wow moment" visuals

1. **Live activity feed scrolling during demo.** Real timestamps. Real
   business names. Real reasoning. Judges read this and *understand* what
   the agent is doing.

2. **Mockup preview hover.** Hovering a lead in the leads table previews
   the winning mockup site as an iframe. Click opens the live URL.

3. **Counter animations.** When the meetings counter ticks up, it pulses.
   That's the moment in the demo. Don't over-animate elsewhere — let the
   meetings counter pulse alone do the work.

4. **Claw cards show real current activity.** Not "online/offline". The
   text content updates: "Designer: critiquing retro variant for Joe's Auto
   Body (iteration 2)".

### Priorities

- **Clarity > beauty.** White background, dark text, generous spacing.
  Tailwind defaults. No custom theme until H+22.
- **Reliability > realtime.** Polling fallback always on. If realtime
  works, great. If it doesn't, demo still works.
- **Demo impact > completeness.** The leads table doesn't need pagination,
  filtering, or search. It needs to look populated and update live.

---

## SECTION 8 — IMPLEMENTATION PLAN

### H+0 to H+6 — Foundation

**Objective:** all infrastructure live. No agent logic yet, but everything
the agents need exists.

**Tasks (in order):**

| # | Task | Owner | Time |
|---|------|-------|------|
| 1 | Install/onboard NemoClaw sandbox + verify OpenShell/Nemotron route | A | 30m |
| 2 | Codex Task 1 — rate_limit_check.py, run it, document results | B | 30m |
| 3 | Codex Task 2 — buy domain, set up Resend DNS | D | 30m |
| 4 | Codex Task 3 — provision Supabase, run schema SQL | A | 30m |
| 5 | Codex Task 4 — set up monorepo skeleton | A | 30m |
| 6 | Codex Task 5 — provision Vercel project for dashboard | D | 15m |
| 7 | Codex Task 6 — Apify account, test scrape, save sample JSON | B | 45m |
| 8 | Codex Task 7 — set up Discord server, channel, webhook | D | 15m |
| 9 | Codex Task 8 — write shared/nemotron_client.py + test | A | 30m |
| 10 | Codex Task 9 — write shared/supabase_client.py + test | A | 30m |
| 11 | Codex Task 10 — write shared/logger.py + test | A | 20m |
| 12 | Codex Task 11 — write shared/discord_bridge.py + test | A | 20m |

**Dependencies:** #4 blocks everything DB-related. #3 blocks #2 partially (DNS propagation runs in background).

**Risks:** Resend DNS propagation can take 1-4 hours. Start it H+0:30. Apify free tier might be low; use $5 personal card if needed.

**Fallback:** if Resend is stuck on DNS, switch to SendGrid (or any SMTP). If Vercel API is flaky, all mockups go to Supabase Storage.

**H+6 checkpoint:** all keys in `.env`, schema in Supabase, can fire a Nemotron request through NemoClaw/OpenShell from Python and get JSON back, can write a row to Supabase from Python, can post to Discord.

---

### H+6 to H+12 — Scout + Designer (the visible pipeline)

**Objective:** Scout populates leads, Designer generates one mockup per lead, both visible in DB. This is the GO/NO-GO checkpoint.

**Tasks:**

| # | Task | Owner | Time |
|---|------|-------|------|
| 13 | Scout tool: scrape_leads.py | B | 1h |
| 14 | Scout tool: score_website.py | B | 1.5h |
| 15 | Scout tool: extract_pain_points.py | B | 45m |
| 16 | Scout claw: claw.py heartbeat + SOUL/AGENTS files | A | 1h |
| 17 | Test Scout end-to-end on 5 real leads | B | 30m |
| 18 | Designer tool: generate_mockup.py | C | 1.5h |
| 19 | Designer tool: deploy_to_vercel.py + storage fallback | C | 1h |
| 20 | Designer claw MVP: 1 variant, no critique, auto-winner | C | 1h |
| 21 | Test Designer end-to-end on 3 Scout-qualified leads | C | 30m |
| 22 | Dashboard skeleton: layout, claw cards, leads table | D | 2h |
| 23 | Dashboard: live action feed | D | 1h |

**Dependencies:** All Scout tools before Scout claw. Designer can develop in parallel.

**Risks:** mockup generation quality. If at H+10 the mockups look like Geocities, person C stops adding features and spends 2h on prompt iteration.

**H+12 checkpoint (GO/NO-GO):**

✅ Scout produces 20+ qualified leads autonomously
✅ Designer produces deployed mockup URLs for 5+ leads
✅ Dashboard shows leads table populated with live updates
✅ Action feed shows real activity

If any of the above is failing at H+12:
- Cut Closer entirely
- Cut Discord bridge — use dashboard buttons for approval
- Cut self-critique loops on Designer and Pitcher
- Cut multiple variants — 1 mockup, 1 email per lead

---

### H+12 to H+18 — Pitcher + Closer (the smart pipeline)

**Objective:** end-to-end agent autonomy: scrape → mockup → email drafted → approval → send → reply → meeting booked.

**Tasks:**

| # | Task | Owner | Time |
|---|------|-------|------|
| 24 | Pitcher tool: generate_email.py (all 4 angles in one file) | C | 1h |
| 25 | Pitcher tool: critique_email.py | C | 45m |
| 26 | Pitcher tool: send_email.py (Resend) | C | 30m |
| 27 | Pitcher claw: heartbeat with approval flow | A | 1h |
| 28 | Discord bridge worker (listens for APPROVE/EDIT/SKIP) | A | 1.5h |
| 29 | Closer tool: classify_reply.py | D | 45m |
| 30 | Closer tool: gcal integration (free_slots + create_event) | D | 1.5h |
| 31 | Closer tool: propose_meeting_times.py + book_meeting.py | D | 1h |
| 32 | Closer claw: heartbeat for inbound emails | A | 1h |
| 33 | Resend inbound webhook handler | A | 30m |
| 34 | Dashboard: lead detail page | D | 1.5h |
| 35 | Dashboard: metrics bar with live counts | D | 30m |
| 36 | Self-critique loop in Designer | C | 1h |
| 37 | 3-variant + pick-winner in Designer | C | 45m |
| 38 | 4-angle + critique in Pitcher (upgrade from 1-angle MVP) | C | 1h |

**Dependencies:** #28 blocks Pitcher autonomy from working. #33 blocks Closer entirely (no inbound = no work).

**Risks:** Discord bridge bot setup can take longer than expected for first-time Discord developers. Have a Plan B: dashboard approval buttons.

**H+18 checkpoint:**

✅ A test reply email triggers Closer
✅ Closer drafts response, posts to Discord
✅ Operator approves in Discord
✅ Meeting appears on real Google Calendar
✅ Dashboard reflects it all in real time

---

### H+18 to H+24 — Polish + Run + Demo

**Objective:** populate the dashboard via overnight run, fix demo-killing bugs, rehearse.

**Tasks:**

| # | Task | Owner | Time |
|---|------|-------|------|
| 39 | MEMORY.md self-update loop (all 4 agents) | A | 1h |
| 40 | Demo data seeder (fake inbound replies for demo) | A | 30m |
| 41 | Start all 4 claws unattended in AUTONOMOUS_MODE=true | A | 5m |
| 42 | Monitor + fix issues during overnight run | A | 2h |
| 43 | Dashboard polish: typography, claw card animations | D | 1.5h |
| 44 | Mockup quality pass: hand-tune prompts | C | 1.5h |
| 45 | Backup demo video record | All | 30m |
| 46 | Demo rehearsal x3 | All | 45m |
| 47 | Vapi inbound (STRETCH, only if H+18 is green) | D | 2h |

**H+22 feature freeze.** No new code after this. Only bug fixes. **H+23 submission.**

---

## SECTION 9 — CUT LIST

### MUST HAVE (cut these and you don't have a project)
- Scout: scraping + scoring + qualification
- Designer: at least 1 mockup variant deployed
- Pitcher: at least 1 angle drafted + send-on-approval
- Closer: email reply classification + at least one auto-reply path
- Dashboard: leads table + action feed + metrics counters
- Supabase + the schema
- Resend setup (sending only is enough for MVP)

### SHOULD HAVE (the demo really needs these)
- Discord bridge approval flow
- 3 mockup variants + self-critique
- 4 email angles + critique
- Google Calendar booking
- MEMORY.md self-update
- Lead detail page

### NICE TO HAVE
- Autonomous niche/city expansion proposals
- Mockup hero image generation
- Reply-to-objection bank
- Counter pulse animations
- Dashboard typography polish

### CUT IMMEDIATELY IF BEHIND
- **Vapi voice (entire feature)** — if not started by H+18, do not start
- Multiple variant/angle systems — fall back to 1 each
- Self-critique loops — fall back to direct generation
- Discord bridge — fall back to dashboard buttons
- Autonomous expansion proposals
- Anything cosmetic on the dashboard

---

## SECTION 10 — CODEX EXECUTION TASKS

Each task is ~10-30 minutes of Codex time. Tasks are ordered. Codex
completes them in sequence unless explicitly parallelizable.

### TASK 0 — NemoClaw install/onboard + sandbox smoke test
**Objective:** make NemoClaw the actual runtime before building agent code.
**Files:** `nemoclaw/install_and_onboard.sh`, `nemoclaw/README.md`, `nemoclaw/network-policy.md`, `nemoclaw/model-routing.md`
**Steps:**
1. Install NemoClaw using the official installer or the Brev early-preview flow.
2. Run `nemoclaw onboard` for sandbox name `mainstreet`.
3. Select/configure the Nemotron provider or routed provider.
4. Verify sandbox status with `nemoclaw mainstreet status`.
5. Connect with `nemoclaw mainstreet connect`.
6. Inside the sandbox, verify the claw shell/TUI opens.
7. From inside the sandbox, run a single inference smoke test against `NEMOTRON_BASE_URL`.
8. Add network-policy notes for required outbound services: Supabase, Apify, Vercel, Resend, Discord, Google Calendar, and Vapi if used.
9. Document the exact commands that worked in `nemoclaw/README.md`.
**Acceptance:** NemoClaw sandbox is running, the agent can call Nemotron through the configured route, and Python can reach Supabase from inside the sandbox.
**Dependencies:** NVIDIA/Brev credentials, Docker/runtime available.
**Complexity:** moderate. Do this before writing agent code.

### TASK 1 — Rate limit check script
**Objective:** Determine Nemotron-through-NemoClaw and Apify rate limits before any agent is built.
**Files:** `agents/scripts/rate_limit_check.py`
**Steps:**
1. Read `NEMOTRON_BASE_URL`, `NVIDIA_API_KEY`, `APIFY_TOKEN` from env
2. Fire 100 Nemotron requests through the NemoClaw/OpenShell inference route when available in batches of 10 with `asyncio.gather`,
   short prompt "say ok", log timestamps + statuses
3. Compute RPM by counting successes in each 60-second window
4. Fire 20 Apify scrape jobs with 5-business limit, similarly measure
5. Print: `NEMOCLAW_NEMOTRON_OBSERVED_RPM=X`, `APIFY_OBSERVED_RPM=Y`
**Acceptance:** script runs without crashing, prints both numbers.
**Dependencies:** none.
**Complexity:** simple.

### TASK 2 — Domain + Resend DNS
**Objective:** sending domain ready for email.
**Files:** none (manual setup)
**Steps:**
1. Buy domain (e.g., `mainstreet.team`) on Namecheap or Porkbun
2. Create Resend account, add domain, copy DNS records
3. Add SPF, DKIM, DMARC records to domain DNS
4. Wait for verification in Resend dashboard (can take 1-4h)
5. Create API key, save as `RESEND_API_KEY` in `.env.example` + actual `.env`
6. Set `OUTREACH_FROM_ADDRESS=pitcher@{domain}` in `.env`
**Acceptance:** Resend shows domain "verified".
**Complexity:** trivial but waits on DNS.

### TASK 3 — Supabase project + schema
**Objective:** database live.
**Files:** `agents/scripts/setup_supabase.sql`
**Steps:**
1. Create Supabase project
2. Save `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` to `.env`
3. Paste all SQL from Section 3 into Supabase SQL Editor, run
4. Verify all tables exist and Realtime publication includes them
5. Create public Storage bucket `mockups`
6. Save `setup_supabase.sql` to repo so it's reproducible
**Acceptance:** can `SELECT * FROM leads` returns empty result, not error.
**Complexity:** simple.

### TASK 4 — Monorepo skeleton
**Objective:** folder structure + base configs.
**Files:** the entire tree in Section 2 (empty files except configs)
**Steps:**
1. `mkdir -p` all directories from Section 2 tree
2. Create `agents/pyproject.toml` with deps: openai, supabase,
   httpx, playwright, pydantic, python-dotenv
3. Create `agents/requirements.txt` mirroring pyproject
4. Create `dashboard/package.json` with deps: next, react, @supabase/supabase-js,
   tailwindcss, typescript
5. Create `.env.example` with every env var listed below
6. `.gitignore`: .env, node_modules, .next, __pycache__, .venv
7. Run `cd dashboard && npx create-next-app@latest . --ts --tailwind --app
   --no-eslint --no-src-dir --import-alias "@/*"` to scaffold the Next.js app
**Acceptance:** `tree -L 3` shows the full structure, both subprojects install
without errors.
**Complexity:** simple.

**Env vars to include in `.env.example`:**
```
# NemoClaw / OpenShell
NEMOCLAW_SANDBOX_NAME=mainstreet
NEMOCLAW_PROVIDER=nvidia
NEMOCLAW_NON_INTERACTIVE=1
NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1
NEMOCLAW_WORKSPACE=/workspace/mainstreet/agents

# Nemotron
# Inside NemoClaw/OpenShell, prefer https://inference.local/v1.
# Outside the sandbox for local dev, use https://integrate.api.nvidia.com/v1.
NVIDIA_API_KEY=
NEMOTRON_MODEL=nvidia/nemotron-3-super-120b-a12b
NEMOTRON_BASE_URL=https://inference.local/v1

# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# Apify
APIFY_TOKEN=

# Resend
RESEND_API_KEY=
OUTREACH_FROM_ADDRESS=

# Vercel
VERCEL_TOKEN=
VERCEL_TEAM_ID=

# Google Calendar
GCAL_CLIENT_ID=
GCAL_CLIENT_SECRET=
GCAL_REFRESH_TOKEN=

# Vapi (stretch)
VAPI_API_KEY=
VAPI_PHONE_NUMBER=

# Discord
DISCORD_WEBHOOK_URL=
DISCORD_BOT_TOKEN=
DISCORD_APPROVAL_CHANNEL_ID=

# Runtime flags
AUTONOMOUS_MODE=false
IGNORE_QUIET_HOURS=true
```

### TASK 5 — Vercel project
**Objective:** dashboard deployable.
**Steps:**
1. Create Vercel project, link to repo, set root dir to `dashboard/`
2. Add Supabase env vars to Vercel project settings
3. Deploy, get the dashboard URL
**Acceptance:** dashboard URL loads (probably 404 or empty page — that's fine).
**Complexity:** trivial.

### TASK 6 — Apify test scrape
**Objective:** verify scraping works, save sample data.
**Files:** `agents/scripts/test_apify.py`, `agents/scripts/sample_leads.json`
**Steps:**
1. Write script that calls the compass/crawler-google-places actor
2. Search: "auto repair" in "Santa Cruz, CA", limit 10
3. Save raw output to `sample_leads.json` for later development without
   re-hitting API
**Acceptance:** sample_leads.json has 5+ businesses with website/phone fields.
**Complexity:** simple.

### TASK 7 — Discord setup
**Objective:** Discord channel and webhook ready.
**Steps:**
1. Create Discord server "Mainstreet Control" (or use existing team server)
2. Create channel `#mainstreet-control`
3. Channel Settings → Integrations → Webhooks → create webhook → copy URL
4. For approval replies (stretch): create Discord application, bot user,
   add to server, save bot token + channel ID
5. Add to `.env`
**Acceptance:** can curl the webhook URL and see message in channel.
**Complexity:** trivial.

### TASK 8 — Nemotron client
**Objective:** reliable JSON-returning wrapper.
**Files:** `agents/shared/nemotron_client.py`
**Steps:**
1. Import OpenAI client, configure with `NEMOTRON_BASE_URL` and
   `NVIDIA_API_KEY`
   - If `NEMOTRON_BASE_URL` contains `inference.local`, this is the NemoClaw/OpenShell route. Allow the API key to default to a placeholder like `openshell` if the gateway handles credentials.
   - If using the direct NVIDIA endpoint outside the sandbox, require `NVIDIA_API_KEY`.
2. Export `chat_json(system: str, user: str, model: str = None,
   retries: int = 1) -> dict`:
   - sets `response_format={"type": "json_object"}` if model supports
   - prepends instruction to system: "Return only valid JSON."
   - tries up to `retries+1` times to parse JSON
   - on final failure, raises `NemotronJSONError`
3. Also export `chat_vision(system: str, user: str, image_b64: str) -> dict`
   for Designer's screenshot critique
4. Include a `test_nemotron()` function at the bottom that hits the API
   with "return {\"ok\": true}" and asserts the result
**Acceptance:** `python -m agents.shared.nemotron_client` prints `OK`.
**Complexity:** moderate.

### TASK 9 — Supabase client + helpers
**Objective:** typed DB operations.
**Files:** `agents/shared/supabase_client.py`, `agents/shared/types.py`
**Steps:**
1. types.py: dataclasses from Section 3
2. supabase_client.py: singleton client + helpers:
   - `next_scout_target() -> dict` (reads config)
   - `insert_leads(rows: list[dict]) -> int`
   - `next_designer_lead() -> Optional[Lead]`
   - `claim_lead_for_designer(lead_id) -> bool` (UPDATE...WHERE worked_by_designer=false RETURNING)
   - `next_pitcher_lead() -> Optional[dict]` (joined with winning mockup)
   - `claim_lead_for_pitcher(lead_id) -> bool`
   - `next_inbound() -> Optional[Inbound]`
   - `mark_inbound_handled(inbound_id, classification, handled_by)`
   - `insert_action(...)` → log_action lives here
   - `read_memory(claw_name) -> str` (reads MEMORY.md from disk, not DB)
   - `append_memory(claw_name, pattern: str)`
**Acceptance:** module imports without errors; `claim_lead_for_designer` returns
True first time and False second time on same lead.
**Complexity:** moderate.

### TASK 10 — Action logger
**Objective:** human-readable action logging.
**Files:** `agents/shared/logger.py`
**Steps:**
1. Wraps `insert_action`
2. Public API: `log(claw, action_type, status, log_text, lead_id=None, result=None)`
3. Auto-fills emoji based on claw_name
4. Auto-fills `started_at`, `finished_at`
5. Has a context manager version: `with logger.action(claw, type, lead_id) as a:
   a.set_log("..."); a.set_result({...})`
**Acceptance:** calling `log("scout", "scrape", "succeeded", "scraped 20 leads")`
inserts a row visible in Supabase.
**Complexity:** simple.

### TASK 11 — Discord bridge (outbound)
**Objective:** post to Discord from agents.
**Files:** `agents/shared/discord_bridge.py`
**Steps:**
1. Public API: `post(content: str, embed: Optional[dict] = None)`
2. Uses webhook URL from env
3. Auto-truncates content to 1900 chars (Discord limit is 2000)
4. Retries once on 5xx
**Acceptance:** `post("test message")` shows up in `#mainstreet-control`.
**Complexity:** trivial.

### TASK 12 — Scout tool: scrape_leads
**Objective:** wrap Apify, dedup against DB, insert new leads.
**Files:** `agents/scout/tools/scrape_leads.py`,
`agents/integrations/apify_client.py`
**Steps:**
1. apify_client.py: `scrape_google_places(query, location, max_results)` per
   Section 6
2. scrape_leads.py: `def run(city, niche, limit=20) -> int`:
   - calls apify_client
   - for each result: skip if (business_name, address) already in `leads`
   - else build a lead row dict, insert
   - return count of inserted rows
3. Log each scrape (entire batch) and each insert (individual lead) via logger
**Acceptance:** running this once on Santa Cruz auto repair returns 5+ new
leads in DB.
**Complexity:** moderate.

### TASK 13 — Scout tool: score_website
**Objective:** score a website 0-10 with reasons.
**Files:** `agents/scout/tools/score_website.py`
**Steps:**
1. If `url` is None or empty: return `{"score": 0, "reasons": ["no website"]}`
2. Use `httpx.AsyncClient` with timeout=10s to fetch
3. Score factors (each adds points up to 10):
   - HTTP 200 + reachable: +2 (else return score 0)
   - HTTPS: +1
   - Has `<meta name="viewport">` (mobile): +2
   - Page weight < 2MB: +1
   - Has structured data (JSON-LD or microdata): +1
   - Has phone number in DOM: +1
   - Last-Modified header within 2 years (if present): +1
   - Title tag length 30-60 chars: +1
4. Build `reasons` list with one short string per failed factor
5. Return `{"score": int, "reasons": [str]}`
6. Wrap in logger context
**Acceptance:** unit tests against 3 known URLs: a good site → 7+, a broken
site → 3-, no URL → 0.
**Complexity:** moderate.

### TASK 14 — Scout tool: extract_pain_points
**Objective:** turn reviews into pain points via Nemotron.
**Files:** `agents/scout/tools/extract_pain_points.py`,
`agents/prompts/scout_extract_pain.txt`
**Steps:**
1. Pull `leads.review_count` and reviews (you need to extend apify scrape
   to capture top 10 reviews — add `scrapeReviewsCount: 10` to the actor
   config in scrape_leads, save review text to a new column
   `leads.review_texts text[]`.)
2. If `review_count` < 5: return empty list, log "insufficient reviews"
3. Build prompt from `scout_extract_pain.txt` (full prompt in Section 5)
4. Call `nemotron_client.chat_json`
5. Parse `{"pain_points": [...]}`
6. Update `leads.top_review_pain_points`
7. Return the list
**Acceptance:** on a lead with 10+ negative reviews, returns 3 pain points;
on a 5-star business, returns empty list.
**Complexity:** moderate.

### TASK 15 — Scout claw integration
**Objective:** the actual Scout agent loop.
**Files:** `agents/scout/SOUL.md`, `agents/scout/AGENTS.md`,
`agents/scout/TOOLS.md`, `agents/scout/HEARTBEAT.md`, `agents/scout/claw.py`
**Steps:**
1. Copy SOUL.md and AGENTS.md content from the prior Mainstreet bundle
2. TOOLS.md: enumerate the 3 tools with signatures
3. HEARTBEAT.md: `interval: 60s`, `entrypoint: claw.py:heartbeat`
4. claw.py implements `def heartbeat()`:
   - Read MEMORY.md
   - Read config
   - Compute current dedup ratio (last hour scrapes vs new inserts)
   - If dedup > 90%: post expansion proposal, return
   - Call scrape_leads.run(city, niche, limit=20)
   - For each new lead in result: score_website, extract_pain_points, set
     qualification_status per rubric
   - End-of-heartbeat: optionally append MEMORY.md
   - Post summary to Discord
5. Add a `--once` flag for manual testing
**Acceptance:** `python -m agents.scout.claw --once` runs end-to-end on real
data, populates leads, posts to Discord.
**Complexity:** complex (this is the integration task).

### TASK 16 — Designer tool: generate_mockup
**Objective:** Nemotron-generated HTML, one variant.
**Files:** `agents/designer/tools/generate_mockup.py`,
`agents/prompts/designer_generate.txt`,
`agents/prompts/variants_clean_modern.txt`,
`agents/prompts/variants_retro_local.txt`,
`agents/prompts/variants_premium.txt`
**Steps:**
1. Prompt files contain the full prompts from Section 5
2. `def run(lead: dict, variant: str, previous_critique: Optional[dict] = None)
   -> str`:
   - Build prompt by formatting `designer_generate.txt` with lead data + variant block
   - If previous_critique, inject into prompt
   - Call nemotron (use `chat_json` even though output is HTML — wrap it:
     `{"html": "<!DOCTYPE html>..."}`)
   - Validate response has `<!DOCTYPE` and `</html>`
   - Return HTML string
3. On invalid HTML: retry once with "previous output was malformed, regenerate"
**Acceptance:** for a sample lead, returns valid HTML containing the business
name.
**Complexity:** moderate.

### TASK 17 — Designer tool: screenshot_html
**Objective:** PIL/Playwright screenshot of HTML.
**Files:** `agents/designer/tools/screenshot_html.py`
**Steps:**
1. Use Playwright Python sync API
2. `def run(html: str) -> bytes`:
   - Launch headless chromium
   - Create a new page, set viewport 1280x800
   - `page.set_content(html)`
   - `page.screenshot(full_page=True)` returns bytes
   - Return bytes
3. Encode as base64 for prompt use: `def run_b64(html: str) -> str`
**Acceptance:** returns valid PNG bytes; manually inspecting one looks right.
**Complexity:** moderate. Playwright install can be sticky — use
`playwright install chromium` in setup script.

### TASK 18 — Designer tool: critique_mockup
**Objective:** vision-based self-critique.
**Files:** `agents/designer/tools/critique_mockup.py`,
`agents/prompts/designer_critique.txt`
**Steps:**
1. `def run(html: str, lead: dict) -> dict`:
   - Take screenshot via `screenshot_html.run_b64`
   - Format critique prompt with business context
   - Call `nemotron_client.chat_vision`
   - Parse `{"score": int, "issues": [...], "suggestions": [...]}`
   - Return dict
**Acceptance:** for a known-bad HTML (e.g., just `<h1>Test</h1>`), returns
score < 5.
**Complexity:** moderate. **Risk:** Nemotron 3 Super 120B may not be
vision-capable — if so, fall back to scoring based on raw HTML inspection
(check for required sections, count `<img>` tags, etc.) without vision. The
prompt becomes "based on this HTML structure..." instead of "based on this
screenshot...".

### TASK 19 — Designer tool: deploy_to_vercel + fallback
**Objective:** publish HTML, get URL back.
**Files:** `agents/designer/tools/deploy_to_vercel.py`,
`agents/integrations/vercel_client.py`,
`agents/integrations/supabase_storage_client.py`
**Steps:**
1. vercel_client.py: `deploy_html_as_site(html, slug) -> str` per Section 6
2. supabase_storage_client.py: `upload_html(html, path) -> str`
3. deploy_to_vercel.py: tries vercel first, on any exception falls back to
   supabase_storage, returns whichever URL succeeded plus a `provider` field
   in the response: `{"url": "...", "provider": "vercel" | "supabase"}`
**Acceptance:** can deploy a test HTML, returned URL loads in browser.
**Complexity:** moderate.

### TASK 20 — Designer tool: pick_winner
**Objective:** Nemotron picks the best variant.
**Files:** `agents/designer/tools/pick_winner.py`,
`agents/prompts/designer_pick_winner.txt`
**Steps:**
1. Input: `lead: dict`, `variants: list[{variant, url, score, html}]`
2. Build prompt with lead vibe signals + variants summary
3. Nemotron returns `{"winner": "<variant_name>", "reasoning": "..."}`
4. Return the dict
**Acceptance:** for a "since 1987" diner, picks retro_local over clean_modern.
**Complexity:** simple.

### TASK 21 — Designer claw integration
**Objective:** the Designer agent loop.
**Files:** `agents/designer/SOUL.md`, `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`,
`claw.py`
**MVP clarification:** Task 21 should ship a reliable one-variant, one-critique
Designer path by default (`DESIGNER_VARIANT_COUNT=1`). Tasks 36-37 harden this
into the full 3-variant, multi-iteration winner-picking behavior.
**Steps:**
1. Copy SOUL/AGENTS from prior bundle
2. claw.py implements heartbeat per Section 4 spec
3. Use the claim pattern to prevent re-pickup
4. MVP mode: run one variant sequentially and keep one critique pass for demo reliability
5. Use env var `DESIGNER_VARIANT_COUNT=1` as the MVP default; Tasks 36-37 harden this to full 3-variant, multi-iteration behavior
6. If `DESIGNER_VARIANT_COUNT=3` is set early, run [clean_modern, retro_local, premium] sequentially and pick a winner
**Acceptance:** `python -m agents.designer.claw --once` picks a qualified lead,
produces at least one hosted URL in MVP mode. After Tasks 36-37, it produces
3 hosted URLs and marks one as winner.
**Complexity:** complex.

### TASK 22 — Dashboard skeleton
**Objective:** the demo screen exists and loads.
**Files:** `dashboard/app/page.tsx`, `dashboard/app/layout.tsx`,
`dashboard/lib/supabase.ts`, `dashboard/components/ClawCard.tsx`,
`dashboard/components/MetricsBar.tsx`, `dashboard/components/LeadsTable.tsx`,
`dashboard/lib/types.ts`
**Steps:**
1. `lib/supabase.ts` exports browser client using ANON_KEY
2. `lib/types.ts` mirrors `agents/shared/types.py` types as TS interfaces
3. `app/page.tsx` is a server component that:
   - Fetches initial leads + actions + metrics
   - Renders the layout from Section 7
4. `ClawCard` component: shows claw name, emoji, current activity (most
   recent action by that claw)
5. `MetricsBar`: 5 counters (scraped, qualified, sites, sent, booked)
6. `LeadsTable`: list of leads with score + status
7. Tailwind only — no custom CSS
**Acceptance:** dashboard loads at the Vercel URL, shows real data from the DB,
no realtime yet.
**Complexity:** moderate.

### TASK 23 — Dashboard activity feed with realtime
**Objective:** live action stream.
**Files:** `dashboard/components/ActivityFeed.tsx`,
`dashboard/lib/realtime.ts`
**Steps:**
1. ActivityFeed is a client component (`'use client'`)
2. Uses `subscribeToActions` from `lib/realtime.ts`
3. Maintains a state array of latest 50 actions
4. On new action: prepend to array, trim to 50
5. Renders each action's `human_readable_log` with timestamp, color-coded
   by `claw_name`
6. Includes the polling fallback from Section 7
**Acceptance:** running Scout claw inserts new actions that appear in the
feed within 5 seconds.
**Complexity:** moderate.

### TASK 24 — Pitcher tool: generate_email
**Objective:** all 4 angles in one tool.
**Files:** `agents/pitcher/tools/generate_email.py`,
`agents/prompts/pitcher_generate_pain.txt`,
`agents/prompts/pitcher_generate_compare.txt`,
`agents/prompts/pitcher_generate_social.txt`,
`agents/prompts/pitcher_generate_curiosity.txt`
**Steps:**
1. `def run(lead: dict, mockup_url: str, angle: str) -> dict`:
   - Load the right prompt file by angle name
   - Format with lead data
   - Call nemotron with JSON output format
   - Validate `{"subject": str, "body": str}`
   - Sanity check: subject ≤ 50 chars, body has ≤ 5 sentences (split on `.!?`)
   - Return dict
2. If validation fails: regenerate once with "previous output violated rules"
**Acceptance:** all 4 angles produce valid output on a sample lead.
**Complexity:** moderate.

### TASK 25 — Pitcher tool: critique_email
**Objective:** self-critique with 4 sub-scores.
**Files:** `agents/pitcher/tools/critique_email.py`,
`agents/prompts/pitcher_critique.txt`
**Steps:**
1. `def run(subject: str, body: str, lead: dict) -> dict`:
   - Build prompt with the email + business context
   - Nemotron returns sub-scores + overall + biggest_issue
   - Return dict
**Acceptance:** for a known bad email (just "buy our stuff"), returns
overall_score < 5.
**Complexity:** simple.

### TASK 26 — Pitcher tool: send_email
**Objective:** Resend integration.
**Files:** `agents/pitcher/tools/send_email.py`,
`agents/integrations/resend_client.py`
**Steps:**
1. resend_client.py per Section 6
2. send_email.py: `def run(outreach_id: UUID) -> dict`:
   - Fetch outreach row
   - Fetch lead row for `to` address (use `leads.email`)
   - Convert body (plain text) to minimal HTML (wrap in `<p>`, preserve line breaks)
   - Call resend_client
   - Update outreach: status='sent', sent_at=now(), resend_message_id=resp.id
   - Return `{"sent": true, "message_id": "..."}`
**Acceptance:** sends a real email to a test address.
**Complexity:** moderate.

### TASK 27 — Pitcher claw integration
**Objective:** Pitcher agent loop.
**Files:** `agents/pitcher/SOUL.md`, `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`,
`claw.py`
**Steps:**
1. claw.py heartbeat:
   - Read MEMORY.md
   - Get next pitcher lead
   - Claim it
   - Generate 4 emails (sequential for simplicity), critique each
   - Pick highest scoring
   - Insert outreach row with `status='pending_approval'` (or `'approved'`
     if `AUTONOMOUS_MODE=true`)
   - Post to Discord approval channel
   - ALSO: scan outreach for `status='approved'` AND `sent_at IS NULL`, send those
2. MVP env var `PITCHER_ANGLE_COUNT=1` skips the multi-angle loop
**Acceptance:** end-to-end pitcher run produces an outreach row, posts to Discord,
on autonomous mode also sends.
**Complexity:** complex.

### TASK 28 — Discord bridge worker (inbound)
**Objective:** parse Discord replies, write to approvals table.
**Files:** `workers/discord_bridge.py`
**Steps:**
1. Use `discord.py` library
2. Bot listens to `DISCORD_APPROVAL_CHANNEL_ID`
3. On message: parse for patterns `APPROVE <uuid>`, `EDIT <uuid>`,
   `SKIP <uuid>` (case insensitive)
4. On APPROVE: insert `approvals` row with `decision='approve'`,
   `decided_at=now()`, `decided_by=author.name`. ALSO update the target
   directly: `outreach.status='approved'`.
5. On SKIP: similar, but `outreach.status='skipped'`
6. On EDIT: expect a follow-up message in a thread or within 60s with
   `Subject: ...\nBody: ...` format → parse and update outreach
7. Run as a long-lived process: `python -m workers.discord_bridge`
**Acceptance:** typing `APPROVE <uuid>` in Discord causes outreach row to
update.
**Complexity:** complex.

### TASK 29 — Closer tool: classify_reply
**Files:** `agents/closer/tools/classify_reply.py`,
`agents/prompts/closer_classify.txt`
**Steps:**
1. `def run(inbound_id: UUID) -> dict`:
   - Fetch inbound row
   - Build classification prompt
   - Call nemotron
   - Update inbound with classification, confidence, key_phrase
   - Return dict
**Acceptance:** on test inbounds with various sentiments, classifies correctly
4/5 times.
**Complexity:** simple.

### TASK 30 — Google Calendar integration
**Files:** `agents/integrations/gcal_client.py`
**Steps:**
1. Use `google-api-python-client` + `google-auth`
2. `get_credentials()`: builds creds from `GCAL_CLIENT_ID`,
   `GCAL_CLIENT_SECRET`, `GCAL_REFRESH_TOKEN`, refreshing if needed
3. `get_free_slots(duration_minutes, days_ahead, hours_range, tz) ->
   list[datetime]`: uses freebusy API, returns 3 free slots
4. `create_event(title, description, start, duration, attendee_email) ->
   str`: creates event, returns event ID
5. ALSO write a one-time script `agents/scripts/gcal_oauth.py` that runs
   the OAuth flow and prints the refresh token to save in env
**Acceptance:** can list 3 free slots, can create a test event visible on calendar.
**Complexity:** complex (OAuth setup is fiddly).

### TASK 31 — Closer tools: propose_meeting_times, book_meeting, draft_reply
**Files:** `agents/closer/tools/propose_meeting_times.py`,
`agents/closer/tools/book_meeting.py`, `agents/closer/tools/draft_reply.py`
**Steps:**
1. propose_meeting_times: thin wrapper around gcal_client.get_free_slots,
   formats output as "Tuesday 10am, Wednesday 2pm, Thursday 11am Pacific"
2. book_meeting: takes `lead_id`, `chosen_slot`, `attendee_email`, calls
   gcal create_event, writes `meetings` row, returns event_id
3. draft_reply: takes `inbound_id` and `branch` (interested/question/objection),
   builds appropriate Nemotron prompt, returns `{subject, body}`
**Acceptance:** each tool works standalone.
**Complexity:** moderate.

### TASK 32 — Closer claw integration
**Files:** `agents/closer/SOUL.md`, `AGENTS.md`, `TOOLS.md`, `HEARTBEAT.md`,
`claw.py`
**Steps:**
1. claw.py heartbeat per Section 4
2. 30s interval (faster than other claws)
3. Branches by classification
**Acceptance:** simulating a test reply triggers full Closer flow.
**Complexity:** complex.

### TASK 33 — Resend inbound webhook
**Files:** `dashboard/app/api/inbound-email/route.ts`
**Steps:**
1. POST handler
2. Parse Resend's payload
3. Match to lead: lookup `outreach` rows where `to_address` matches `from`
4. INSERT into `inbound` with channel='email', from_address, raw_content
5. Return 200 OK
6. **In Resend dashboard:** configure inbound webhook URL to this endpoint
**Acceptance:** sending an email to the configured inbound address creates
an `inbound` row.
**Complexity:** moderate. **Risk:** Resend inbound parsing — if it doesn't
work as expected, fall back to manually inserting test rows for the demo.

### TASK 34 — Lead detail page
**Files:** `dashboard/app/leads/[id]/page.tsx`,
`dashboard/components/LeadDetail.tsx`, `dashboard/components/MockupPreview.tsx`
**Steps:**
1. Server component fetches lead + all related rows (generated_sites, outreach, inbound, meetings, actions for this lead)
2. Renders: header card, mockup variants grid with iframe previews,
   outreach card with subject+body, inbound thread, meeting card, timeline of actions
**Acceptance:** clicking a lead in the table navigates to its detail page,
all data loads.
**Complexity:** moderate.

### TASK 35 — Metrics bar live counts
**Files:** `dashboard/components/MetricsBar.tsx`
**Steps:**
1. Client component
2. Calls metrics query every 5s
3. On meetings count increase: trigger a pulse animation (Tailwind animate-pulse)
**Acceptance:** numbers update live as agents work.
**Complexity:** simple.

### TASK 36 — Designer self-critique loop hardening
**Objective:** harden the iteration loop to full demo behavior after Task 21 MVP.
**Files:** `agents/designer/claw.py`
**Steps:**
1. After generating a variant, run critique
2. If score < 8 and iterations < 5: append critique to prompt, regenerate
3. Track iteration count, save to `generated_sites.self_critique_iterations`
**Acceptance:** in the action log, see entries like "iteration 3 scored 8.4, shipped".
**Complexity:** moderate.

### TASK 37 — Designer 3-variant + pick_winner hardening
**Objective:** harden from Task 21 MVP one-variant mode to 3 variants + winner pick.
**Files:** `agents/designer/claw.py`
**Steps:**
1. Loop over [clean_modern, retro_local, premium]
2. After all 3 deployed: call pick_winner tool
3. Update `is_chosen_winner` on the winning row
**Acceptance:** each lead now has 3 rows in generated_sites, exactly one winner.
**Complexity:** simple (just integration).

### TASK 38 — Pitcher 4-angle + critique upgrade
**Files:** `agents/pitcher/claw.py`
**Steps:** mirror TASK 37 for pitcher.
**Complexity:** simple.

### TASK 39 — MEMORY.md self-update for all claws
**Files:** `agents/shared/memory_updater.py`, plus integration in each claw.py
**Steps:**
1. memory_updater.py: `def maybe_update_memory(claw_name: str, heartbeat_summary: str)`:
   - Read current MEMORY.md
   - Build prompt asking Nemotron for ONE pattern worth keeping
   - If pattern returned, append with timestamp
   - Prune MEMORY.md to last 30 entries
2. Call from end of each claw's heartbeat
**Acceptance:** after a few heartbeats, MEMORY.md files contain real observations.
**Complexity:** moderate.

### TASK 40 — Demo data seeder
**Files:** `agents/scripts/seed_demo_data.py`
**Steps:**
1. Script that inserts pre-written inbound replies for 3 known leads
2. One "interested" reply, one "has_question" reply, one "not_interested"
3. Used during demo to trigger Closer actions on cue
**Complexity:** trivial.

### TASK 41 — Start all 4 claws
**Files:** `agents/scripts/start_all_claws.sh`
**Steps:**
1. Shell script that runs all 4 claws as background processes with nohup
2. Logs to `logs/{claw}.log`
3. Includes `stop_all_claws.sh` companion
**Acceptance:** running it starts 4 processes that survive shell exit.
**Complexity:** trivial.

### TASKS 42-46 — Polish, monitor, rehearse
Less code-heavy, mostly running + watching + fixing.

### TASK 47 — Vapi inbound (STRETCH)
Only attempt if H+18 is green. Define inputs, webhook handler, voice-side tools.

---

## SECTION 11 — FAILURE MODES

### Technical risks

**NemoClaw/OpenShell sandbox setup.** Highest foundation risk. If the sandbox cannot call Nemotron, Supabase, or Apify, the entire agent story stalls. Mitigation: finish TASK 0 first, keep direct NVIDIA API fallback for local development only, and document exact working commands in `nemoclaw/README.md`.

**NemoClaw network policy blocks external services.** Supabase, Apify, Vercel, Resend, Discord, Google Calendar, and Vapi may need explicit allow rules. Mitigation: define allowed egress domains in `nemoclaw/network-policy.md`, smoke-test each service from inside the sandbox, and cut blocked services fast if policy debugging eats time.

**Nemotron rate limits.** Highest risk. Mitigation: do rate-limit check FIRST.
If RPM is below 60, you cannot run 4 claws at 60s heartbeats with self-critique
loops. Throttle by extending heartbeat to 120s, or run claws on staggered
schedules (Scout at :00, Designer at :15, Pitcher at :30, Closer at :45).

**Playwright on the deploy environment.** If you're deploying claws to a
container without browser libs, `playwright install` will fail. Fallback:
HTML-only critique (no screenshot).

**Vercel API key scopes.** First-time setup often misses team-scope. If
deploys 401, regenerate token with team access.

**Supabase Realtime intermittent drops.** Already mitigated with polling fallback.

**Google Calendar refresh token expiry.** Refresh tokens last 6 months when
in production OAuth app; for unverified apps (which is what we're using),
they expire in 7 days. Test the refresh flow in hour 1.

### API limit risks

- Apify free tier: ~$5 in credits per month. At 20 businesses per scrape,
  100 scrapes = limit. Watch usage.
- Resend free tier: 100 emails/day. For demo this is plenty. Don't send
  hundreds during overnight run.
- Nemotron: see above.
- Discord webhook: 30 messages per minute per webhook. Combined output from
  4 claws can exceed this. Mitigation: throttle in `discord_bridge.post()`
  with a 2s sleep between messages.

### Demo risks

**Live demo failure.** Mitigation: record a backup video at H+22.
**Empty dashboard.** Mitigation: pre-populate via overnight run.
**Mockup looks bad on the projector.** Mitigation: print one good mockup screenshot,
keep in slides as a fallback.
**Wifi at venue.** Mitigation: tether to phone, test before stage.

### Prompt failure risks

**Nemotron returns prose instead of JSON.** Mitigation: explicit instruction
+ retry with stricter prompt + JSON validation.
**Nemotron hallucinates business facts.** Mitigation: never let it "remember"
business, always pass data explicitly.
**Critique scores inflate.** Mitigation: include calibration examples in
critique prompt ("8 means: ready to send to owner").

### Race conditions

**Two heartbeats pick the same lead.** Mitigation: the "claim" pattern with
UPDATE ... WHERE worked_by_X = false RETURNING. If returned row is null,
another heartbeat won the race.

**Pitcher and Designer claws for different leads, fine.** But Pitcher
processing a lead while Designer is still on it: the `worked_by_designer`
flag is set BEFORE the work completes. If Designer fails mid-work, the lead
shows as "designer worked" without artifacts. Mitigation: status enum or
explicit "designer_complete" flag set only on success.

**Discord approval arrives between Pitcher heartbeats.** Pitcher's
"check for approved outreach" runs every 60s, so worst case 60s lag. Acceptable.

### Async consistency

**Inbound webhook fires while Closer is processing prior inbound.** No
collision because each inbound is a separate row and Closer claims via
`handled_at = NULL` predicate.

**MEMORY.md file write race.** Two heartbeats of same claw can't run
concurrently (NemoClaw/OpenShell heartbeat scheduling should enforce this, but keep the DB claim pattern anyway). Different claws have different files.
Safe.

---

## SECTION 12 — HACKATHON JUDGE STRATEGY

### What judges actually care about (NVIDIA agent hackathon specifically)

1. **Does it actually run?** They will ask: "show me, live." If your live
   demo crashes, you lose. Build for reliability over features.
2. **Does it use Nemotron meaningfully?** Not just one call, real
   multi-step reasoning. Show the action log with real Nemotron reasoning
   in it.
3. **Is it actually autonomous, or did you script it?** This is where the
   action log saves you. They can read it and see real agent decisions.
4. **Does it use NemoClaw architecture genuinely?** Not just a model wrapper.
   Show the NemoClaw sandbox, heartbeats, SOUL files, OpenShell policy notes, and multi-agent coordination.
5. **Is it a real use case?** Lead gen + outreach is real. They can imagine
   buying it. That matters.

### What creates perceived intelligence

- **Visible reasoning.** The human_readable_log entries are the demo. Read
  some out loud. "The agent picked the retro variant because reviews
  mentioned 'old-school quality' — Nemotron noticed that."
- **Different decisions for different inputs.** If you can show two leads
  side by side getting different mockup styles, different email angles,
  different reply handling — that's intelligence.
- **Self-correction.** "Iteration 1 scored 6.2. Agent regenerated with the
  critique. Iteration 2 scored 8.4." This single phrase wins points.

### The wow moment

The intended wow moment is **a live inbound flow**. Pre-demo, teammate
emails the inbound address with "interested, when can we chat?" Live
during demo, Closer picks it up, classifies it, proposes times, books a
meeting on a calendar that's visible on the projector via a second window.

If Vapi is in, the alternative wow moment is calling the phone number
live. Higher risk; only if H+18 is green.

### What's unnecessary

- Sign-in/auth
- Multiple users
- Settings pages
- Anything administrative
- A pretty landing page for the dashboard
- Animations beyond the meetings counter pulse
- A "how it works" explainer in the UI (you explain that live)

### Emphasize during demo

- "Four NemoClaw claws, each with its own SOUL.md, each running on its own
  heartbeat" (architectural credibility)
- "All coordination through shared memory — no message bus, no queue.
  Database as the queue" (engineering taste)
- "Self-critique means the agent reviews its own work before any human
  sees it" (perceived intelligence)
- "Look at the action log — every line is a real Nemotron decision with
  reasoning" (transparency)
- "We let it run overnight. Here's what it did" (autonomy demonstrated)

### How to avoid looking fake

- **Show the code briefly.** Open `scout/claw.py` for 10 seconds. Judges
  who code respect this.
- **Read live timestamps off the action log.** Real timestamps in the last
  60 seconds are hard to fake.
- **Click into a random lead.** Show the full trail. Show the actual
  generated mockup URL. Click it, the site loads.
- **Don't memorize a script too tightly.** If the demo deviates and you
  recover gracefully, judges believe it more.

### One thing to NOT do

Do not say "AI agents." Say "NemoClaw claws" or "Nemotron-powered claws."
Be specific about the tech. This is an NVIDIA event. Specificity buys
credibility.

---

## APPENDIX — Quick reference for Codex

### Tool function signature contract

Every tool in `agents/{claw}/tools/{name}.py` MUST:

```python
def run(*args, **kwargs) -> dict:
    """Returns dict. Never raises on expected failures — wraps in error dict."""
    pass
```

Errors:
- Expected failures: `return {"error": "<reason>", "_status": "skipped"}`
- Unexpected failures: raise the original exception (caller logs + handles)

### Logging contract

Every tool wraps its main work in:

```python
from agents.shared.logger import logger

def run(lead_id, ...):
    with logger.action(
        claw="scout",
        action_type="score_website",
        lead_id=lead_id,
    ) as a:
        result = do_the_work()
        a.set_log(f"Scored {url} as {result['score']}/10")
        a.set_result(result)
        return result
```

### Memory append contract

```python
from agents.shared.memory_updater import maybe_update_memory

# At end of heartbeat:
maybe_update_memory(claw_name="scout", heartbeat_summary="...")
```

### Discord post contract

```python
from agents.shared.discord_bridge import post
post(content="🔍 Scout: scraped 20 new leads, 14 qualified.")
```

### Env var access

Always via `os.environ.get` with a default that fails loudly:

```python
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    raise RuntimeError("NVIDIA_API_KEY not set")
```

### NEVER do these

- Direct HTTP calls without retry wrapping
- Logging via print() — use the logger
- Cross-agent imports (e.g., scout importing from pitcher)
- Storing secrets anywhere except .env
- Adding auth to anything
- Optimizing for production scale

---

END OF SPEC
