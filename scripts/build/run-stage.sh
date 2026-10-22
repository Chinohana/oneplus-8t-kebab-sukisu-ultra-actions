#!/usr/bin/env bash
set -Eeuo pipefail
stage="${1:?build stage required}"
case "$stage" in
  baseline-identity|fingerprint|references|patch-preflight|source|patches|audit-hide|audit-susfs|audit-hooks|configure|cache-configure|compile|cache-stats|audit-build|tool|package|raw|provenance) ;;
  *) echo "Unknown build stage: $stage" >&2; exit 2 ;;
esac
export BUILD_ROOT="${BUILD_ROOT:-${GITHUB_WORKSPACE:-$PWD}}"
export BUILD_TEMP="${BUILD_TEMP:-${RUNNER_TEMP:-$BUILD_ROOT/build-temp}}"
export BUILD_ENV="${BUILD_ENV:-${GITHUB_ENV:-$BUILD_TEMP/environment}}"
export BUILD_SUMMARY="${BUILD_SUMMARY:-${GITHUB_STEP_SUMMARY:-$BUILD_TEMP/summary.md}}"
export BUILDER_COMMIT="${BUILDER_COMMIT:-${GITHUB_SHA:-$(git -C "$BUILD_ROOT" rev-parse HEAD)}}"
mkdir -p "$BUILD_TEMP"
cd "$BUILD_ROOT"
source .github/scripts/load-build-pins.sh "$BUILD_ROOT"
if test -f "$BUILD_ENV"; then
  set -a
  # The file is written only by the build stages in this isolated run.
  # shellcheck source=/dev/null
  source "$BUILD_ENV"
  set +a
fi
export PROFILE="${SUSFS_PROFILE:-extended-full}"
if test "$stage" = audit-hide && test "${ENABLE_SELINUX_HIDE:-true}" != true; then exit 0; fi
if test "$stage" = audit-susfs && test "${ENABLE_SUSFS:-true}" != true; then exit 0; fi
bash "scripts/build/stages/$stage.sh"
