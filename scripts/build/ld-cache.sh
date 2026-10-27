#!/usr/bin/env bash
# Cache the ThinLTO backend only; pass ordinary linker invocations unchanged.
set -euo pipefail
args=("$@")
for ((index=0; index<${#args[@]}; index++)); do
  if test "${args[index]}" = -o && test "${args[index+1]:-}" = vmlinux.o; then
    exec "$REAL_LD" --thinlto-cache-dir="$THINLTO_CACHE_DIR" \
      --thinlto-cache-policy=cache_size_bytes=8g:cache_size=0% \
      --thinlto-jobs="${BUILD_JOBS:-8}" "$@"
  fi
done
exec "$REAL_LD" "$@"
