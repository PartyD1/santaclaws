# Mainstreet NemoClaw Demo Runbook

## Goal

Show four NemoClaw claws running on heartbeats, coordinated through Supabase, using Nemotron for scoring, generation, critique, outreach, reply classification, and memory updates.

## Preflight

- Confirm `.env` has Supabase, Nemotron, Apify, Discord, Resend, Vercel or Supabase Storage, and Google Calendar values.
- For the Vapi stretch, also confirm `VAPI_API_KEY`, `VAPI_PHONE_NUMBER`, and `VAPI_WEBHOOK_URL`; otherwise leave voice disabled.
- Run `python -m agents.scripts.seed_demo_data` if the dashboard needs fallback rows.
- Start the dashboard from `dashboard/` with `npm.cmd run dev`.
- Start claws from repo root with `bash agents/scripts/start_all_claws.sh`.
- Open dashboard, Discord approval channel, Supabase table view, and Google Calendar.
- Keep `logs/scout.log`, `logs/designer.log`, `logs/pitcher.log`, and `logs/closer.log` visible or easy to tail.

## Monitor Checklist

- Every 5 minutes, confirm all PID files exist in `logs/`.
- Check each claw log for fresh heartbeat output.
- Confirm dashboard activity feed is receiving `actions` rows.
- Watch Supabase counts for leads, generated sites, outreach, inbound, and meetings.
- Confirm Discord is not rate-limiting approval or heartbeat summaries.
- If Nemotron errors repeat, increase heartbeat intervals or stop Designer first.
- If Apify runs hot, set `SCOUT_SCRAPE_LIMIT=5` or stop Scout after enough leads.
- If Resend is not ready, keep Pitcher in draft/approval mode and do not send live email.

## Live Demo Path

1. Show the dashboard metrics and four claw cards.
2. Open a lead detail page with generated mockups.
3. Point out Designer self-critique: score, issues, iteration count, and chosen winner.
4. Show Pitcher outreach with the winning email angle and runner-up variants if visible in Supabase.
5. Send or reveal an inbound reply.
6. Run or wait for Closer heartbeat.
7. Show classification, drafted reply, proposed times, and booked/demo meeting.
8. End on the action feed as the audit trail of Nemotron-powered decisions.

## Commands

```bash
python -m agents.scripts.seed_demo_data
bash agents/scripts/start_all_claws.sh
bash agents/scripts/stop_all_claws.sh
```

```powershell
cd dashboard
npm.cmd run dev
```

## What To Say

- "These are four NemoClaw claws, each with its own SOUL and MEMORY, running independently."
- "Supabase is the shared memory and work queue. There is no hidden message bus."
- "Nemotron is used for the judgment-heavy steps: pain extraction, mockup generation, critique, outreach selection, reply classification, and memory updates."
- "The action feed is the transparency layer: every important decision becomes a row."

## If Something Fails Live

- If dashboard is empty, run `python -m agents.scripts.seed_demo_data` and refresh.
- If claws are quiet, show existing action rows and logs, then restart with `start_all_claws.sh`.
- If Nemotron is unavailable, show fallback seed data and explain the failed memory/generation logs.
- If Resend or Calendar fails, show the draft/meeting rows that would be sent/booked.
- If Vapi fails, continue with email inbound and mention voice is the stretch path.
