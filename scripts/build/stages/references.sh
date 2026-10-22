#!/usr/bin/env bash
set -euo pipefail

git init susfs_reference
git -C susfs_reference remote add origin "$SUSFS_REPOSITORY"
for attempt in 1 2 3; do
  if git -C susfs_reference fetch --no-tags --depth=1 \
      origin "$SUSFS_COMMIT"; then
    break
  fi
  if test "$attempt" = 3; then
    echo "::error::Unable to fetch pinned SUSFS after three attempts."
    exit 1
  fi
  sleep "$((attempt * 10))"
done
git -C susfs_reference checkout --detach "$SUSFS_COMMIT"
test "$(git -C susfs_reference rev-parse HEAD)" = "$SUSFS_COMMIT"
grep -Fqx '#define SUSFS_VERSION "v2.3.0"' \
  susfs_reference/kernel_patches/include/linux/susfs.h

git init sm8250_reference
git -C sm8250_reference remote add origin \
  "$SM8250_REFERENCE_REPOSITORY"
git -C sm8250_reference fetch --no-tags --depth=2 \
  "${SM8250_SEED:-$SM8250_REFERENCE_REPOSITORY}" "$SM8250_REFERENCE_COMMIT"
git -C sm8250_reference checkout --detach \
  "$SM8250_REFERENCE_COMMIT"
test "$(
  git -C sm8250_reference rev-parse HEAD
)" = "$SM8250_REFERENCE_COMMIT"
test "$(
  git -C sm8250_reference rev-parse \
    "${SM8250_REFERENCE_COMMIT}^"
)" = "$SM8250_REFERENCE_BASE_COMMIT"
