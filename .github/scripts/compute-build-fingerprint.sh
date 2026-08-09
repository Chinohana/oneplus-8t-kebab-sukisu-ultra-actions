#!/usr/bin/env bash
set -euo pipefail

root="${1:-$PWD}"
output_dir="${2:-$root/audit}"
mkdir -p "$output_dir"

source "$root/.github/scripts/load-build-pins.sh" "$root"
kernel_commit="$("$root/.github/scripts/resolve-kernel-pin.sh" "$root" | tail -n1)"

enable_susfs="${ENABLE_SUSFS:-true}"
susfs_profile="${SUSFS_PROFILE:-extended-full}"
enable_selinux_hide="${ENABLE_SELINUX_HIDE:-true}"
use_anykernel="${USE_ANYKERNEL:-true}"
build_channel="${BUILD_CHANNEL:-approved}"

case "$enable_susfs:$enable_selinux_hide:$use_anykernel" in
  true:true:true|true:true:false|true:false:true|true:false:false|\
  false:true:true|false:true:false|false:false:true|false:false:false) ;;
  *) echo "Invalid boolean build input" >&2; exit 1 ;;
esac
case "$susfs_profile" in
  smoke|minimal-mount|extended-stat|extended-full) ;;
  *) echo "Invalid SUSFS profile: $susfs_profile" >&2; exit 1 ;;
esac
case "$build_channel" in
  approved|candidate|unapproved_latest) ;;
  *) echo "Invalid build channel: $build_channel" >&2; exit 1 ;;
esac

file_hashes="$output_dir/build-input-files.sha256"
git -C "$root" ls-files -z -- \
  .gitmodules \
  config/build-pins.env \
  config/migration-baseline-lineage-23.2.sha256 \
  '.github/scripts/*.sh' \
  .github/workflows/build-sukisu-ultra.yml \
  'patches/*.patch' |
  LC_ALL=C sort -z |
  while IFS= read -r -d '' file; do
    hash="$(sha256sum < "$root/$file" | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$file"
  done > "$file_hashes"
test -s "$file_hashes"

inputs="$output_dir/build-inputs.txt"
{
  echo 'fingerprint_schema=1'
  echo 'device=kebab'
  echo 'rom=LineageOS 23.2'
  echo "kernel_repository=$KERNEL_REPOSITORY"
  echo "kernel_branch=$KERNEL_BRANCH"
  echo "kernel_commit=$kernel_commit"
  echo "kernel_defconfig=$KERNEL_DEFCONFIG"
  echo "oplus_config=$OPLUS_CONFIG"
  echo "sukisu_repository=$SUKISU_REPOSITORY"
  echo "sukisu_branch=$SUKISU_BRANCH"
  echo "sukisu_commit=$SUKISU_COMMIT"
  echo "sukisu_driver_version=$SUKISU_DRIVER_VERSION"
  echo "susfs_repository=$SUSFS_REPOSITORY"
  echo "susfs_commit=$SUSFS_COMMIT"
  echo "susfs_version=$SUSFS_VERSION"
  echo "sm8250_reference_repository=$SM8250_REFERENCE_REPOSITORY"
  echo "sm8250_reference_commit=$SM8250_REFERENCE_COMMIT"
  echo "sm8250_reference_base_commit=$SM8250_REFERENCE_BASE_COMMIT"
  echo "clang_revision=$CLANG_REVISION"
  echo "clang_archive_commit=$CLANG_ARCHIVE_COMMIT"
  echo "anykernel_repository=$ANYKERNEL_REPOSITORY"
  echo "anykernel_commit=$ANYKERNEL_COMMIT"
  echo "android_ndk_version=$ANDROID_NDK_VERSION"
  echo "enable_susfs=$enable_susfs"
  echo "susfs_profile=$susfs_profile"
  echo "enable_selinux_hide=$enable_selinux_hide"
  echo "use_anykernel=$use_anykernel"
  cat "$file_hashes"
} > "$inputs"

fingerprint="$(sha256sum < "$inputs" | awk '{print $1}')"
printf '%s  build-inputs.txt\n' "$fingerprint" \
  > "$output_dir/build-inputs.txt.sha256"
printf '%s\n' "$fingerprint"
