#!/usr/bin/env bash
set -euo pipefail

root="${1:-$PWD}"
source "$root/.github/scripts/load-build-pins.sh" "$root"

entry="$(git -C "$root" ls-tree HEAD -- "$KERNEL_PIN_PATH")"
mode="$(awk '{print $1}' <<< "$entry")"
kernel_commit="$(awk '{print $3}' <<< "$entry")"

test "$mode" = 160000
if ! [[ "$kernel_commit" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Invalid kernel gitlink SHA: $kernel_commit" >&2
  exit 1
fi

if test -n "${KERNEL_COMMIT_OVERRIDE:-}"; then
  if ! [[ "$KERNEL_COMMIT_OVERRIDE" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Invalid kernel override SHA: $KERNEL_COMMIT_OVERRIDE" >&2
    exit 1
  fi
  kernel_commit="$KERNEL_COMMIT_OVERRIDE"
fi

export KERNEL_COMMIT="$kernel_commit"
if test -n "${GITHUB_ENV:-}"; then
  printf 'KERNEL_COMMIT=%s\n' "$kernel_commit" >> "$GITHUB_ENV"
fi
printf '%s\n' "$kernel_commit"
