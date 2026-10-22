#!/usr/bin/env bash
set -euo pipefail

normalize_warnings() {
  local log="$1"
  local output="$2"
  {
    grep -E '(^|: )[Ww]arning:' "$log" || true
  } |
    sed -E \
      -e "s#${BUILD_ROOT}/##g" \
      -e 's/:[0-9]+(:[0-9]+)?:/:<line>:/g' |
    LC_ALL=C sort -u > "$output"
}

normalize_warnings audit/build-baseline.log \
  audit/warnings-baseline.txt
if test "$ENABLE_SUSFS" = "true"; then
  normalize_warnings audit/build-smoke.log \
    audit/warnings-smoke.txt
  comm -13 audit/warnings-baseline.txt \
    audit/warnings-smoke.txt \
    > audit/warnings-new-in-smoke.txt
  if test -s audit/warnings-new-in-smoke.txt; then
    echo "::error::The smoke build introduced new compiler warnings."
    cat audit/warnings-new-in-smoke.txt
    exit 1
  fi
else
  normalize_warnings audit/build-selected.log \
    audit/warnings-selected.txt
  comm -13 audit/warnings-baseline.txt \
    audit/warnings-selected.txt \
    > audit/warnings-new-in-selected.txt
  if test -s audit/warnings-new-in-selected.txt; then
    echo "::error::The selected build introduced new compiler warnings."
    cat audit/warnings-new-in-selected.txt
    exit 1
  fi
fi

if test "$ENABLE_SUSFS" = "true"; then
  if test "$PROFILE" = minimal-mount ||
     test "$PROFILE" = extended-stat ||
     test "$PROFILE" = extended-full; then
    normalize_warnings audit/build-minimal-mount.log \
      audit/warnings-minimal-mount.txt
    comm -13 audit/warnings-smoke.txt \
      audit/warnings-minimal-mount.txt \
      > audit/warnings-new-in-minimal-mount.txt
    if test -s audit/warnings-new-in-minimal-mount.txt; then
      echo "::error::minimal-mount introduced new compiler warnings."
      cat audit/warnings-new-in-minimal-mount.txt
      exit 1
    fi
  fi

  if test "$PROFILE" = extended-stat; then
    normalize_warnings audit/build-extended-stat.log \
      audit/warnings-extended-stat.txt
    comm -13 audit/warnings-minimal-mount.txt \
      audit/warnings-extended-stat.txt \
      > audit/warnings-new-in-extended-stat.txt
    if test -s audit/warnings-new-in-extended-stat.txt; then
      echo "::error::extended-stat introduced new compiler warnings."
      cat audit/warnings-new-in-extended-stat.txt
      exit 1
    fi
  fi

  if test "$PROFILE" = extended-full; then
    normalize_warnings audit/build-extended-full.log \
      audit/warnings-extended-full.txt
    comm -13 audit/warnings-minimal-mount.txt \
      audit/warnings-extended-full.txt \
      > audit/warnings-new-in-extended-full.txt
    if test -s audit/warnings-new-in-extended-full.txt; then
      echo "::error::extended-full introduced new compiler warnings."
      cat audit/warnings-new-in-extended-full.txt
      exit 1
    fi
  fi
fi

build_logs="audit/build-baseline.log"
if test "$ENABLE_SUSFS" = "true"; then
  build_logs="$build_logs audit/build-smoke.log \
    audit/build-minimal-mount.log audit/build-extended-stat.log \
    audit/build-extended-full.log"
else
  build_logs="$build_logs audit/build-selected.log"
fi
if grep -Eqi \
  'undefined reference|duplicate symbol|ld\.lld: error' \
  $build_logs 2>/dev/null; then
  echo "::error::A linker error signature is present."
  exit 1
fi

require_symbol() {
  local map="$1"
  local symbol="$2"
  grep -Eq "[[:space:]]${symbol}$" "$map"
}

if test "$ENABLE_SUSFS" = "true"; then
  second_map=kernel_experiment/out-smoke/System.map
else
  second_map=kernel_experiment/out-selected/System.map
fi
for map in \
  kernel_baseline/out-baseline/System.map \
  "$second_map"; do
  for symbol in \
    kernelsu_init \
    ksu_handle_execveat \
    ksu_handle_faccessat \
    ksu_handle_vfs_read \
    ksu_handle_stat \
    ksu_handle_sys_reboot; do
    require_symbol "$map" "$symbol"
  done
done

