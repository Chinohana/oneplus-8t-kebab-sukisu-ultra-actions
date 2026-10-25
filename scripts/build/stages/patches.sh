#!/usr/bin/env bash
set -euo pipefail

git -C kernel_baseline apply --check --whitespace=error-all \
  "$BUILD_ROOT/$BASELINE_HOOK_PATCH"
git -C kernel_baseline apply --whitespace=error-all \
  "$BUILD_ROOT/$BASELINE_HOOK_PATCH"
git -C kernel_baseline diff --check
git -C kernel_baseline diff --name-only -- fs include kernel security |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/baseline-hook-files.actual"
diff -u "$BUILD_TEMP/baseline-hook-files.expected" \
  "$BUILD_TEMP/baseline-hook-files.actual"

if test "$ENABLE_SUSFS" = "true"; then
  git -C kernel_experiment apply --check \
    --whitespace=error-all \
    "$BUILD_ROOT/$SUSFS_PATCH"
  git -C kernel_experiment apply --whitespace=error-all \
    "$BUILD_ROOT/$SUSFS_PATCH"
  git -C kernel_experiment add -N \
    fs/susfs.c include/linux/susfs.h include/linux/susfs_def.h
  git -C kernel_experiment apply --check \
    --whitespace=error-all \
    "$BUILD_ROOT/$SUSFS_SUKISU_42_COMPAT_PATCH"
  git -C kernel_experiment apply --whitespace=error-all \
    "$BUILD_ROOT/$SUSFS_SUKISU_42_COMPAT_PATCH"
else
  git -C kernel_experiment apply --check \
    --whitespace=error-all \
    "$BUILD_ROOT/$BASELINE_HOOK_PATCH"
  git -C kernel_experiment apply --whitespace=error-all \
    "$BUILD_ROOT/$BASELINE_HOOK_PATCH"
fi
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  git -C kernel_experiment apply --check \
    --whitespace=error-all \
    "$BUILD_ROOT/$SELINUX_HIDE_KERNEL_PATCH"
  git -C kernel_experiment apply --whitespace=error-all \
    "$BUILD_ROOT/$SELINUX_HIDE_KERNEL_PATCH"
fi
git -C kernel_experiment diff --check
git -C kernel_experiment diff --name-only \
  -- block fs include kernel security |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/susfs-kernel-files.actual"
if test "$ENABLE_SUSFS" = "true"; then
  expected_files="$BUILD_TEMP/susfs-kernel-files.expected"
else
  expected_files="$BUILD_TEMP/baseline-hook-files.expected"
fi
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  expected_files="$expected_files $BUILD_TEMP/selinux-hide-kernel-files.expected"
fi
cat $expected_files |
  LC_ALL=C sort -u > "$BUILD_TEMP/experiment-files.expected"
diff -u "$BUILD_TEMP/experiment-files.expected" \
  "$BUILD_TEMP/susfs-kernel-files.actual"

for tree in kernel_baseline kernel_experiment; do
  git -C "$tree" apply --check --whitespace=error-all \
    "$BUILD_ROOT/$REPRODUCIBLE_KHEADERS_PATCH"
  git -C "$tree" apply --whitespace=error-all \
    "$BUILD_ROOT/$REPRODUCIBLE_KHEADERS_PATCH"
  git -C "$tree" diff --check
  grep -Fq -- "--sort=name --mtime=\"@\${SOURCE_DATE_EPOCH:-0}\"" \
    "$tree/kernel/gen_kheaders.sh"
done
{
  git -C kernel_baseline diff --name-only -- kernel/gen_kheaders.sh
  git -C kernel_experiment diff --name-only -- kernel/gen_kheaders.sh
} | LC_ALL=C sort -u \
  > "$BUILD_TEMP/reproducible-kheaders-files.actual"
diff -u "$BUILD_TEMP/reproducible-kheaders-files.expected" \
  "$BUILD_TEMP/reproducible-kheaders-files.actual"
cp "$BUILD_TEMP/reproducible-kheaders-files.actual" audit/

find kernel_baseline kernel_experiment \
  -path '*/.git' -prune -o \
  -type f \( -name '*.rej' -o -name '*.orig' \) -print \
  > "$BUILD_TEMP/rejects-or-originals"
test ! -s "$BUILD_TEMP/rejects-or-originals"

cp "$BUILD_TEMP/"*.actual audit/
