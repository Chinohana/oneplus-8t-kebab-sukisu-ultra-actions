#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts/kernel/audit
migration_equivalence=not-applicable

if test "$USE_ANYKERNEL" = "true"; then
  cp "${PACKAGE_NAME}.zip" "${PACKAGE_NAME}.zip.sha256" \
    artifacts/kernel/
else
  cp "kernel_experiment/$SELECTED_OUT/arch/arm64/boot/Image" \
    artifacts/kernel/Image
  sha256sum artifacts/kernel/Image \
    > artifacts/kernel/Image.sha256
fi
cp -a audit/. artifacts/kernel/audit/
cp "kernel_experiment/$SELECTED_OUT/.config" \
  artifacts/kernel/selected.config
cp "kernel_experiment/$SELECTED_OUT/System.map" \
  artifacts/kernel/selected.System.map
sha256sum \
  artifacts/kernel/selected.config \
  artifacts/kernel/selected.System.map \
  "kernel_experiment/$SELECTED_OUT/arch/arm64/boot/Image" \
  > artifacts/kernel/selected-build-files.sha256

if test "$ROM_VERSION" = 23.2 &&
   test "$KERNEL_COMMIT" = "$SM8250_REFERENCE_BASE_COMMIT" &&
   test "$ENABLE_SUSFS" = true &&
   test "$PROFILE" = extended-full &&
   test "$ENABLE_SELINUX_HIDE" = true; then
  {
    sha256sum artifacts/kernel/selected.config |
      awk '{print $1 "  selected.config"}'
    sha256sum artifacts/kernel/selected.System.map |
      awk '{print $1 "  selected.System.map"}'
    sha256sum \
      "kernel_experiment/$SELECTED_OUT/arch/arm64/boot/Image" |
      awk '{print $1 "  Image"}'
  } > "$BUILD_TEMP/migration-current.sha256"
  grep -v '^#' config/migration-baseline-lineage-23.2.sha256 \
    > "$BUILD_TEMP/migration-approved.sha256"
  cp "$BUILD_TEMP/migration-current.sha256" \
    artifacts/kernel/audit/migration-equivalence.sha256
  if diff -u "$BUILD_TEMP/migration-approved.sha256" \
    "$BUILD_TEMP/migration-current.sha256" \
    > artifacts/kernel/audit/migration-equivalence.diff; then
    migration_equivalence=identical
  else
    migration_equivalence=different-phone-retest-required
    echo "::warning::Image/config/System.map differ from the approved migration baseline; a new phone test is required."
  fi
fi

{
  echo "status=${BUILD_CHANNEL^^}_DO_NOT_AUTO_INSTALL"
  echo "device=kebab"
  echo "model=OnePlus 8T"
  echo "rom=LineageOS $ROM_VERSION"
  echo "android_api=$ANDROID_API"
  if test "$ENABLE_SUSFS" = "true"; then
    echo "profile=$PROFILE"
  else
    echo "profile=selected"
  fi
  echo "enable_susfs=$ENABLE_SUSFS"
  echo "enable_selinux_hide=$ENABLE_SELINUX_HIDE"
  echo "use_anykernel=$USE_ANYKERNEL"
  echo "build_channel=$BUILD_CHANNEL"
  echo "build_fingerprint=$BUILD_FINGERPRINT"
  echo "base_kernel_commit=$BASE_KERNEL_COMMIT"
  echo "migration_equivalence=$migration_equivalence"
  echo "builder_commit=$BUILDER_COMMIT"
  echo "builder_base_commit=$BUILDER_BASE_COMMIT"
  echo "execution_environment=${EXECUTION_ENVIRONMENT:-github-actions}"
  if test "${EXECUTION_ENVIRONMENT:-github-actions}" = local-wsl2; then
    echo "local_run_id=$LOCAL_RUN_ID"
  else
    echo "github_run_id=$GITHUB_RUN_ID"
    echo "github_run_attempt=$GITHUB_RUN_ATTEMPT"
  fi
  echo "kernel_repository=$KERNEL_REPOSITORY"
  echo "kernel_branch=$KERNEL_BRANCH"
  echo "kernel_commit=$KERNEL_COMMIT"
  echo "defconfig=$KERNEL_DEFCONFIG+$OPLUS_CONFIG"
  echo "sukisu_repository=$SUKISU_REPOSITORY"
  echo "sukisu_branch=$SUKISU_BRANCH"
  echo "sukisu_commit=$SUKISU_COMMIT"
  echo "sukisu_driver_version=$SUKISU_DRIVER_VERSION"
  if test "$ENABLE_SUSFS" = "true"; then
    echo "susfs_repository=$SUSFS_REPOSITORY"
    echo "susfs_commit=$SUSFS_COMMIT"
    echo "susfs_version=$SUSFS_VERSION"
    echo "susfs_variant=NON-GKI"
    echo "sm8250_reference_repository=$SM8250_REFERENCE_REPOSITORY"
    echo "sm8250_reference_commit=$SM8250_REFERENCE_COMMIT"
  fi
  if test "$ENABLE_SELINUX_HIDE" = "true"; then
    echo "selinux_hide_port=linux-4.19"
  fi
  echo "hook=manual-inline-combined"
  echo "kprobes=n"
  echo "kpm=n"
  echo "selinux_policy_modified=n"
  echo "ramdisk_modified=n"
  echo "dtb_modified=n"
  echo "dtbo_modified=n"
  echo "vendor_boot_modified=n"
  echo "init_boot_modified=n"
  echo "anykernel_repository=$ANYKERNEL_REPOSITORY"
  echo "anykernel_commit=$ANYKERNEL_COMMIT"
  echo "clang_revision=$CLANG_REVISION"
  echo "clang_archive_commit=$CLANG_ARCHIVE_COMMIT"
  echo "clang=$(
    "$BUILD_ROOT/toolchains/clang/bin/clang" \
      --version | head -n1
  )"
  echo "android_ndk_version=$ANDROID_NDK_VERSION"
  if test "$USE_ANYKERNEL" = "true"; then
    echo "package=${PACKAGE_NAME}.zip"
    cat "${PACKAGE_NAME}.zip.sha256"
  else
    echo "package=${PACKAGE_NAME} (raw Image/System.map/config)"
    cat artifacts/kernel/Image.sha256
  fi
  cat audit/patches.sha256
  cat artifacts/kernel/selected-build-files.sha256
} | tee artifacts/kernel/build-provenance.txt

if test "$ENABLE_SUSFS" = "true"; then
  {
    echo "status=${BUILD_CHANNEL^^}_TEST_ATTACHMENT_DO_NOT_AUTO_INSTALL"
    echo "source_repository=$SUSFS_REPOSITORY"
    echo "source_commit=$SUSFS_COMMIT"
    echo "susfs_version=$SUSFS_VERSION"
    echo "abi=arm64-v8a"
    echo "android_ndk_version=$ANDROID_NDK_VERSION"
    echo "builder_commit=$BUILDER_COMMIT"
    cat artifacts/tool/ksu_susfs-v2.3.0-arm64.sha256
  } | tee artifacts/tool/tool-provenance.txt
fi

sha256sum artifacts/kernel/build-provenance.txt \
  > artifacts/kernel/build-provenance.txt.sha256
if test "$ENABLE_SUSFS" = "true"; then
  sha256sum artifacts/tool/tool-provenance.txt \
    > artifacts/tool/tool-provenance.txt.sha256
fi
