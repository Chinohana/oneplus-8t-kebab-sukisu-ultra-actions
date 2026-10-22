#!/usr/bin/env bash
set -euo pipefail

if test -n "${ANDROID_NDK_ROOT:-}"; then
  ndk_root="$ANDROID_NDK_ROOT"
else
  sdkmanager="$ANDROID_SDK_ROOT/cmdline-tools/latest/bin/sdkmanager"
  test -x "$sdkmanager"
  "$sdkmanager" "ndk;$ANDROID_NDK_VERSION"
  ndk_root="$ANDROID_SDK_ROOT/ndk/$ANDROID_NDK_VERSION"
fi
test -x "$ndk_root/ndk-build"
grep -Fq "Pkg.Revision = $ANDROID_NDK_VERSION" \
  "$ndk_root/source.properties"

export PATH="$ndk_root:$PATH"
cd susfs_reference
bash ./build_ksu_susfs_tool.sh
cd "$BUILD_ROOT"

tool_source="susfs_reference/ksu_susfs/libs/arm64-v8a/ksu_susfs"
test -s "$tool_source"
file "$tool_source" | tee audit/ksu-susfs-tool.file.txt
grep -Eq 'ELF 64-bit.*ARM aarch64' \
  audit/ksu-susfs-tool.file.txt
"$ndk_root/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf" \
  -h -d "$tool_source" \
  > audit/ksu-susfs-tool.readelf.txt

mkdir -p artifacts/tool
cp "$tool_source" \
  artifacts/tool/ksu_susfs-v2.3.0-arm64
sha256sum artifacts/tool/ksu_susfs-v2.3.0-arm64 |
  tee artifacts/tool/ksu_susfs-v2.3.0-arm64.sha256
cp "$ndk_root/source.properties" \
  artifacts/tool/ndk-source.properties

tool_artifact_name="${BUILD_CHANNEL^^}_ksu_susfs-tool_v2.3.0_${PROFILE}_HIDE-${ENABLE_SELINUX_HIDE}_SF-${SUSFS_COMMIT:0:12}_NDK-${ANDROID_NDK_VERSION}_WF-${BUILDER_COMMIT:0:12}"
echo "TOOL_ARTIFACT_NAME=$tool_artifact_name" \
  >> "$BUILD_ENV"
