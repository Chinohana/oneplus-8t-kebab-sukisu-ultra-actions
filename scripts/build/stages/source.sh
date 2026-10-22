#!/usr/bin/env bash
set -euo pipefail

prepare_sukisu() {
  git init KernelSU
  git -C KernelSU remote add origin "$SUKISU_REPOSITORY"
  git -C KernelSU fetch --no-tags --depth=1 \
    "${SUKISU_SEED:-$SUKISU_REPOSITORY}" "$SUKISU_COMMIT"
  git -C KernelSU checkout --detach "$SUKISU_COMMIT"
  # Match the pinned setup.sh integration without downloading it or running git pull.
  ln -sf ../KernelSU/kernel drivers/kernelsu
  grep -q kernelsu drivers/Makefile || printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> drivers/Makefile
  grep -q 'drivers/kernelsu/Kconfig' drivers/Kconfig || \
    sed -i '/endmenu/i\source "drivers/kernelsu/Kconfig"' drivers/Kconfig
}

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
prepare_sukisu
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
prepare_sukisu
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
