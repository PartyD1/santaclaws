#!/usr/bin/env bash
# Run this INSIDE the NemoClaw sandbox after: nemoclaw mainstreet connect
# It installs dependencies and starts all 5 agents (4 claws + Discord bridge).
set -euo pipefail

WORKSPACE="/workspace/mainstreet"

if [[ ! -d "${WORKSPACE}" ]]; then
  echo "ERROR: ${WORKSPACE} not found — are you inside the mainstreet sandbox?" >&2
  echo "Run: nemoclaw mainstreet connect" >&2
  exit 1
fi

cd "${WORKSPACE}"
echo "Working directory: $(pwd)"
echo

# ── Python environment ────────────────────────────────────────────────────────

PYTHON="${PYTHON:-python3}"

echo "Installing Python dependencies..."
"${PYTHON}" -m pip install -r agents/requirements.txt --quiet
echo "OK: dependencies installed"
echo

# ── .env setup ────────────────────────────────────────────────────────────────

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in SUPABASE_URL, SUPABASE_SERVICE_KEY,"
  echo "APIFY_TOKEN, RESEND_API_KEY, DISCORD_BOT_TOKEN, and DISCORD_APPROVAL_CHANNEL_ID"
  echo "before the agents can run. Then re-run this script."
  exit 0
fi

# ── Preflight check ───────────────────────────────────────────────────────────

echo "Running preflight check..."
"${PYTHON}" -m agents.scripts.preflight_check --skip-live
echo

# ── Start all agents ──────────────────────────────────────────────────────────

echo "Starting all agents (4 claws + Discord bridge) under NemoClaw..."
bash agents/scripts/start_all_claws.sh

echo
echo "All agents started. Monitor with:"
echo "  nemoclaw mainstreet logs --follow    (from host)"
echo "  tail -f logs/all_claws.log           (inside sandbox)"
