#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PYTHON_BIN="${PYTHON_BIN:-python}"

mkdir -p "${LOG_DIR}"
cd "${ROOT_DIR}"

start_claw() {
  local claw="$1"
  local module="$2"
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

  nohup "${PYTHON_BIN}" -m "${module}" >"${log_file}" 2>&1 &
  local pid="$!"
  echo "${pid}" >"${pid_file}"
  echo "started ${claw} PID ${pid}; log ${log_file}"
}

start_claw "scout" "agents.scout.claw"
start_claw "designer" "agents.designer.claw"
start_claw "pitcher" "agents.pitcher.claw"
start_claw "closer" "agents.closer.claw"

echo "NemoClaw claws are running. PID files live in ${LOG_DIR}."
