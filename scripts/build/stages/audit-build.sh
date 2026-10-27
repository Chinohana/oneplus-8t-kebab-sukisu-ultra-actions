#!/usr/bin/env bash
set -euo pipefail
out="kernel_experiment/$SELECTED_OUT"
test -s "$out/arch/arm64/boot/Image"
test -s "$out/vmlinux"
test -s "$out/System.map"
# Preserve warnings without pretending a second configuration was compiled.
{ grep -E '(^|: )[Ww]arning:' audit/build-selected.log || true; } |
  sed -E -e "s#${BUILD_ROOT}/##g" -e 's/:[0-9]+(:[0-9]+)?:/:<line>:/g' |
  LC_ALL=C sort -u > audit/warnings-selected.txt
if grep -Eqi 'undefined reference|duplicate symbol|ld\.lld: error' audit/build-selected.log; then
  echo '::error::A linker error signature is present.'
  exit 1
fi
require_symbol() {
  grep -Eq "[[:space:]]${1}$" "$out/System.map"
}
for symbol in kernelsu_init ksu_handle_execveat ksu_handle_faccessat ksu_handle_vfs_read ksu_handle_stat ksu_handle_sys_reboot; do
  require_symbol "$symbol"
done
if test "$ENABLE_SUSFS" = true; then
  for symbol in susfs_init susfs_show_version susfs_show_variant susfs_get_enabled_features susfs_enable_log susfs_set_avc_log_spoofing susfs_start_sdcard_monitor_fn susfs_extra_works susfs_set_priority_uid_filter susfs_is_priority_uid_filtered ksu_handle_setresuid ksu_handle_execveat_sucompat ksu_handle_vfs_fstat; do
    require_symbol "$symbol"
  done
  if test "$PROFILE" != smoke; then
    for symbol in susfs_set_hide_sus_mnts_for_non_su_procs susfs_get_non_sus_mnt_id_from_mnt susfs_get_non_sus_vfsmnt_from_vfsmnt; do
      require_symbol "$symbol"
    done
  fi
  if test "$PROFILE" = extended-stat || test "$PROFILE" = extended-full; then
    for symbol in susfs_add_sus_kstat susfs_update_sus_kstat susfs_sus_kstat_spoof_generic_fillattr susfs_sus_kstat_spoof_show_map_vma; do
      require_symbol "$symbol"
    done
  fi
  if test "$PROFILE" = extended-full; then
    for symbol in susfs_add_sus_path susfs_add_sus_path_loop susfs_set_uname susfs_spoof_uname susfs_set_cmdline_or_bootconfig susfs_spoof_cmdline_or_bootconfig susfs_add_open_redirect susfs_open_redirect_spoof_do_sys_openat susfs_add_sus_map; do
      require_symbol "$symbol"
    done
  fi
fi
if test "$ENABLE_SELINUX_HIDE" = true; then
  for symbol in ksu_selinux_hide_init ksu_selinux_hide_exit ksu_selinux_hide_handle_second_stage ksu_selinux_hide_handle_post_fs_data ksu_selinux_hide_drop_backup_if_unused ksu_dup_selinux_ss ksu_destroy_selinux_ss; do
    require_symbol "$symbol"
  done
fi
"$BUILD_ROOT/toolchains/clang/bin/llvm-nm" -u "$out/vmlinux" > audit/unresolved-selected.txt
if grep -Eqi 'susfs|ksu' audit/unresolved-selected.txt; then
  echo '::error::An unresolved KSU/SUSFS symbol remains.'
  exit 1
fi
{
  echo "selected_out=$SELECTED_OUT"
  echo "selected_bytes=$(stat -c '%s' "$out/arch/arm64/boot/Image")"
  echo 'comparison_baseline=not-built-single-configuration-policy'
} > audit/image-size-report.txt

git -C kernel_experiment diff --name-only \
  -- block fs include kernel security |
  LC_ALL=C sort -u \
  > "$BUILD_TEMP/susfs-kernel-files.after-build"
if test "$ENABLE_SUSFS" = "true"; then
  expected_files="$BUILD_TEMP/susfs-kernel-files.expected"
else
  expected_files="$BUILD_TEMP/baseline-hook-files.expected"
fi
expected_files="$expected_files $BUILD_TEMP/reproducible-kheaders-files.expected"
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  expected_files="$expected_files $BUILD_TEMP/selinux-hide-kernel-files.expected"
fi
cat $expected_files |
  LC_ALL=C sort -u > "$BUILD_TEMP/experiment-files.after"
diff -u "$BUILD_TEMP/experiment-files.after" \
  "$BUILD_TEMP/susfs-kernel-files.after-build"

sha256sum "$out/.config" "$out/System.map" "$out/arch/arm64/boot/Image" > audit/kernel-build-files.sha256