if test "$ENABLE_SUSFS" = "true"; then
  for symbol in \
    susfs_init \
    susfs_show_version \
    susfs_show_variant \
    susfs_get_enabled_features \
    susfs_enable_log \
    susfs_set_avc_log_spoofing \
    susfs_start_sdcard_monitor_fn \
    susfs_extra_works \
    ksu_handle_setresuid \
    ksu_handle_execveat_sucompat \
    ksu_handle_vfs_fstat; do
    require_symbol \
      kernel_experiment/out-smoke/System.map "$symbol"
  done
fi

if test "$ENABLE_SELINUX_HIDE" = "true"; then
  for symbol in \
    ksu_selinux_hide_init \
    ksu_selinux_hide_exit \
    ksu_selinux_hide_handle_second_stage \
    ksu_selinux_hide_handle_post_fs_data \
    ksu_selinux_hide_drop_backup_if_unused \
    ksu_dup_selinux_ss \
    ksu_destroy_selinux_ss; do
    require_symbol "$second_map" "$symbol"
  done
fi

if test "$ENABLE_SUSFS" = "true"; then
  if test "$PROFILE" = minimal-mount ||
     test "$PROFILE" = extended-stat ||
     test "$PROFILE" = extended-full; then
    for symbol in \
      kernelsu_init \
      ksu_handle_execveat \
      ksu_handle_faccessat \
      ksu_handle_vfs_read \
      ksu_handle_stat \
      ksu_handle_sys_reboot \
      susfs_init \
      susfs_show_version \
      susfs_show_variant \
      susfs_get_enabled_features \
      susfs_enable_log \
      susfs_set_avc_log_spoofing \
      susfs_start_sdcard_monitor_fn \
      susfs_extra_works \
      susfs_set_hide_sus_mnts_for_non_su_procs \
      susfs_get_non_sus_mnt_id_from_mnt \
      susfs_get_non_sus_vfsmnt_from_vfsmnt \
      ksu_handle_setresuid \
      ksu_handle_execveat_sucompat \
      ksu_handle_vfs_fstat; do
      require_symbol \
        kernel_experiment/out-minimal-mount/System.map "$symbol"
    done
  fi

  if test "$PROFILE" = extended-stat; then
    for symbol in \
      kernelsu_init \
      ksu_handle_execveat \
      ksu_handle_faccessat \
      ksu_handle_vfs_read \
      ksu_handle_stat \
      ksu_handle_sys_reboot \
      susfs_init \
      susfs_show_version \
      susfs_show_variant \
      susfs_get_enabled_features \
      susfs_enable_log \
      susfs_extra_works \
      susfs_set_hide_sus_mnts_for_non_su_procs \
      susfs_get_non_sus_mnt_id_from_mnt \
      susfs_get_non_sus_vfsmnt_from_vfsmnt \
      susfs_add_sus_kstat \
      susfs_update_sus_kstat \
      susfs_sus_kstat_spoof_generic_fillattr \
      susfs_sus_kstat_spoof_show_map_vma \
      ksu_handle_setresuid \
      ksu_handle_execveat_sucompat \
      ksu_handle_vfs_fstat; do
      require_symbol \
        kernel_experiment/out-extended-stat/System.map "$symbol"
    done
  fi

  if test "$PROFILE" = extended-full; then
    for symbol in \
      kernelsu_init \
      ksu_handle_execveat \
      ksu_handle_faccessat \
      ksu_handle_vfs_read \
      ksu_handle_stat \
      ksu_handle_sys_reboot \
      susfs_init \
      susfs_show_version \
      susfs_show_variant \
      susfs_get_enabled_features \
      susfs_enable_log \
      susfs_extra_works \
      susfs_add_sus_path \
      susfs_add_sus_path_loop \
      susfs_set_hide_sus_mnts_for_non_su_procs \
      susfs_add_sus_kstat \
      susfs_update_sus_kstat \
      susfs_set_uname \
      susfs_spoof_uname \
      susfs_set_cmdline_or_bootconfig \
      susfs_spoof_cmdline_or_bootconfig \
      susfs_add_open_redirect \
      susfs_open_redirect_spoof_do_sys_openat \
      susfs_add_sus_map \
      ksu_handle_setresuid \
      ksu_handle_execveat_sucompat \
      ksu_handle_vfs_fstat; do
      require_symbol \
        kernel_experiment/out-extended-full/System.map "$symbol"
    done
  fi
fi

awk '{print $3}' kernel_baseline/out-baseline/System.map |
  LC_ALL=C sort -u > audit/symbols-baseline.txt
