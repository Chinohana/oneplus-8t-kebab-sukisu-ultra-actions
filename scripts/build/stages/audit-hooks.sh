#!/usr/bin/env bash
set -euo pipefail

require_one_call() {
  local file="$1"
  local call="$2"
  local count
  count="$(
    awk -v needle="$call" \
      'index($0, needle) { count++ } END { print count + 0 }' \
      "$file"
  )"
  if test "$count" -ne 1; then
    echo "::error file=$file::Expected one '$call' call, found $count."
    exit 1
  fi
}

for tree in kernel_baseline kernel_experiment; do
  python3 "$BUILD_ROOT/scripts/test-extension-abi.py" "$tree/KernelSU/kernel"
  python3 "$BUILD_ROOT/scripts/test-mount-hide.py" \
    "$tree/KernelSU/kernel/feature/mount_hide.c"
  python3 "$BUILD_ROOT/scripts/test-manager-crown.py" \
    "$tree/KernelSU/kernel/manager/throne_tracker.c"
  grep -Fq 'DECLARE(__u32, KERNEL_SU_UAPI_VERSION, 6);' \
    "$tree/KernelSU/kernel/include/uapi/supercall.h"
  grep -Fq "DECLARE(__u32, KSU_IOCTL_EXTENSION," \
    "$tree/KernelSU/kernel/include/uapi/extension.h"
  grep -Fq ".handler = do_extension," \
    "$tree/KernelSU/kernel/supercall/dispatch.c"
  grep -Fq "ksu_extension_dynamic_manager_io" \
    "$tree/KernelSU/kernel/extension/dynamic_manager.c"
  grep -Fq 'DECLARE(__u32, EVENT_SERVICES, 4);' \
    "$tree/KernelSU/kernel/include/uapi/supercall.h"
  require_one_call "$tree/fs/exec.c" \
    'ksu_handle_execveat(&fd'
  require_one_call "$tree/fs/exec.c" \
    'ksu_install_su_fd();'
  require_one_call "$tree/fs/open.c" \
    'ksu_handle_faccessat(&dfd, &filename'
  require_one_call "$tree/fs/read_write.c" \
    'ksu_handle_vfs_read(&file'
  require_one_call "$tree/fs/stat.c" \
    'ksu_handle_stat(&dfd, &filename'
  require_one_call "$tree/kernel/reboot.c" \
    'ksu_handle_sys_reboot(magic1'
done

if test "$ENABLE_SUSFS" = "true"; then
  require_one_call kernel_experiment/fs/open.c \
    'ksu_handle_faccessat(&dfd, &name'
  require_one_call kernel_experiment/fs/open.c \
    'struct filename **filename, int *mode'
  require_one_call kernel_experiment/fs/stat.c \
    'ksu_handle_stat(&dfd, &name'
  require_one_call kernel_experiment/fs/stat.c \
    'struct filename **filename, int *flags'

  grep -Fq \
    'int ksu_handle_faccessat(int *dfd, struct filename **filename, int *mode,' \
    kernel_experiment/KernelSU/kernel/feature/sucompat.h
  grep -Fq \
    'int ksu_handle_stat(int *dfd, struct filename **filename, int *flags);' \
    kernel_experiment/KernelSU/kernel/feature/sucompat.h
fi
