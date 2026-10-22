#!/usr/bin/env bash
set -euo pipefail
export PATH="$BUILD_ROOT/toolchains/clang/bin:$PATH"

susfs_children_off() {
  local config="$1"
  local option
  for option in \
    KSU_SUSFS_SUS_PATH \
    KSU_SUSFS_SUS_MOUNT \
    KSU_SUSFS_SUS_KSTAT \
    KSU_SUSFS_SPOOF_UNAME \
    KSU_SUSFS_ENABLE_LOG \
    KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS \
    KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG \
    KSU_SUSFS_OPEN_REDIRECT \
    KSU_SUSFS_SUS_MAP; do
    scripts/config --file "$config" -d "$option"
  done
}

configure_tree() {
  local tree="$1"
  local out="$2"
  local profile="$3"

  cd "$BUILD_ROOT/$tree"
  make O="$out" ARCH=arm64 LLVM=1 LLVM_IAS=1 \
    KSU_VERSION="$SUKISU_DRIVER_VERSION" \
    "$KERNEL_DEFCONFIG"
  scripts/kconfig/merge_config.sh -m -O "$out" \
    "$out/.config" "arch/arm64/configs/$OPLUS_CONFIG"

  scripts/config --file "$out/.config" -e KSU
  scripts/config --file "$out/.config" -d KPROBES
  scripts/config --file "$out/.config" -d KPROBE_EVENTS
  scripts/config --file "$out/.config" -d KPM
  scripts/config --file "$out/.config" -e KALLSYMS
  scripts/config --file "$out/.config" -e KALLSYMS_ALL
  if test "$tree" = kernel_experiment && \
     test "$ENABLE_SELINUX_HIDE" = "true"; then
    scripts/config --file "$out/.config" \
      -e KSU_SELINUX_HIDE_4_19
  fi
  susfs_children_off "$out/.config"

  if test "$profile" = baseline || \
     test "$ENABLE_SUSFS" != "true"; then
    scripts/config --file "$out/.config" -d KSU_SUSFS
  else
    scripts/config --file "$out/.config" -e KSU_SUSFS
    scripts/config --file "$out/.config" -e KSU_SUSFS_ENABLE_LOG
    if test "$profile" = minimal-mount ||
       test "$profile" = extended-stat ||
       test "$profile" = extended-full; then
      scripts/config --file "$out/.config" \
        -e KSU_SUSFS_SUS_MOUNT
    fi
    if test "$profile" = extended-stat ||
       test "$profile" = extended-full; then
      scripts/config --file "$out/.config" \
        -e KSU_SUSFS_SUS_KSTAT
    fi
    if test "$profile" = extended-full; then
      for option in \
        KSU_SUSFS_SUS_PATH \
        KSU_SUSFS_SPOOF_UNAME \
        KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS \
        KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG \
        KSU_SUSFS_OPEN_REDIRECT \
        KSU_SUSFS_SUS_MAP; do
        scripts/config --file "$out/.config" -e "$option"
      done
    fi
  fi

  make O="$out" ARCH=arm64 LLVM=1 LLVM_IAS=1 \
    KSU_VERSION="$SUKISU_DRIVER_VERSION" olddefconfig
  cd "$BUILD_ROOT"
}

verify_common_config() {
  local config="$1"
  grep -q '^CONFIG_KSU=y$' "$config"
  grep -q '^CONFIG_KALLSYMS=y$' "$config"
  grep -q '^CONFIG_KALLSYMS_ALL=y$' "$config"
  grep -q '^# CONFIG_KPROBES is not set$' "$config"
  grep -q '^# CONFIG_KPM is not set$' "$config"
  if grep -Eq \
    '^CONFIG_(KPROBES|KPROBE_EVENTS|KPM)=[ym]$' "$config"; then
    echo "::error::KPM or kprobes was enabled."
    exit 1
  fi
}

verify_selinux_hide_config() {
  local config="$1"
  grep -q '^CONFIG_KSU_SELINUX_HIDE_4_19=y$' "$config"
  grep -q '^CONFIG_SECURITY_SELINUX=y$' "$config"
  grep -q '^CONFIG_SECURITY_SELINUX_DEVELOP=y$' "$config"
}

