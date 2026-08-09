#!/usr/bin/env bash
set -euo pipefail

root="${1:-$PWD}"
pins_file="$root/config/build-pins.env"
test -f "$pins_file"

while IFS= read -r line || test -n "$line"; do
  case "$line" in
    ''|'#'*) continue ;;
  esac
  if ! [[ "$line" =~ ^[A-Z][A-Z0-9_]*=[A-Za-z0-9._:/+-]+$ ]]; then
    echo "Invalid build pin line: $line" >&2
    exit 1
  fi
  export "$line"
  if test -n "${GITHUB_ENV:-}"; then
    printf '%s\n' "$line" >> "$GITHUB_ENV"
  fi
done < "$pins_file"
