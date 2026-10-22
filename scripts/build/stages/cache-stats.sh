#!/usr/bin/env bash
set -euo pipefail
mkdir -p audit
{
  echo "## ccache stage statistics"
  echo
} >> "$BUILD_SUMMARY"
while IFS= read -r stage; do
  stats_file="audit/ccache-stats-$stage.txt"
  CCACHE_DIR="$BUILD_ROOT/.ccache/$stage" \
    ccache --show-stats --verbose | tee "$stats_file"
  {
    echo "### $stage"
    echo '```text'
    cat "$stats_file"
    echo '```'
    echo
  } >> "$BUILD_SUMMARY"
done < audit/ccache-stages.txt