if test "$ENABLE_SUSFS" = "true"; then
  awk '{print $3}' kernel_experiment/out-smoke/System.map |
    LC_ALL=C sort -u > audit/symbols-smoke.txt
  comm -3 audit/symbols-baseline.txt audit/symbols-smoke.txt \
    > audit/system-map-baseline-to-smoke.diff
  if test "$PROFILE" = minimal-mount ||
     test "$PROFILE" = extended-stat ||
     test "$PROFILE" = extended-full; then
    awk '{print $3}' \
      kernel_experiment/out-minimal-mount/System.map |
      LC_ALL=C sort -u > audit/symbols-minimal-mount.txt
    comm -3 audit/symbols-smoke.txt \
      audit/symbols-minimal-mount.txt \
      > audit/system-map-smoke-to-minimal-mount.diff
  fi
  if test "$PROFILE" = extended-stat; then
    awk '{print $3}' \
      kernel_experiment/out-extended-stat/System.map |
      LC_ALL=C sort -u > audit/symbols-extended-stat.txt
    comm -3 audit/symbols-minimal-mount.txt \
      audit/symbols-extended-stat.txt \
      > audit/system-map-minimal-mount-to-extended-stat.diff
  fi
  if test "$PROFILE" = extended-full; then
    awk '{print $3}' \
      kernel_experiment/out-extended-full/System.map |
      LC_ALL=C sort -u > audit/symbols-extended-full.txt
    comm -3 audit/symbols-minimal-mount.txt \
      audit/symbols-extended-full.txt \
      > audit/system-map-minimal-mount-to-extended-full.diff
  fi
else
  awk '{print $3}' \
    kernel_experiment/out-selected/System.map |
    LC_ALL=C sort -u > audit/symbols-selected.txt
  comm -3 audit/symbols-baseline.txt \
    audit/symbols-selected.txt \
    > audit/system-map-baseline-to-selected.diff
fi

if test "$ENABLE_SUSFS" = "true"; then
  "$BUILD_ROOT/toolchains/clang/bin/llvm-nm" -u \
    kernel_experiment/out-smoke/vmlinux \
    > audit/unresolved-smoke.txt || true
  if grep -Eqi 'susfs|ksu' audit/unresolved-smoke.txt; then
    echo "::error::An unresolved KSU/SUSFS symbol remains."
    exit 1
  fi

  if test "$PROFILE" = extended-stat; then
    "$BUILD_ROOT/toolchains/clang/bin/llvm-nm" -u \
      kernel_experiment/out-extended-stat/vmlinux \
      > audit/unresolved-extended-stat.txt || true
    if grep -Eqi 'susfs|ksu' \
      audit/unresolved-extended-stat.txt; then
      echo "::error::An unresolved extended-stat KSU/SUSFS symbol remains."
      exit 1
    fi
  fi
  if test "$PROFILE" = extended-full; then
    "$BUILD_ROOT/toolchains/clang/bin/llvm-nm" -u \
      kernel_experiment/out-extended-full/vmlinux \
      > audit/unresolved-extended-full.txt || true
    if grep -Eqi 'susfs|ksu' \
      audit/unresolved-extended-full.txt; then
      echo "::error::An unresolved extended-full KSU/SUSFS symbol remains."
      exit 1
    fi
  fi
else
  "$BUILD_ROOT/toolchains/clang/bin/llvm-nm" -u \
    kernel_experiment/out-selected/vmlinux \
    > audit/unresolved-selected.txt || true
  if grep -Eqi 'susfs|ksu' audit/unresolved-selected.txt; then
    echo "::error::An unresolved KSU symbol remains."
    exit 1
  fi
fi

baseline_size="$(
  stat -c '%s' \
    kernel_baseline/out-baseline/arch/arm64/boot/Image
)"
{
  echo "baseline_bytes=$baseline_size"
  echo "max_growth_bytes=$MAX_IMAGE_GROWTH_BYTES"
  echo "max_growth_percent=$MAX_IMAGE_GROWTH_PERCENT"
} > audit/image-size-report.txt

