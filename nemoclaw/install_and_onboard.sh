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

require_command python
require_command npm
require_command git

echo
echo "Manual NemoClaw setup still required:"
echo "1. Install/login to NemoClaw or Brev runtime."
echo "2. Create/open sandbox: mainstreet."
echo "3. Mount this repo at the workspace path from .env.example."
echo "4. Allow egress domains listed in nemoclaw/network-policy.md."
echo "5. Verify Nemotron routing from nemoclaw/model-routing.md."
echo
echo "After setup, run:"
echo "  python -m agents.shared.nemotron_client"
echo "  python -m agents.scripts.rate_limit_check --skip-apify"
echo "  bash agents/scripts/start_all_claws.sh"
