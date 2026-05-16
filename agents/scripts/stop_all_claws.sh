#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"

stop_claw() {
  local claw="$1"
  local pid_file="${LOG_DIR}/${claw}.pid"

  if [[ ! -f "${pid_file}" ]]; then
    echo "${claw} not running: no PID file"
    return
  fi

  local pid
  pid="$(cat "${pid_file}")"
  if [[ -z "${pid}" ]]; then
    rm -f "${pid_file}"
    echo "${claw} PID file was empty; removed it"
    return
  fi

  if kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}" 2>/dev/null || true
    sleep 1
    if kill -0 "${pid}" 2>/dev/null; then
      kill -TERM "${pid}" 2>/dev/null || true
    fi
    echo "stopped ${claw} PID ${pid}"
  else
    echo "${claw} PID ${pid} was not running"
  fi
  rm -f "${pid_file}"
}

stop_claw "scout"
stop_claw "designer"
stop_claw "pitcher"
stop_claw "closer"

echo "NemoClaw claw stop complete."