if test "$ENABLE_SUSFS" = "true"; then
  smoke_size="$(
    stat -c '%s' \
      kernel_experiment/out-smoke/arch/arm64/boot/Image
  )"
  smoke_delta="$((smoke_size - baseline_size))"
  {
    echo "smoke_bytes=$smoke_size"
    echo "smoke_delta_bytes=$smoke_delta"
  } >> audit/image-size-report.txt

  test "$smoke_delta" -le "$MAX_IMAGE_GROWTH_BYTES"
  test "$((smoke_size * 100))" \
    -le "$((baseline_size * (100 + MAX_IMAGE_GROWTH_PERCENT)))"

  selected_out=out-smoke
  if test "$PROFILE" = minimal-mount ||
     test "$PROFILE" = extended-stat ||
     test "$PROFILE" = extended-full; then
    selected_out=out-minimal-mount
    minimal_size="$(
      stat -c '%s' \
        kernel_experiment/out-minimal-mount/arch/arm64/boot/Image
    )"
    minimal_delta="$((minimal_size - baseline_size))"
    {
      echo "minimal_mount_bytes=$minimal_size"
      echo "minimal_mount_delta_bytes=$minimal_delta"
    } >> audit/image-size-report.txt
    test "$minimal_delta" -le "$MAX_IMAGE_GROWTH_BYTES"
    test "$((minimal_size * 100))" \
      -le "$((baseline_size * (100 + MAX_IMAGE_GROWTH_PERCENT)))"
  fi
  if test "$PROFILE" = extended-stat; then
    selected_out=out-extended-stat
    extended_size="$(
      stat -c '%s' \
        kernel_experiment/out-extended-stat/arch/arm64/boot/Image
    )"
    extended_delta="$((extended_size - baseline_size))"
    {
      echo "extended_stat_bytes=$extended_size"
      echo "extended_stat_delta_bytes=$extended_delta"
    } >> audit/image-size-report.txt
    test "$extended_delta" -le "$MAX_IMAGE_GROWTH_BYTES"
    test "$((extended_size * 100))" \
      -le "$((baseline_size * (100 + MAX_IMAGE_GROWTH_PERCENT)))"
  fi
  if test "$PROFILE" = extended-full; then
    selected_out=out-extended-full
    full_size="$(
      stat -c '%s' \
        kernel_experiment/out-extended-full/arch/arm64/boot/Image
    )"
    full_delta="$((full_size - baseline_size))"
    {
      echo "extended_full_bytes=$full_size"
      echo "extended_full_delta_bytes=$full_delta"
    } >> audit/image-size-report.txt
    test "$full_delta" -le "$MAX_IMAGE_GROWTH_BYTES"
    test "$((full_size * 100))" \
      -le "$((baseline_size * (100 + MAX_IMAGE_GROWTH_PERCENT)))"
  fi
else
  selected_out=out-selected
  selected_size="$(
    stat -c '%s' \
      kernel_experiment/out-selected/arch/arm64/boot/Image
  )"
  selected_delta="$((selected_size - baseline_size))"
  {
    echo "selected_bytes=$selected_size"
    echo "selected_delta_bytes=$selected_delta"
  } >> audit/image-size-report.txt
  test "$selected_delta" -le "$MAX_IMAGE_GROWTH_BYTES"
  test "$((selected_size * 100))" \
    -le "$((baseline_size * (100 + MAX_IMAGE_GROWTH_PERCENT)))"
fi
echo "SELECTED_OUT=$selected_out" >> "$BUILD_ENV"

git -C kernel_experiment diff --name-only \
  -- fs include kernel security |
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

sha256sum \
  kernel_baseline/out-baseline/.config \
  kernel_baseline/out-baseline/System.map \
  kernel_baseline/out-baseline/arch/arm64/boot/Image \
  > audit/kernel-build-files.sha256
if test "$ENABLE_SUSFS" = "true"; then
  sha256sum \
    kernel_experiment/out-smoke/.config \
    kernel_experiment/out-smoke/System.map \
    kernel_experiment/out-smoke/arch/arm64/boot/Image \
    >> audit/kernel-build-files.sha256
  if test "$PROFILE" = minimal-mount ||
     test "$PROFILE" = extended-stat ||
     test "$PROFILE" = extended-full; then
    sha256sum \
      kernel_experiment/out-minimal-mount/.config \
      kernel_experiment/out-minimal-mount/System.map \
      kernel_experiment/out-minimal-mount/arch/arm64/boot/Image \
      >> audit/kernel-build-files.sha256
  fi
  if test "$PROFILE" = extended-stat; then
    sha256sum \
      kernel_experiment/out-extended-stat/.config \
      kernel_experiment/out-extended-stat/System.map \
      kernel_experiment/out-extended-stat/arch/arm64/boot/Image \
      >> audit/kernel-build-files.sha256
  fi
  if test "$PROFILE" = extended-full; then
    sha256sum \
      kernel_experiment/out-extended-full/.config \
      kernel_experiment/out-extended-full/System.map \
      kernel_experiment/out-extended-full/arch/arm64/boot/Image \
      >> audit/kernel-build-files.sha256
  fi
else
  sha256sum \
    kernel_experiment/out-selected/.config \
    kernel_experiment/out-selected/System.map \
    kernel_experiment/out-selected/arch/arm64/boot/Image \
    >> audit/kernel-build-files.sha256
fi
