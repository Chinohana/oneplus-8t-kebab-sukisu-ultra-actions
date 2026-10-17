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
  # Intentionally export the validated KEY=VALUE assignment.
  # shellcheck disable=SC2163
  export "$line"
  if test -n "${GITHUB_ENV:-}"; then
    printf '%s\n' "$line" >> "$GITHUB_ENV"
  fi
done < "$pins_file"

# ROM, API, branch and bookmark form one target; never mix platform inputs.
case "$ROM_VERSION:$ANDROID_API:$KERNEL_BRANCH:$KERNEL_PIN_PATH" in
  23.2:36:lineage-23.2:pins/kernel-lineage-23.2|\
  24.0:37:lineage-24.0:pins/kernel-lineage-24.0) ;;
  *) echo "Unsupported or inconsistent target platform" >&2; exit 1 ;;
esac
