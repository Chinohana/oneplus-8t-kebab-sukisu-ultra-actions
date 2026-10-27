#!/usr/bin/env bash
set -euo pipefail
stages=("selected-$PROFILE-$CCACHE_HIDE_TAG")

mkdir -p audit
printf '%s\n' "${stages[@]}" > audit/ccache-stages.txt
for stage in "${stages[@]}"; do
  cache_dir="$BUILD_ROOT/.ccache/$stage"
  mkdir -p "$cache_dir"
  CCACHE_DIR="$cache_dir" ccache --set-config=max_size=800M
  CCACHE_DIR="$cache_dir" ccache --set-config=compression=true
  CCACHE_DIR="$cache_dir" ccache --zero-stats
done
