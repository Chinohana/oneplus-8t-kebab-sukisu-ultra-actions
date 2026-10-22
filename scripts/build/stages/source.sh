#!/usr/bin/env bash
set -euo pipefail

git init kernel_common
git -C kernel_common remote add origin "$KERNEL_REPOSITORY"
kernel_fetch_source="${KERNEL_SEED:-$KERNEL_REPOSITORY}"
git -C kernel_common fetch --no-tags --depth=1 \
  "$kernel_fetch_source" "$KERNEL_COMMIT"
git -C kernel_common checkout --detach "$KERNEL_COMMIT"
test "$(git -C kernel_common rev-parse HEAD)" = "$KERNEL_COMMIT"

sed -i 's/ -dirty//g' kernel_common/scripts/setlocalversion
sed -i '$i res=$(echo "$res" | sed '\''s/-dirty//g'\'')' \
  kernel_common/scripts/setlocalversion

cd kernel_common
curl --fail --location --show-error --silent \
  "https://raw.githubusercontent.com/SukiSU-Ultra/SukiSU-Ultra/${SUKISU_COMMIT}/kernel/setup.sh" \
  | bash -s "$SUKISU_COMMIT"
test -d KernelSU
test "$(git -C KernelSU rev-parse HEAD)" = "$SUKISU_COMMIT"
test "$(
  git -C KernelSU remote get-url origin
)" = "$SUKISU_REPOSITORY"

git -C KernelSU apply --check --whitespace=error-all \
  "$BUILD_ROOT/$SUKISU_COMPAT_PATCH"
git -C KernelSU apply --whitespace=error-all \
  "$BUILD_ROOT/$SUKISU_COMPAT_PATCH"
git -C KernelSU diff --check
git -C KernelSU diff --name-only |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/sukisu-compat-files.actual"
diff -u "$BUILD_TEMP/sukisu-compat-files.expected" \
  "$BUILD_TEMP/sukisu-compat-files.actual"
cd "$BUILD_ROOT"

# kernel_baseline is a fresh checkout of KERNEL_COMMIT; replay the
# same SukiSU builtin preparation below so both trees stay
# identical except for the SUSFS/SELinux hide patches.
git -C kernel_common worktree add ../kernel_baseline "$KERNEL_COMMIT"
mv kernel_common kernel_experiment
git -C kernel_experiment worktree repair ../kernel_baseline

sed -i 's/ -dirty//g' kernel_baseline/scripts/setlocalversion
sed -i '$i res=$(echo "$res" | sed '\''s/-dirty//g'\'')' \
  kernel_baseline/scripts/setlocalversion
cd kernel_baseline
curl --fail --location --show-error --silent \
  "https://raw.githubusercontent.com/SukiSU-Ultra/SukiSU-Ultra/${SUKISU_COMMIT}/kernel/setup.sh" \
  | bash -s "$SUKISU_COMMIT"
test -d KernelSU
test "$(git -C KernelSU rev-parse HEAD)" = "$SUKISU_COMMIT"
test "$(git -C KernelSU remote get-url origin)" = "$SUKISU_REPOSITORY"
git -C KernelSU apply --check --whitespace=error-all \
  "$BUILD_ROOT/$SUKISU_COMPAT_PATCH"
git -C KernelSU apply --whitespace=error-all \
  "$BUILD_ROOT/$SUKISU_COMPAT_PATCH"
git -C KernelSU diff --check
git -C KernelSU diff --name-only |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/sukisu-compat-files.baseline.actual"
diff -u "$BUILD_TEMP/sukisu-compat-files.expected" \
  "$BUILD_TEMP/sukisu-compat-files.baseline.actual"
cd "$BUILD_ROOT"

if test "$ENABLE_SELINUX_HIDE" = "true"; then
  git -C kernel_experiment/KernelSU apply --check \
    --whitespace=error-all \
    "$BUILD_ROOT/$SELINUX_HIDE_SUKISU_PATCH"
  git -C kernel_experiment/KernelSU apply \
    --whitespace=error-all \
    "$BUILD_ROOT/$SELINUX_HIDE_SUKISU_PATCH"
  git -C kernel_experiment/KernelSU diff --check
fi
