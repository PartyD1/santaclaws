#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Mainstreet NemoClaw onboarding checklist"
echo "repo: ${ROOT_DIR}"

require_command() {
  local name="$1"
  if command -v "${name}" >/dev/null 2>&1; then
    echo "OK: ${name} found"
  else
    echo "WARN: ${name} is not installed or not on PATH"
  fi
}

if command -v python >/dev/null 2>&1; then
  echo "OK: python found"
elif command -v python3 >/dev/null 2>&1; then
  echo "OK: python3 found"
else
  echo "WARN: python/python3 is not installed or not on PATH"
fi
require_command npm
require_command git
require_command nemoclaw

echo
echo "Task 0 NemoClaw setup:"
echo "1. Install/login to NemoClaw or Brev runtime if 'nemoclaw' is missing above."
echo "2. Run: nemoclaw onboard --sandbox mainstreet"
echo "3. Run: nemoclaw mainstreet status"
echo "4. Run: nemoclaw mainstreet connect"
echo "5. Mount/sync this repo at: /workspace/mainstreet"
echo "6. Set env vars from .env.example inside the sandbox."
echo "7. Allow egress domains listed in nemoclaw/network-policy.md."
echo "8. Verify Nemotron routing from nemoclaw/model-routing.md."
echo
echo "Inside the sandbox, run smoke tests:"
echo "  python3 -m agents.shared.nemotron_client"
echo "  python3 -m agents.scripts.preflight_check --skip-live"
echo "  python3 -m agents.scripts.preflight_check"
echo "  python3 -m agents.scripts.rate_limit_check --nemotron-rounds 3 --skip-apify"
