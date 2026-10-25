#!/usr/bin/env bash
set -euo pipefail
mkdir -p audit

cat > "$BUILD_TEMP/reproducible-kheaders-files.expected" <<'EOF'
kernel/gen_kheaders.sh
EOF
sed -i 's/^          //' \
  "$BUILD_TEMP/reproducible-kheaders-files.expected"
git apply --numstat "$REPRODUCIBLE_KHEADERS_PATCH" |
  awk -F '\t' '{print $3}' |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/reproducible-kheaders-files.from-patch"
diff -u "$BUILD_TEMP/reproducible-kheaders-files.expected" \
  "$BUILD_TEMP/reproducible-kheaders-files.from-patch"
if grep -Eq '(^/|(^|/)\.\.(/|$)|\\)' \
  "$BUILD_TEMP/reproducible-kheaders-files.from-patch"; then
  echo "::error::Unsafe path found in the reproducible kheaders patch."
  exit 1
fi

if test "$ENABLE_SUSFS" = "true"; then
  cat > "$BUILD_TEMP/susfs-kernel-files.expected" <<'EOF'
block/ioprio.c
fs/Makefile
fs/exec.c
fs/namespace.c
fs/notify/fdinfo.c
fs/open.c
fs/proc/fd.c
fs/proc_namespace.c
fs/read_write.c
fs/stat.c
fs/statfs.c
fs/susfs.c
include/linux/susfs.h
include/linux/susfs_def.h
kernel/reboot.c
kernel/sys.c
security/selinux/avc.c
EOF
  sed -i 's/^          //' \
    "$BUILD_TEMP/susfs-kernel-files.expected"
  LC_ALL=C sort -o "$BUILD_TEMP/susfs-kernel-files.expected" \
    "$BUILD_TEMP/susfs-kernel-files.expected"

  git apply --numstat "$SUSFS_PATCH" |
    awk -F '\t' '{print $3}' |
    LC_ALL=C sort -u \
    > "$BUILD_TEMP/susfs-kernel-files.from-patch"
  diff -u "$BUILD_TEMP/susfs-kernel-files.expected" \
    "$BUILD_TEMP/susfs-kernel-files.from-patch"

  if grep -Eq '(^/|(^|/)\.\.(/|$)|\\)' \
    "$BUILD_TEMP/susfs-kernel-files.from-patch"; then
    echo "::error::Unsafe path found in the experimental patch."
    exit 1
  fi

  cat > "$BUILD_TEMP/susfs-sukisu-42-compat-files.expected" <<'EOF'
fs/exec.c
EOF
  sed -i 's/^          //' \
    "$BUILD_TEMP/susfs-sukisu-42-compat-files.expected"
  git apply --numstat "$SUSFS_SUKISU_42_COMPAT_PATCH" |
    awk -F '\t' '{print $3}' |
    LC_ALL=C sort -u \
    > "$BUILD_TEMP/susfs-sukisu-42-compat-files.from-patch"
  diff -u "$BUILD_TEMP/susfs-sukisu-42-compat-files.expected" \
    "$BUILD_TEMP/susfs-sukisu-42-compat-files.from-patch"
fi

cat > "$BUILD_TEMP/baseline-hook-files.expected" <<'EOF'
fs/exec.c
fs/open.c
fs/read_write.c
fs/stat.c
kernel/reboot.c
EOF
sed -i 's/^          //' \
  "$BUILD_TEMP/baseline-hook-files.expected"

git apply --numstat "$BASELINE_HOOK_PATCH" |
  awk -F '\t' '{print $3}' |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/baseline-hook-files.from-patch"
diff -u "$BUILD_TEMP/baseline-hook-files.expected" \
  "$BUILD_TEMP/baseline-hook-files.from-patch"

cat > "$BUILD_TEMP/sukisu-compat-files.expected" <<'EOF'
kernel/Makefile
kernel/extension/cpu_spoof.c
kernel/extension/dynamic_sig_fallback.c
kernel/feature/mount_hide.c
kernel/kernel_includes.h
kernel/ksu_main.c
kernel/manager/pkg_observer.c
kernel/policy/feature.c
kernel/runtime/ksud.c
kernel/selinux/rules.c
kernel/sulog/event.c
kernel/supercall/dispatch.c
EOF
sed -i 's/^          //' \
  "$BUILD_TEMP/sukisu-compat-files.expected"
git apply --numstat "$SUKISU_COMPAT_PATCH" |
  awk -F '\t' '{print $3}' |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/sukisu-compat-files.from-patch"
diff -u "$BUILD_TEMP/sukisu-compat-files.expected" \
  "$BUILD_TEMP/sukisu-compat-files.from-patch"

if test "$ENABLE_SELINUX_HIDE" = "true"; then
  cat > "$BUILD_TEMP/selinux-hide-sukisu-files.expected" <<'EOF'
kernel/Kconfig
kernel/feature/selinux_hide.c
kernel/feature/selinux_hide.h
kernel/include/uapi/feature.h
kernel/ksu_main.c
kernel/runtime/ksud.c
kernel/selinux/rules.c
kernel/selinux/sepolicy.c
kernel/selinux/sepolicy.h
EOF
  sed -i 's/^          //' \
    "$BUILD_TEMP/selinux-hide-sukisu-files.expected"
  git apply --numstat "$SELINUX_HIDE_SUKISU_PATCH" |
    awk -F '\t' '{print $3}' | LC_ALL=C sort -u \
    > "$BUILD_TEMP/selinux-hide-sukisu-files.from-patch"
  diff -u "$BUILD_TEMP/selinux-hide-sukisu-files.expected" \
    "$BUILD_TEMP/selinux-hide-sukisu-files.from-patch"

  cat > "$BUILD_TEMP/selinux-hide-kernel-files.expected" <<'EOF'
security/selinux/selinuxfs.c
EOF
  sed -i 's/^          //' \
    "$BUILD_TEMP/selinux-hide-kernel-files.expected"
  git apply --numstat "$SELINUX_HIDE_KERNEL_PATCH" |
    awk -F '\t' '{print $3}' | LC_ALL=C sort -u \
    > "$BUILD_TEMP/selinux-hide-kernel-files.from-patch"
  diff -u "$BUILD_TEMP/selinux-hide-kernel-files.expected" \
    "$BUILD_TEMP/selinux-hide-kernel-files.from-patch"
fi

cp "$BUILD_TEMP/"*.expected audit/
cp "$BUILD_TEMP/"*.from-patch audit/
if test "$ENABLE_SUSFS" = "true"; then
  patch_hash_list="$SUSFS_PATCH $SUSFS_SUKISU_42_COMPAT_PATCH "
else
  patch_hash_list=""
fi
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  patch_hash_list="${patch_hash_list}$SELINUX_HIDE_SUKISU_PATCH $SELINUX_HIDE_KERNEL_PATCH "
fi
sha256sum $patch_hash_list "$SUKISU_COMPAT_PATCH" \
  "$BASELINE_HOOK_PATCH" "$REPRODUCIBLE_KHEADERS_PATCH" |
  tee audit/patches.sha256
