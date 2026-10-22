#!/usr/bin/env bash
set -euo pipefail

feature_tags=""
string_feature=""
if test "$ENABLE_SUSFS" = "true"; then
  feature_tags="${PROFILE}"
  string_feature="SUSFS v2.3 ${PROFILE}"
else
  feature_tags="nosusfs"
  string_feature="no SUSFS"
fi
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  feature_tags="${feature_tags}-hide"
  string_feature="${string_feature} SELinux hide"
fi

package_name="${BUILD_CHANNEL^^}_RAW_SukiSU_kebab_LOS${ROM_VERSION}_${feature_tags}_K${KERNEL_COMMIT:0:7}_SU${SUKISU_COMMIT:0:7}_KSU${SUKISU_DRIVER_VERSION}"
echo "PACKAGE_NAME=$package_name" >> "$BUILD_ENV"
echo "KERNEL_ARTIFACT_NAME=$package_name" >> "$BUILD_ENV"