verify_susfs_profile() {
  local config="$1"
  local profile="$2"
  local expected="$BUILD_TEMP/$profile.susfs-enabled.expected"
  local actual="$BUILD_TEMP/$profile.susfs-enabled.actual"

  case "$profile" in
    smoke)
      printf '%s\n' \
        CONFIG_KSU_SUSFS \
        CONFIG_KSU_SUSFS_ENABLE_LOG > "$expected"
      ;;
    minimal-mount)
      printf '%s\n' \
        CONFIG_KSU_SUSFS \
        CONFIG_KSU_SUSFS_ENABLE_LOG \
        CONFIG_KSU_SUSFS_SUS_MOUNT > "$expected"
      ;;
    extended-stat)
      printf '%s\n' \
        CONFIG_KSU_SUSFS \
        CONFIG_KSU_SUSFS_ENABLE_LOG \
        CONFIG_KSU_SUSFS_SUS_KSTAT \
        CONFIG_KSU_SUSFS_SUS_MOUNT > "$expected"
      ;;
    extended-full)
      printf '%s\n' \
        CONFIG_KSU_SUSFS \
        CONFIG_KSU_SUSFS_ENABLE_LOG \
        CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS \
        CONFIG_KSU_SUSFS_OPEN_REDIRECT \
        CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG \
        CONFIG_KSU_SUSFS_SPOOF_UNAME \
        CONFIG_KSU_SUSFS_SUS_KSTAT \
        CONFIG_KSU_SUSFS_SUS_MAP \
        CONFIG_KSU_SUSFS_SUS_MOUNT \
        CONFIG_KSU_SUSFS_SUS_PATH > "$expected"
      ;;
    *)
      echo "::error::Unknown SUSFS profile: $profile"
      exit 1
      ;;
  esac
  LC_ALL=C sort -o "$expected" "$expected"
  sed -n \
    's/^\(CONFIG_KSU_SUSFS\(_[A-Z0-9_]*\)\?\)=y$/\1/p' \
    "$config" |
    LC_ALL=C sort -u > "$actual"
  diff -u "$expected" "$actual"
  if grep -Eq '^CONFIG_KSU_SUSFS(_[A-Z0-9_]+)?=m$' "$config"; then
    echo "::error::A SUSFS option was built as a module."
    exit 1
  fi
}

configure_tree kernel_baseline out-baseline baseline
verify_common_config kernel_baseline/out-baseline/.config
grep -q '^# CONFIG_KSU_SUSFS is not set$' \
  kernel_baseline/out-baseline/.config
if grep -Eq '^CONFIG_KSU_SUSFS(_[A-Z0-9_]+)?=[ym]$' \
  kernel_baseline/out-baseline/.config; then
  echo "::error::SUSFS was enabled in the baseline."
  exit 1
fi

