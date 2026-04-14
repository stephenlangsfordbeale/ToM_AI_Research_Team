#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT_DEFAULT="/Users/stephenbeale/Projects/ToM_AI_Research_Team"
if git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  REPO_ROOT="$git_root"
else
  REPO_ROOT="$REPO_ROOT_DEFAULT"
fi

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
  if [[ -z "${clip// }" ]]; then
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
  cat >"$tmp_file"

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
  if command -v code >/dev/null 2>&1; then
    code "$NOTES_FILE" >/dev/null 2>&1 || true
    echo "Opened in VS Code: $NOTES_FILE"
  else
    echo "VS Code CLI (code) not found. File path:"
    echo "  $NOTES_FILE"
  fi
}

show_recent() {
  echo "----- Recent notes -----"
  tail -n 60 "$NOTES_FILE" || true
  echo "------------------------"
}

usage() {
  cat <<EOF
Usage:
  $(basename "$0")                 # open interactive menu
  $(basename "$0") --append-clipboard [title]
  $(basename "$0") --append-note "text"
  $(basename "$0") --show
  $(basename "$0") --open
  $(basename "$0") --v6-status [volume-name]
  $(basename "$0") --v5-status [volume-name]
EOF
}

show_v6_status() {
  local status_cmd="$REPO_ROOT/tom-v6-status"
  local volume_override="${1:-}"

  if [[ ! -x "$status_cmd" ]]; then
    echo "v6 status command not found or not executable: $status_cmd"
    return 1
  fi

  if [[ -n "${volume_override// }" ]]; then
    "$status_cmd" --volume "$volume_override"
  else
    "$status_cmd"
  fi
}

show_v5_status() {
  local status_cmd="$REPO_ROOT/tom-v5-status"
  local volume_override="${1:-}"

  if [[ ! -x "$status_cmd" ]]; then
    echo "v5 status command not found or not executable: $status_cmd"
    return 1
  fi

  if [[ -n "${volume_override// }" ]]; then
    "$status_cmd" --volume "$volume_override"
  else
    "$status_cmd"
  fi
}

main_menu() {
  while true; do
    cat <<'EOF'

🧭 ToM Superb Menu
  1) Save current clipboard excerpt
  2) Save current clipboard excerpt (with title)
  3) Write a manual note
  4) Show recent notes
  5) Open notes in VS Code
  6) Check Modal v6 run status
  7) Check Modal v5 run status
  0) Exit
EOF
    read -r -p "Choose [0-7]: " choice
    case "$choice" in
      1) append_clipboard "Clipboard capture" ;;
      2)
        read -r -p "Title: " title
        append_clipboard "${title:-Clipboard capture}"
        ;;
      3) append_typed_note ;;
      4) show_recent ;;
      5) open_notes ;;
      6)
        read -r -p "Volume override (Enter for default): " volume_override
        show_v6_status "$volume_override"
        ;;
      7)
        read -r -p "Volume override (Enter for default): " volume_override
        show_v5_status "$volume_override"
        ;;
      0) break ;;
      *) echo "Invalid choice. Pick 0-7." ;;
    esac
  done
}

ensure_notes_file

case "${1:-}" in
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
  --v6-status)
    show_v6_status "${2:-}"
    ;;
  --v5-status)
    show_v5_status "${2:-}"
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
