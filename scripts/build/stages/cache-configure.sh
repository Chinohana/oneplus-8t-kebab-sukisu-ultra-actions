#!/usr/bin/env bash
set -euo pipefail
stages=(baseline)
if test "$ENABLE_SUSFS" = "true"; then
  stages+=("smoke-$CCACHE_HIDE_TAG")
  if test "$PROFILE" != smoke; then
    stages+=("minimal-mount-$CCACHE_HIDE_TAG")
  fi
  if test "$PROFILE" = extended-stat; then
    stages+=("extended-stat-$CCACHE_HIDE_TAG")
  fi
  if test "$PROFILE" = extended-full; then
    stages+=("extended-full-$CCACHE_HIDE_TAG")
  fi
else
  stages+=("selected-$CCACHE_HIDE_TAG")
fi

mkdir -p audit
printf '%s\n' "${stages[@]}" > audit/ccache-stages.txt
for stage in "${stages[@]}"; do
  cache_dir="$BUILD_ROOT/.ccache/$stage"
  mkdir -p "$cache_dir"
  CCACHE_DIR="$cache_dir" ccache --set-config=max_size=800M
  CCACHE_DIR="$cache_dir" ccache --set-config=compression=true
  CCACHE_DIR="$cache_dir" ccache --zero-stats
done
