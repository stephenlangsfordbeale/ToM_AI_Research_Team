#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
stamp="${TOM_RUN_STAMP:-$(date +%Y%m%d-%H%M%S)}"

export TOM_INCUMBENT_FAMILY="${TOM_INCUMBENT_FAMILY:-auxhead-lite-v2-local800}"
export TOM_REMOTE_OUTPUT_FAMILY="${TOM_REMOTE_OUTPUT_FAMILY:-auxhead-lite}"
export TOM_MODAL_APP_NAME="${TOM_MODAL_APP_NAME:-tom-previous-v2-duplicate-$stamp}"
export TOM_MODAL_VOLUME_NAME="${TOM_MODAL_VOLUME_NAME:-tom-previous-v2-duplicate-$stamp}"

cd "$repo_root"

printf 'Launching previous V2 duplicate\n'
printf '  repo: %s\n' "$repo_root"
printf '  app_name: %s\n' "$TOM_MODAL_APP_NAME"
printf '  volume_name: %s\n' "$TOM_MODAL_VOLUME_NAME"

exec modal run scripts/modal_auxhead_lite_runner.py "$@"
