#!/usr/bin/env bash
# One-shot NemoClaw setup intended for an NVIDIA Brev (Linux + Docker) instance.
#
# Prerequisites on the instance:
#   - Docker running and usable by the current user (`docker info`).
#   - For NVIDIA Endpoints (default): set NVIDIA_API_KEY before running.
#
# On Brev / SSH workstations, bind the dashboard so forwarded URLs work from your laptop
# (see NemoClaw "NEMOCLAW_DASHBOARD_BIND" in the CLI env reference).
#
# Brev instance name (for your setup): santaclaws — SSH into it, then run this script there.
#
# Usage (on the Brev instance, from a clone of this repo):
#   export NVIDIA_API_KEY="nvapi-..."   # https://build.nvidia.com/settings/api-keys
#   optional: export NEMOCLAW_MODEL="..."  # catalog model id if non-interactive needs it
#   optional: export NEMOCLAW_SANDBOX_NAME="my-sandbox"   # default matches instance: santaclaws
#   ./scripts/brev-nemoclaw-setup.sh
#
# Optional env:
#   SKIP_INSTALL=1          - skip the curl installer (requires `nemoclaw` on PATH), then run onboard
#   NEMOCLAW_PROVIDER       - default: nvidia (also: openai, anthropic, ollama, routed, ...)
#   NEMOCLAW_POLICY_TIER    - default: balanced
#   NEMOCLAW_SANDBOX_READY_TIMEOUT - default: 600 (first image pull can be slow)
#   FORCE_ONBOARD=1         - run `nemoclaw onboard` even after a fresh installer (normally skipped
#                              because the installer already launches onboard once)
#
# Legacy wrapper from an older Brev bootstrap (your laptop, if you still use it):
#   nemoclaw deploy santaclaws
# Prefer: provision the Brev instance, SSH in, run this script.

set -euo pipefail

export NEMOCLAW_DASHBOARD_BIND="${NEMOCLAW_DASHBOARD_BIND:-0.0.0.0}"
export NEMOCLAW_SANDBOX_READY_TIMEOUT="${NEMOCLAW_SANDBOX_READY_TIMEOUT:-600}"
export NEMOCLAW_PROVIDER="${NEMOCLAW_PROVIDER:-nvidia}"
export NEMOCLAW_POLICY_TIER="${NEMOCLAW_POLICY_TIER:-balanced}"
export NEMOCLAW_SANDBOX_NAME="${NEMOCLAW_SANDBOX_NAME:-santaclaws}"

if ! docker info >/dev/null 2>&1; then
  echo "error: Docker is not reachable. Start Docker on this Brev instance and ensure your user can run 'docker info'."
  exit 1
fi

if [[ "${NEMOCLAW_PROVIDER}" == "nvidia" && -z "${NVIDIA_API_KEY:-}" ]]; then
  echo "error: NEMOCLAW_PROVIDER=nvidia requires NVIDIA_API_KEY (see https://build.nvidia.com/settings/api-keys)."
  exit 1
fi

if [[ "${NEMOCLAW_PROVIDER}" == "routed" && -z "${NVIDIA_API_KEY:-}" ]]; then
  echo "error: NEMOCLAW_PROVIDER=routed requires NVIDIA_API_KEY."
  exit 1
fi

_refresh_path_for_nvm() {
  export NVM_DIR="${NVM_DIR:-${HOME}/.nvm}"
  # shellcheck source=/dev/null
  [[ -s "${NVM_DIR}/nvm.sh" ]] && . "${NVM_DIR}/nvm.sh"
  hash -r
}

_refresh_path_for_nvm

had_nemoclaw_cli=0
command -v nemoclaw >/dev/null 2>&1 && had_nemoclaw_cli=1

if [[ "${SKIP_INSTALL:-0}" != "1" ]]; then
  if [[ "${had_nemoclaw_cli}" == "0" ]]; then
    curl -fsSL https://www.nvidia.com/nemoclaw.sh \
      | NEMOCLAW_NON_INTERACTIVE=1 NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE=1 bash
  fi
else
  if [[ "${had_nemoclaw_cli}" == "0" ]]; then
    echo "error: SKIP_INSTALL=1 but 'nemoclaw' is not on PATH."
    exit 1
  fi
fi

_refresh_path_for_nvm

if ! command -v nemoclaw >/dev/null 2>&1; then
  echo "error: 'nemoclaw' not found on PATH after install. Open a new shell or run: source ~/.nvm/nvm.sh"
  exit 1
fi

export NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE="${NEMOCLAW_ACCEPT_THIRD_PARTY_SOFTWARE:-1}"
export NEMOCLAW_YES="${NEMOCLAW_YES:-1}"

# The piped installer already runs `nemoclaw onboard` on success; avoid running it twice on first boot.
if [[ "${had_nemoclaw_cli}" == "1" || "${FORCE_ONBOARD:-0}" == "1" ]]; then
  exec nemoclaw onboard --non-interactive --yes-i-accept-third-party-software
fi

echo "Installer finished. The first-time setup should have run onboard already."
echo "Check: nemoclaw list"
echo "If onboarding did not finish, run: FORCE_ONBOARD=1 ${0}"
