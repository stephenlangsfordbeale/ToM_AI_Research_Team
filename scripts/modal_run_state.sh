#!/usr/bin/env bash
# Record and resolve the active or most recently used Modal runner lane.

modal_run_state_path() {
  printf '%s\n' "${TOM_MODAL_RUN_STATE:-$TOM_REPO_ROOT/.omx/state/modal-run-state.json}"
}

modal_run_state_record() {
  local launcher="$1"
  local runner_version="$2"
  local volume_name="$3"
  local output_family="$4"
  local seeds_csv="${5:-7,11,23}"
  local app_name="${6:-}"
  local target_total_episodes="${7:-140000}"

  local state_path
  state_path="$(modal_run_state_path)"
  mkdir -p "$(dirname "$state_path")"

  python3 - "$state_path" "$launcher" "$runner_version" "$volume_name" "$output_family" "$seeds_csv" "$app_name" "$target_total_episodes" "$$" <<'PY'
import json, sys
from datetime import datetime, timezone
from pathlib import Path

path, launcher, runner_version, volume, output_family, seeds, app_name, target_eps, pid = sys.argv[1:10]
payload = {
    "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "launcher": launcher,
    "runner_version": runner_version,
    "volume_name": volume,
    "output_family": output_family,
    "seeds_csv": seeds,
    "app_name": app_name,
    "target_total_episodes": int(target_eps) if str(target_eps).isdigit() else target_eps,
    "pid": int(pid),
}
Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

modal_run_state_read() {
  local state_path
  state_path="$(modal_run_state_path)"
  [[ -f "$state_path" ]] || return 1
  python3 - "$state_path" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    obj = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    raise SystemExit(1)
if not isinstance(obj, dict):
    raise SystemExit(1)
for key in ("runner_version", "volume_name", "output_family", "seeds_csv"):
    value = obj.get(key)
    if value is None:
        raise SystemExit(1)
    print(f"{key}={value}")
for key in ("launcher", "app_name", "updated_at_utc", "pid", "target_total_episodes"):
    value = obj.get(key, "")
    print(f"{key}={value}")
PY
}

_modal_pid_alive() {
  local pid="${1:-}"
  [[ -n "$pid" ]] || return 1
  kill -0 "$pid" 2>/dev/null
}

_modal_runner_running_version() {
  if pgrep -fl "scripts/modal_v6_runner.py" >/dev/null 2>&1; then
    printf 'v6\n'
    return 0
  fi
  if pgrep -fl "scripts/modal_v5_runner.py" >/dev/null 2>&1; then
    printf 'v5\n'
    return 0
  fi
  return 1
}

modal_run_state_resolve() {
  # Prefer a currently running Modal runner in this repo.
  local running_version=""
  if running_version="$(_modal_runner_running_version)"; then
    printf 'source=running\n'
    printf 'runner_version=%s\n' "$running_version"
    if [[ -f "$(modal_run_state_path)" ]]; then
      local saved_version saved_pid
      saved_version="$(modal_run_state_read 2>/dev/null | awk -F= '/^runner_version=/{print $2}' || true)"
      saved_pid="$(modal_run_state_read 2>/dev/null | awk -F= '/^pid=/{print $2}' || true)"
      if [[ "$saved_version" == "$running_version" ]] && _modal_pid_alive "$saved_pid"; then
        modal_run_state_read
        return 0
      fi
    fi
    if [[ "$running_version" == "v6" ]]; then
      printf 'launcher=%s\n' "${TOM_V6_LAUNCHER:-unknown}"
      printf 'volume_name=%s\n' "${TOM_V6_MODAL_VOLUME_NAME:-tom-v6-omx-full2-runs}"
      printf 'output_family=%s\n' "${TOM_V6_REMOTE_OUTPUT_FAMILY:-v6-omx-full2-promo-candidate}"
      printf 'seeds_csv=%s\n' "${TOM_V6_SEEDS_CSV:-7,11,23}"
      printf 'target_total_episodes=%s\n' "${TOM_V6_TARGET_TOTAL_EPISODES:-140000}"
      printf 'app_name=%s\n' "${TOM_V6_MODAL_APP_NAME:-}"
      printf 'updated_at_utc=\n'
      printf 'pid=\n'
      return 0
    fi
    printf 'launcher=%s\n' "${TOM_V5_LAUNCHER:-unknown}"
    printf 'volume_name=%s\n' "${TOM_V5_MODAL_VOLUME_NAME:-tom-v5-delayedtrust-runs}"
    printf 'output_family=%s\n' "${TOM_V5_REMOTE_OUTPUT_FAMILY:-v5-delayedtrust-split-candidate}"
    printf 'seeds_csv=%s\n' "${TOM_V5_SEEDS_CSV:-7,11,23}"
    printf 'target_total_episodes=%s\n' "${TOM_V5_TARGET_TOTAL_EPISODES:-140000}"
    printf 'app_name=%s\n' "${TOM_V5_MODAL_APP_NAME:-}"
    printf 'updated_at_utc=\n'
    printf 'pid=\n'
    return 0
  fi

  # Fall back to the last recorded launcher invocation.
  if [[ -f "$(modal_run_state_path)" ]]; then
    printf 'source=last_used\n'
    modal_run_state_read
    return 0
  fi

  # Default lane when nothing has been recorded yet.
  printf 'source=default\n'
  printf 'runner_version=v6\n'
  printf 'launcher=tom-run-v6\n'
  printf 'volume_name=%s\n' "${TOM_V6_MODAL_VOLUME_NAME:-tom-v6-omx-full2-runs}"
  printf 'output_family=%s\n' "${TOM_V6_REMOTE_OUTPUT_FAMILY:-v6-omx-full2-promo-candidate}"
  printf 'seeds_csv=%s\n' "${TOM_V6_SEEDS_CSV:-7,11,23}"
  printf 'target_total_episodes=%s\n' "${TOM_V6_TARGET_TOTAL_EPISODES:-140000}"
  printf 'app_name=%s\n' "${TOM_V6_MODAL_APP_NAME:-}"
  printf 'updated_at_utc=\n'
  printf 'pid=\n'
}
