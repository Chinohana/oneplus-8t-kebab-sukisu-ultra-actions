#!/usr/bin/env bash
# Build one user-selected configuration in a user's GitHub repository.
set -Eeuo pipefail
test "${GITHUB_ACTIONS:-}" = true
test "$GITHUB_REPOSITORY" != Chinohana/oneplus-8t-kebab-sukisu-ultra-actions
export BUILD_ROOT="$GITHUB_WORKSPACE"
export BUILD_TEMP="$RUNNER_TEMP/kernel-build"
export BUILD_ENV="$BUILD_TEMP/environment"
export BUILD_SUMMARY="$GITHUB_STEP_SUMMARY"
export BUILDER_COMMIT="$GITHUB_SHA"
export EXECUTION_ENVIRONMENT=github-actions
export BUILD_CHANNEL=candidate
export USE_ANYKERNEL=true
export USE_CCACHE=true
export BUILD_JOBS="$(nproc)"
mkdir -p "$BUILD_TEMP" "$BUILD_ROOT/audit" "$BUILD_ROOT/.ccache" "$BUILD_ROOT/toolchains/clang"
touch "$BUILD_ENV"
cd "$BUILD_ROOT"
source .github/scripts/load-build-pins.sh "$BUILD_ROOT"
case "$ENABLE_SUSFS:$ENABLE_SELINUX_HIDE" in
  true:true|true:false|false:true|false:false) ;;
  *) echo 'Invalid feature selection' >&2; exit 1 ;;
esac
case "$SUSFS_PROFILE" in
  smoke|minimal-mount|extended-stat|extended-full) ;;
  *) echo 'Invalid SUSFS profile' >&2; exit 1 ;;
esac
curl -fL --retry 3 \
  "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/${CLANG_ARCHIVE_COMMIT}/${CLANG_REVISION}.tar.gz" \
  -o "$BUILD_TEMP/clang.tar.gz"
sha256sum "$BUILD_TEMP/clang.tar.gz" > audit/toolchain-downloads.sha256
tar -xzf "$BUILD_TEMP/clang.tar.gz" -C toolchains/clang
toolchains/clang/bin/clang --version | tee audit/clang-version.txt
grep -Fq "${CLANG_REVISION#clang-}" audit/clang-version.txt
rm "$BUILD_TEMP/clang.tar.gz"
if test "$ENABLE_SUSFS" = true; then
  curl -fL --retry 3 https://dl.google.com/android/repository/android-ndk-r27c-linux.zip -o "$BUILD_TEMP/ndk.zip"
  printf '%s  %s\n' 090e8083a715fdb1a3e402d0763c388abb03fb4e "$BUILD_TEMP/ndk.zip" | sha1sum -c -
  sha256sum "$BUILD_TEMP/ndk.zip" >> audit/toolchain-downloads.sha256
  unzip -q "$BUILD_TEMP/ndk.zip" -d toolchains
  rm "$BUILD_TEMP/ndk.zip"
  export ANDROID_NDK_ROOT="$BUILD_ROOT/toolchains/android-ndk-r27c"
  grep -Fq "Pkg.Revision = $ANDROID_NDK_VERSION" "$ANDROID_NDK_ROOT/source.properties"
fi
export KERNEL_COMMIT="$(bash .github/scripts/resolve-kernel-pin.sh "$BUILD_ROOT" | tail -n1)"
export BASE_KERNEL_COMMIT="$KERNEL_COMMIT"
stages=(baseline-identity fingerprint)
if test "$ENABLE_SUSFS" = true; then stages+=(references); fi
stages+=(patch-preflight source patches audit-hide audit-susfs audit-hooks configure cache-configure compile cache-stats audit-build)
if test "$ENABLE_SUSFS" = true; then stages+=(tool); fi
stages+=(package provenance)
for stage in "${stages[@]}"; do
  echo "STAGE $stage"
  bash scripts/build/run-stage.sh "$stage" 2>&1 | tee -a audit/custom-action.log
done
python3 scripts/build/verify-artifacts.py artifacts
