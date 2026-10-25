#!/usr/bin/env bash
set -euo pipefail

grep -Fqx '#define SUSFS_VERSION "v2.3.0"' \
  kernel_experiment/include/linux/susfs.h
grep -Fqx '#define SUSFS_VARIANT "NON-GKI"' \
  kernel_experiment/include/linux/susfs.h

cmp \
  <(sed -e 's/\r$//' -e 's/[[:space:]]*$//' \
    susfs_reference/kernel_patches/include/linux/susfs.h) \
  <(sed -e 's/\r$//' -e 's/[[:space:]]*$//' \
    kernel_experiment/include/linux/susfs.h)
for definition in \
  '#define TIF_PROC_NO_SU 34' \
  '#define TIF_PROC_UMOUNTED_FOR_ZYGOTE_NEXT 35'; do
  grep -Fqx "$definition" \
    kernel_experiment/include/linux/susfs_def.h
done
for helper in \
  susfs_clear_current_proc_umounted \
  susfs_is_current_proc_umounted_for_zygote_next \
  susfs_set_current_proc_umounted_for_zygote_next \
  susfs_clear_current_proc_umounted_for_zygote_next \
  susfs_is_current_proc_no_su \
  susfs_set_current_proc_no_su \
  susfs_clear_current_proc_no_su; do
  grep -Fq "static inline" \
    kernel_experiment/include/linux/susfs_def.h
  grep -Fq "${helper}(void)" \
    kernel_experiment/include/linux/susfs_def.h
done
grep -Fq \
  'if (susfs_is_current_proc_umounted()) {' \
  kernel_experiment/fs/namespace.c

cmp \
  <(sed -e 's/\r$//' -e 's/[[:space:]]*$//' \
    susfs_reference/kernel_patches/include/linux/susfs_def.h) \
  <(sed -e 's/\r$//' -e 's/[[:space:]]*$//' \
    kernel_experiment/include/linux/susfs_def.h)

grep -Fq \
  'Linux 4.19 delivers the raw child name through fsnotify_ops.handle_event.' \
  kernel_experiment/fs/susfs.c
grep -Fq 'err = -ENOMEM;' kernel_experiment/fs/susfs.c
grep -Fq 'susfs_is_inode_sus_kstat' kernel_experiment/fs/stat.c
grep -Fq 'susfs_statfs_by_dentry' kernel_experiment/fs/statfs.c
python3 "$BUILD_ROOT/scripts/test-susfs-priority-filter.py" kernel_experiment/fs/susfs.c
for file in kernel/sys.c block/ioprio.c; do
  calls="$(grep -Fc '&& susfs_is_priority_uid_filtered(uid.val)' "kernel_experiment/$file")"
  test "$calls" -eq 2
done
grep -Fq 'case CMD_SUSFS_SET_PRIORITY_UID_FILTER:' \
  kernel_experiment/KernelSU/kernel/supercall/dispatch.c
grep -Fq 'susfs_set_priority_uid_filter(arg);' \
  kernel_experiment/KernelSU/kernel/supercall/dispatch.c
grep -Fq 'susfs_parse_priority_app_strings();' \
  kernel_experiment/KernelSU/kernel/manager/pkg_observer.c
grep -Fq 'susfs_sus_kstat_spoof_proc_fd_seq_show' kernel_experiment/fs/proc/fd.c
grep -Fq 'susfs_sus_kstat_spoof_inotify_fdinfo' kernel_experiment/fs/notify/fdinfo.c
grep -Fq \
  '.handle_event = susfs_handle_sdcard_inode_event' \
  kernel_experiment/fs/susfs.c
grep -Fq 'if (!info) {' kernel_experiment/fs/susfs.c
if grep -Fq '.handle_inode_event =' \
  kernel_experiment/fs/susfs.c; then
  echo "::error::The incompatible Linux 6.1 fsnotify callback remains."
  exit 1
fi

if grep -R -Fq \
  -e 'SUSFS_VERSION "v1.5.5"' \
  -e CONFIG_KSU_SUSFS_TRY_UMOUNT \
  -e CONFIG_KSU_SUSFS_AUTO_ADD \
  -e susfs_run_try_umount_for_current_mnt_ns \
  kernel_experiment/fs kernel_experiment/include/linux \
  kernel_experiment/kernel; then
  echo "::error::A legacy SUSFS API or option was introduced."
  exit 1
fi

batch_sid_calls="$(
  grep -Fc 'susfs_set_batch_sid();' \
    kernel_experiment/KernelSU/kernel/selinux/rules.c
)"
if test "$batch_sid_calls" -ne 2; then
  echo "::error::Expected both modern and Linux 4.19 SID-cache calls; found ${batch_sid_calls}."
  exit 1
fi

diff -u \
  susfs_reference/kernel_patches/fs/susfs.c \
  kernel_experiment/fs/susfs.c \
  > audit/susfs-v2.3-to-sm8250-4.19.diff || true
test -s audit/susfs-v2.3-to-sm8250-4.19.diff
