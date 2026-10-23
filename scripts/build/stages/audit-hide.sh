#!/usr/bin/env bash
set -euo pipefail

ksu_dir=kernel_experiment/KernelSU/kernel
test "$(grep -Fc 'ksu_selinux_hide_init();' "$ksu_dir/ksu_main.c")" = 1
test "$(grep -Fc 'ksu_selinux_hide_handle_post_fs_data();' "$ksu_dir/runtime/ksud.c")" = 1
test "$(grep -Fc 'ksu_selinux_hide_handle_second_stage();' "$ksu_dir/runtime/ksud.c")" = 2
test "$(grep -Fc 'ksu_selinux_hide_drop_backup_if_unused();' "$ksu_dir/runtime/ksud.c")" = 1

grep -Fq 'fake_state.ss = backup_selinux_ss;' \
  "$ksu_dir/feature/selinux_hide.c"
grep -Fq 'fake_state = selinux_state;' \
  "$ksu_dir/feature/selinux_hide.c"
grep -Fq 'selinux_state.ss->status_lock' \
  "$ksu_dir/feature/selinux_hide.c"
grep -Fq 'ksu_selinux_hide_backup_was_dropped' \
  "$ksu_dir/feature/selinux_hide.c"
grep -Fq 'selinux_hide: queued for the next boot' \
  "$ksu_dir/feature/selinux_hide.c"
grep -Fq 'read_lock(&old_ss->policy_rwlock);' \
  "$ksu_dir/selinux/sepolicy.c"
grep -Fq 'snapshot->latest_granting == selinux_state.ss->latest_granting' \
  "$ksu_dir/selinux/rules.c"

if sed -n '/#if LINUX_VERSION_CODE < KERNEL_VERSION(5, 10, 0)/,/#else/p' \
    "$ksu_dir/feature/selinux_hide.c" |
    grep -Eq 'selinux_state\.(policy|policy_mutex|status_lock|status_page)'; then
  echo "::error::Linux 4.19 code references a Linux 5.10 SELinux field."
  exit 1
fi

# Keep this audit list explicit so newly backported files can be added here.
# shellcheck disable=SC2043
for file in security/selinux/selinuxfs.c; do
  grep -Fq CONFIG_KSU_SELINUX_HIDE_4_19 \
    "kernel_experiment/$file"
done
grep -Fq 'READ_ONCE(ksu_selinux_hide_running)' \
  kernel_experiment/security/selinux/selinuxfs.c

sed -n '/^#else \/\* Linux 4.19 \*\//,$p' \
  "$ksu_dir/feature/selinux_hide.c" > "$BUILD_TEMP/selinux-hide-4.19.c"
if grep -Eq 'kprobe|patch_text|find_kernel_symbol' \
    "$BUILD_TEMP/selinux-hide-4.19.c" \
    kernel_experiment/security/selinux/selinuxfs.c; then
  echo "::error::Runtime hooking was introduced by the 4.19 port."
  exit 1
fi
