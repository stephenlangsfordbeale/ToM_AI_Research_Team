#!/usr/bin/env bash
# Shared path defaults for ToM CLI launchers.
# Override with environment variables when needed.

tom_resolve_repo_root() {
  if [[ -n "${TOM_REPO_ROOT:-}" ]]; then
    printf '%s\n' "$TOM_REPO_ROOT"
    return 0
  fi
  if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    printf '%s\n' "$git_root"
    return 0
  fi
  printf '%s\n' "/Users/stephenbeale/Projects/ToM_AI_Research_Team"
}

export TOM_REPO_ROOT="${TOM_REPO_ROOT:-$(tom_resolve_repo_root)}"
export TOM_AUTORESEARCH_ROOT="${TOM_AUTORESEARCH_ROOT:-/Users/stephenbeale/Projects/autoresearch-macos-tomx}"
export TOM_DEMO_SUMMARY="${TOM_DEMO_SUMMARY:-$TOM_REPO_ROOT/logs/omx_full_2_5seed_summary.md}"
export TOM_DEMO_INCUMBENT_NOTE="${TOM_DEMO_INCUMBENT_NOTE:-$TOM_REPO_ROOT/incumbents/ToM_experiment_incumbent/auxhead-clear/INCUMBENT_NOTE.md}"
export TOM_LOGS_MODAL_ROOT="${TOM_LOGS_MODAL_ROOT:-$TOM_REPO_ROOT/logs/modal}"
export TOM_MODAL_WARMSTART_ROOT="${TOM_MODAL_WARMSTART_ROOT:-$TOM_REPO_ROOT/modal/tom-experiment-incumbent}"
export TOM_MODAL_ARCHIVE_ROOT="${TOM_MODAL_ARCHIVE_ROOT:-$TOM_REPO_ROOT/archive/modal}"
export TOM_CAMPAIGN_INDEX="${TOM_CAMPAIGN_INDEX:-$TOM_REPO_ROOT/docs/CAMPAIGN_INDEX.md}"
