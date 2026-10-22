#!/usr/bin/env bash
set -euo pipefail
fingerprint="$(
  bash .github/scripts/compute-build-fingerprint.sh \
    "$BUILD_ROOT" "$BUILD_ROOT/audit"
)"
ccache_source_fingerprint="$(
  {
    echo 'ccache_schema=3'
    echo "kernel_commit=$KERNEL_COMMIT"
    echo "sukisu_commit=$SUKISU_COMMIT"
    echo "susfs_commit=$SUSFS_COMMIT"
    echo "sm8250_reference_commit=$SM8250_REFERENCE_COMMIT"
    echo "clang_revision=$CLANG_REVISION"
    echo "clang_archive_commit=$CLANG_ARCHIVE_COMMIT"
    echo "sukisu_driver_version=$SUKISU_DRIVER_VERSION"
    cat audit/build-input-files.sha256
  } | sha256sum | awk '{print $1}'
)"
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  ccache_hide_tag=hide
else
  ccache_hide_tag=plain
fi
{
  echo "BUILD_FINGERPRINT=$fingerprint"
  echo "CCACHE_SOURCE_FINGERPRINT=$ccache_source_fingerprint"
  echo "CCACHE_HIDE_TAG=$ccache_hide_tag"
} >> "$BUILD_ENV"
echo "Build fingerprint: $fingerprint"
echo "ccache source fingerprint: $ccache_source_fingerprint"
