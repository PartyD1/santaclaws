#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PYTHON_BIN="${PYTHON_BIN:-python}"

mkdir -p "${LOG_DIR}"
cd "${ROOT_DIR}"

# Single-process mode: run all agents under one openclaw_run all process.
# Set USE_OPENCLAW_ALL=false to fall back to per-claw nohup processes.
USE_OPENCLAW_ALL="${USE_OPENCLAW_ALL:-true}"

if [[ "${USE_OPENCLAW_ALL}" == "true" ]]; then
  pid_file="${LOG_DIR}/all_claws.pid"
  log_file="${LOG_DIR}/all_claws.log"

  if [[ -f "${pid_file}" ]]; then
    old_pid="$(cat "${pid_file}")"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
      echo "All claws already running with PID ${old_pid}"
      exit 0
    fi
  fi

  nohup "${PYTHON_BIN}" -u -m agents.scripts.openclaw_run all >"${log_file}" 2>&1 &
  pid="$!"
  echo "${pid}" >"${pid_file}"
  echo "Started all agents (PID ${pid}); log ${log_file}"
  exit 0
fi

# Per-claw fallback: each claw gets its own nohup process and PID file.
start_claw() {
  local claw="$1"
  local pid_file="${LOG_DIR}/${claw}.pid"
  local log_file="${LOG_DIR}/${claw}.log"

  if [[ -f "${pid_file}" ]]; then
    local old_pid
    old_pid="$(cat "${pid_file}")"
    if [[ -n "${old_pid}" ]] && kill -0 "${old_pid}" 2>/dev/null; then
      echo "${claw} already running with PID ${old_pid}"
      return
    fi
  fi

  nohup "${PYTHON_BIN}" -u -m agents.scripts.openclaw_run "${claw}" >"${log_file}" 2>&1 &
  local pid="$!"
  echo "${pid}" >"${pid_file}"
  echo "started ${claw} PID ${pid}; log ${log_file}"
}

start_claw "scout"
start_claw "designer"
start_claw "pitcher"
start_claw "closer"

echo "NemoClaw claws are running. PID files live in ${LOG_DIR}."
