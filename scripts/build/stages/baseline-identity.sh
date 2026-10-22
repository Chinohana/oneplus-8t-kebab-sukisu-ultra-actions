#!/usr/bin/env bash
set -euo pipefail
git fetch --no-tags --depth=1 origin "$BUILDER_BASE_COMMIT"
git show "${BUILDER_BASE_COMMIT}:.github/workflows/build-sukisu.yml" \
  > "$BUILD_TEMP/original-build-sukisu.yml"
test "$(sha256sum "$BUILD_TEMP/original-build-sukisu.yml" | awk '{print $1}')" = "$ORIGINAL_WORKFLOW_SHA256"
