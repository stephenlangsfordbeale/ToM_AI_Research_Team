#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/tom_paths.sh
source "$script_dir/tom_paths.sh"

REPO_ROOT="$TOM_REPO_ROOT"
NOTES_FILE="${TOMX_NOTES_FILE:-$REPO_ROOT/logs/key-chat-excerpts.md}"
TIMESTAMP_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

ensure_notes_file() {
  mkdir -p "$(dirname "$NOTES_FILE")"
  if [[ ! -f "$NOTES_FILE" ]]; then
    cat >"$NOTES_FILE" <<'EOF'
# Key Chat Excerpts

Quick-capture notes from terminal/chat sessions.

EOF
  fi
}

append_clipboard() {
  local title="${1:-Clipboard capture}"
  local clip
  clip="$(pbpaste 2>/dev/null || true)"
  if [[ -z "${clip//[[:space:]]/}" ]]; then
    echo "Clipboard looks empty. Copy text first, then retry."
    return 1
  fi
  {
    echo
    echo "## ${TIMESTAMP_UTC} — ${title}"
    echo
    echo '```text'
    printf '%s\n' "$clip"
    echo '```'
  } >>"$NOTES_FILE"
  echo "Saved clipboard excerpt -> $NOTES_FILE"
}

append_typed_note() {
  echo "Enter your note. Finish with Ctrl-D on a new line:"
  local tmp_file
  tmp_file="$(mktemp)"
  if ! cat >"$tmp_file"; then
    rm -f "$tmp_file"
    echo "Note capture cancelled."
    return 1
  fi

  if [[ ! -s "$tmp_file" ]]; then
    rm -f "$tmp_file"
    echo "No note captured."
    return 1
  fi

  {
    echo
    echo "## ${TIMESTAMP_UTC} — Manual note"
    echo
    cat "$tmp_file"
  } >>"$NOTES_FILE"
  rm -f "$tmp_file"
  echo "Saved manual note -> $NOTES_FILE"
}

open_notes() {
  ensure_notes_file
  if command -v cursor >/dev/null 2>&1; then
    cursor "$NOTES_FILE" >/dev/null 2>&1 || true
    echo "Opened in Cursor: $NOTES_FILE"
    return 0
  fi
  if [[ "$(uname -s)" == "Darwin" ]] && open -a "Cursor" "$NOTES_FILE" >/dev/null 2>&1; then
    echo "Opened in Cursor: $NOTES_FILE"
    return 0
  fi
  echo "Cursor CLI not found. File path:"
  echo "  $NOTES_FILE"
  return 1
}

show_recent() {
  ensure_notes_file
  echo "----- Recent notes ($NOTES_FILE) -----"
  local note_lines
  note_lines="$(grep -cve '^[[:space:]]*$' "$NOTES_FILE" 2>/dev/null || echo 0)"
  if [[ "$note_lines" -le 3 ]]; then
    echo "(no notes yet — use option 4 or 5 to capture)"
  else
    tail -n 60 "$NOTES_FILE" || true
  fi
  echo "-------------------------------------"
}

run_mode_script() {
  local cmd="$1"
  if [[ ! -x "$cmd" ]]; then
    echo "Command not found or not executable: $cmd"
    return 1
  fi
  "$cmd"
}

show_modal_status() {
  local status_cmd="$REPO_ROOT/tom-modal-status"
  local volume_override="${1:-}"

  if [[ ! -x "$status_cmd" ]]; then
    echo "Modal status command not found or not executable: $status_cmd"
    return 1
  fi

  if [[ -n "${volume_override// }" ]]; then
    "$status_cmd" --volume "$volume_override"
  else
    "$status_cmd"
  fi
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0")                    # open interactive menu
  $(basename "$0") --results            # Results Mode (tom-demo)
  $(basename "$0") --test [args...]     # Test Mode (tom-test)
  $(basename "$0") --learn [args...]    # Learning Mode (tom-learn)
  $(basename "$0") --append-clipboard [title]
  $(basename "$0") --append-note "text"
  $(basename "$0") --show
  $(basename "$0") --open
  $(basename "$0") --modal-status [volume-name]
EOF
}

main_menu() {
  while true; do
    cat <<'EOF'

🧭 ToM CLI — three demo modes
  1) Results Mode   — show 5-seed promotion summary (tom-demo)
  2) Test Mode      — local runner + promotion gate (tom-test)
  3) Learning Mode  — OMX agent dashboard (tom-learn)

Utilities
  4) Save current clipboard excerpt
  5) Write a manual note
  6) Show recent notes
  7) Open notes in Cursor
  8) Check Modal run status
  0) Exit
EOF
    read -r -p "Choose [0-8]: " choice
    case "$choice" in
      1) run_mode_script "$REPO_ROOT/tom-demo" ;;
      2)
        read -r -p "Train episodes [5]: " episodes
        read -r -p "Seed [7]: " seed
        episodes="${episodes:-5}"
        seed="${seed:-7}"
        run_mode_script "$REPO_ROOT/tom-test" --train-episodes "$episodes" --seed "$seed"
        ;;
      3) run_mode_script "$REPO_ROOT/tom-learn" ;;
      4) append_clipboard "Clipboard capture" ;;
      5) append_typed_note ;;
      6) show_recent ;;
      7) open_notes ;;
      8)
        read -r -p "Volume override (Enter for auto-detect): " volume_override
        show_modal_status "$volume_override"
        ;;
      0) break ;;
      *) echo "Invalid choice. Pick 0-8." ;;
    esac
  done
}

ensure_notes_file

case "${1:-}" in
  --results)
    run_mode_script "$REPO_ROOT/tom-demo" "${@:2}"
    ;;
  --test)
    run_mode_script "$REPO_ROOT/tom-test" "${@:2}"
    ;;
  --learn)
    run_mode_script "$REPO_ROOT/tom-learn" "${@:2}"
    ;;
  --append-clipboard)
    append_clipboard "${2:-Clipboard capture}"
    ;;
  --append-note)
    note="${2:-}"
    if [[ -z "${note// }" ]]; then
      echo "Missing note text."
      exit 1
    fi
    {
      echo
      echo "## ${TIMESTAMP_UTC} — Manual note"
      echo
      printf '%s\n' "$note"
    } >>"$NOTES_FILE"
    echo "Saved manual note -> $NOTES_FILE"
    ;;
  --show)
    show_recent
    ;;
  --open)
    open_notes
    ;;
  --modal-status)
    show_modal_status "${2:-}"
    ;;
  --v6-status|--v5-status)
    show_modal_status "${2:-}"
    ;;
  -h|--help)
    usage
    ;;
  "")
    main_menu
    ;;
  *)
    usage
    exit 1
    ;;
esac
