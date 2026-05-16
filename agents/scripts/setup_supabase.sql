-- Mainstreet Supabase schema.
-- Task 3 applies this in the Supabase SQL editor.

create extension if not exists pgcrypto;

create table if not exists leads (
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
  website_score int,
  website_score_reasons text[],
  qualification_status text not null default 'pending',
  qualification_reason text,
  worked_by_designer boolean default false,
  worked_by_pitcher boolean default false,
  do_not_contact boolean default false,
  scraped_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_leads_qual_status on leads(qualification_status);
create index if not exists idx_leads_designer_queue on leads(qualification_status, worked_by_designer)
  where worked_by_designer = false;
create index if not exists idx_leads_pitcher_queue on leads(worked_by_designer, worked_by_pitcher)
  where worked_by_designer = true and worked_by_pitcher = false;
create index if not exists idx_leads_dedup on leads(business_name, address);

create table if not exists actions (
  id uuid primary key default gen_random_uuid(),
  claw_name text not null,
  lead_id uuid references leads(id),
  action_type text not null,
  status text not null,
  started_at timestamptz default now(),
  finished_at timestamptz,
  result_json jsonb,
  human_readable_log text not null
);

create index if not exists idx_actions_recent on actions(started_at desc);
create index if not exists idx_actions_lead on actions(lead_id);
create index if not exists idx_actions_claw on actions(claw_name, started_at desc);

create table if not exists generated_sites (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) not null,
  variant text not null,
  vercel_url text,
  storage_url text,
  html_content text not null,
  self_critique_score numeric,
  self_critique_iterations int default 1,
  critique_issues text[],
  is_chosen_winner boolean default false,
  pick_reasoning text,
  generated_at timestamptz default now()
);

create index if not exists idx_generated_sites_lead on generated_sites(lead_id);
create index if not exists idx_generated_sites_winner on generated_sites(lead_id)
  where is_chosen_winner = true;

create table if not exists outreach (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) not null,
  to_address text,
  angle text not null,
  subject text not null,
  body text not null,
  critique_score numeric,
  runner_up_variants jsonb,
  status text not null default 'pending_approval',
  drafted_at timestamptz default now(),
  approved_at timestamptz,
  sent_at timestamptz,
  resend_message_id text
);

create index if not exists idx_outreach_status on outreach(status);
create index if not exists idx_outreach_lead on outreach(lead_id);

create table if not exists inbound (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id),
  channel text not null,
  raw_content text not null,
  transcript text,
  from_address text,
  classification text,
  classification_confidence int,
  classification_key_phrase text,
  received_at timestamptz default now(),
  handled_at timestamptz,
  handled_by text
);

create index if not exists idx_inbound_unhandled on inbound(received_at)
  where handled_at is null;
create index if not exists idx_inbound_lead on inbound(lead_id);

create table if not exists meetings (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid references leads(id) not null,
  inbound_id uuid references inbound(id),
  scheduled_for timestamptz not null,
  google_event_id text,
  status text not null default 'booked',
  attendee_email text,
  booked_at timestamptz default now()
);

create index if not exists idx_meetings_lead on meetings(lead_id);
create index if not exists idx_meetings_scheduled on meetings(scheduled_for);

create table if not exists approvals (
  id uuid primary key default gen_random_uuid(),
  target_type text not null,
  target_id uuid not null,
  decision text,
  edit_payload jsonb,
  requested_at timestamptz default now(),
  decided_at timestamptz,
  decided_by text
);

create index if not exists idx_approvals_pending on approvals(target_type, target_id)
  where decided_at is null;

create table if not exists config (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz default now()
);

create table if not exists agent_memory (
  id uuid primary key default gen_random_uuid(),
  claw_name text not null,
  pattern text not null,
  source text not null default 'nemotron',
  heartbeat_summary jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_agent_memory_claw_recent on agent_memory(claw_name, created_at desc);

insert into config (key, value) values
  ('target', '{"niches": ["restaurants", "cafes", "hair salons", "barbers", "fitness centers", "spas", "house cleaners", "contractors"], "city": "Santa Cruz", "state": "CA"}'),
  ('autonomous_mode', 'false'),
  ('ignore_quiet_hours', 'true'),
  ('session_lead_cap', '500')
on conflict (key) do nothing;

alter publication supabase_realtime add table leads;
alter publication supabase_realtime add table actions;
alter publication supabase_realtime add table generated_sites;
alter publication supabase_realtime add table outreach;
alter publication supabase_realtime add table inbound;
alter publication supabase_realtime add table meetings;
alter publication supabase_realtime add table approvals;
