#!/usr/bin/env bash
# Creates the `mainstreet` NemoClaw sandbox and verifies it is ready.
# Run from the repo root: bash nemoclaw/install_and_onboard.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Mainstreet NemoClaw onboarding"
echo "repo: ${ROOT_DIR}"
echo

# ── Prerequisite checks ────────────────────────────────────────────────────────

require_command() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    echo "OK: ${name}"
  else
    echo "MISSING: ${name} — install it before continuing" >&2
    exit 1
  fi
}

if command -v python >/dev/null 2>&1; then
  echo "OK: python"
elif command -v python3 >/dev/null 2>&1; then
  echo "OK: python3"
else
  echo "MISSING: python/python3" >&2
  exit 1
fi
require_command git
require_command nemoclaw

echo

# ── Create sandbox if it doesn't exist ────────────────────────────────────────

if nemoclaw list 2>/dev/null | grep -q "mainstreet"; then
  echo "Sandbox 'mainstreet' already exists."
else
  echo "Sandbox 'mainstreet' does not exist yet."
  echo
  echo "Run this command interactively in your terminal and follow the prompts"
  echo "(choose option 1 — NVIDIA Endpoints):"
  echo
  echo "  nemoclaw onboard --name mainstreet --yes-i-accept-third-party-software"
  echo
  echo "Once it completes, re-run this script to add policies and verify:"
  echo "  bash nemoclaw/install_and_onboard.sh"
  exit 0
fi

echo

# ── Network policies ──────────────────────────────────────────────────────────

echo "Adding network policies..."
nemoclaw mainstreet policy-add discord    || echo "WARN: discord policy-add failed (may already be set)"

echo
echo "Note: Supabase, Apify, Resend, Vercel, and Google APIs may require"
echo "additional policy-add steps. See nemoclaw/network-policy.md for the"
echo "required egress domains."
echo

# ── Status check ──────────────────────────────────────────────────────────────

echo "Sandbox status:"
nemoclaw mainstreet status

echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Sandbox ready. Next steps:"
echo
echo "  # 1. Connect into the sandbox"
echo "  nemoclaw mainstreet connect"
echo
echo "  # 2. Inside the sandbox, install deps and start all 5 agents:"
echo "  bash /workspace/mainstreet/nemoclaw/start_inside_sandbox.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