if test "$ENABLE_SUSFS" = "true"; then
  configure_tree kernel_experiment out-smoke smoke
  verify_common_config kernel_experiment/out-smoke/.config
  verify_susfs_profile kernel_experiment/out-smoke/.config smoke
  if test "$ENABLE_SELINUX_HIDE" = "true"; then
    verify_selinux_hide_config \
      kernel_experiment/out-smoke/.config
  fi

  if test "$PROFILE" = minimal-mount ||
     test "$PROFILE" = extended-stat ||
     test "$PROFILE" = extended-full; then
    configure_tree kernel_experiment out-minimal-mount \
      minimal-mount
    verify_common_config \
      kernel_experiment/out-minimal-mount/.config
    verify_susfs_profile \
      kernel_experiment/out-minimal-mount/.config minimal-mount
    if test "$ENABLE_SELINUX_HIDE" = "true"; then
      verify_selinux_hide_config \
        kernel_experiment/out-minimal-mount/.config
    fi

    cmp \
      <(sed \
        '/^CONFIG_KSU_SUSFS_SUS_MOUNT=/d;
         /^# CONFIG_KSU_SUSFS_SUS_MOUNT is not set$/d' \
        kernel_experiment/out-smoke/.config) \
      <(sed \
        '/^CONFIG_KSU_SUSFS_SUS_MOUNT=/d;
         /^# CONFIG_KSU_SUSFS_SUS_MOUNT is not set$/d' \
        kernel_experiment/out-minimal-mount/.config)
  fi

  if test "$PROFILE" = extended-stat; then
    configure_tree kernel_experiment out-extended-stat \
      extended-stat
    verify_common_config \
      kernel_experiment/out-extended-stat/.config
    verify_susfs_profile \
      kernel_experiment/out-extended-stat/.config extended-stat
    if test "$ENABLE_SELINUX_HIDE" = "true"; then
      verify_selinux_hide_config \
        kernel_experiment/out-extended-stat/.config
    fi

    cmp \
      <(sed \
        '/^CONFIG_KSU_SUSFS_SUS_KSTAT=/d;
         /^# CONFIG_KSU_SUSFS_SUS_KSTAT is not set$/d' \
        kernel_experiment/out-minimal-mount/.config) \
      <(sed \
        '/^CONFIG_KSU_SUSFS_SUS_KSTAT=/d;
         /^# CONFIG_KSU_SUSFS_SUS_KSTAT is not set$/d' \
        kernel_experiment/out-extended-stat/.config)
  fi

  if test "$PROFILE" = extended-full; then
    configure_tree kernel_experiment out-extended-full \
      extended-full
    verify_common_config \
      kernel_experiment/out-extended-full/.config
    verify_susfs_profile \
      kernel_experiment/out-extended-full/.config extended-full
    if test "$ENABLE_SELINUX_HIDE" = "true"; then
      verify_selinux_hide_config \
        kernel_experiment/out-extended-full/.config
    fi

    cmp \
      <(sed -E \
        '/^CONFIG_KSU_SUSFS_(SUS_PATH|SUS_KSTAT|SPOOF_UNAME|HIDE_KSU_SUSFS_SYMBOLS|SPOOF_CMDLINE_OR_BOOTCONFIG|OPEN_REDIRECT|SUS_MAP)=/d;
         /^# CONFIG_KSU_SUSFS_(SUS_PATH|SUS_KSTAT|SPOOF_UNAME|HIDE_KSU_SUSFS_SYMBOLS|SPOOF_CMDLINE_OR_BOOTCONFIG|OPEN_REDIRECT|SUS_MAP) is not set$/d' \
        kernel_experiment/out-minimal-mount/.config) \
      <(sed -E \
        '/^CONFIG_KSU_SUSFS_(SUS_PATH|SUS_KSTAT|SPOOF_UNAME|HIDE_KSU_SUSFS_SYMBOLS|SPOOF_CMDLINE_OR_BOOTCONFIG|OPEN_REDIRECT|SUS_MAP)=/d;
         /^# CONFIG_KSU_SUSFS_(SUS_PATH|SUS_KSTAT|SPOOF_UNAME|HIDE_KSU_SUSFS_SYMBOLS|SPOOF_CMDLINE_OR_BOOTCONFIG|OPEN_REDIRECT|SUS_MAP) is not set$/d' \
        kernel_experiment/out-extended-full/.config)
  fi

  kernel_experiment/scripts/diffconfig \
    kernel_baseline/out-baseline/.config \
    kernel_experiment/out-smoke/.config \
    > audit/config-baseline-to-smoke.diff
  if test "$PROFILE" = minimal-mount; then
    kernel_experiment/scripts/diffconfig \
      kernel_experiment/out-smoke/.config \
      kernel_experiment/out-minimal-mount/.config \
      > audit/config-smoke-to-minimal-mount.diff
  fi
  if test "$PROFILE" = extended-stat; then
    kernel_experiment/scripts/diffconfig \
      kernel_experiment/out-smoke/.config \
      kernel_experiment/out-minimal-mount/.config \
      > audit/config-smoke-to-minimal-mount.diff
    kernel_experiment/scripts/diffconfig \
      kernel_experiment/out-minimal-mount/.config \
      kernel_experiment/out-extended-stat/.config \
      > audit/config-minimal-mount-to-extended-stat.diff
    test "$(
      wc -l < audit/config-minimal-mount-to-extended-stat.diff
    )" -eq 1
    grep -Fqx ' KSU_SUSFS_SUS_KSTAT n -> y' \
      audit/config-minimal-mount-to-extended-stat.diff
  fi
  if test "$PROFILE" = extended-full; then
    kernel_experiment/scripts/diffconfig \
      kernel_experiment/out-smoke/.config \
      kernel_experiment/out-minimal-mount/.config \
      > audit/config-smoke-to-minimal-mount.diff
    kernel_experiment/scripts/diffconfig \
      kernel_experiment/out-minimal-mount/.config \
      kernel_experiment/out-extended-full/.config \
      > audit/config-minimal-mount-to-extended-full.diff
    test "$(
      wc -l < audit/config-minimal-mount-to-extended-full.diff
    )" -eq 7
    for option in \
      KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS \
      KSU_SUSFS_OPEN_REDIRECT \
      KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG \
      KSU_SUSFS_SPOOF_UNAME \
      KSU_SUSFS_SUS_KSTAT \
      KSU_SUSFS_SUS_MAP \
      KSU_SUSFS_SUS_PATH; do
      grep -Fqx " ${option} n -> y" \
        audit/config-minimal-mount-to-extended-full.diff
    done
  fi
else
  configure_tree kernel_experiment out-selected selected
  verify_common_config \
    kernel_experiment/out-selected/.config
  grep -q '^# CONFIG_KSU_SUSFS is not set$' \
    kernel_experiment/out-selected/.config
  if grep -Eq '^CONFIG_KSU_SUSFS(_[A-Z0-9_]+)?=[ym]$' \
    kernel_experiment/out-selected/.config; then
    echo "::error::SUSFS was enabled without enable_susfs."
    exit 1
  fi
  if test "$ENABLE_SELINUX_HIDE" = "true"; then
    verify_selinux_hide_config \
      kernel_experiment/out-selected/.config
  fi
  kernel_experiment/scripts/diffconfig \
    kernel_baseline/out-baseline/.config \
    kernel_experiment/out-selected/.config \
    > audit/config-baseline-to-selected.diff
fi
