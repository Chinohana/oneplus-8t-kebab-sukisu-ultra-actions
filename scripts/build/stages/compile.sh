#!/usr/bin/env bash
set -euo pipefail
export PATH="$BUILD_ROOT/toolchains/clang/bin:$PATH"
export KBUILD_BUILD_USER=github-actions
export KBUILD_BUILD_HOST=github
SOURCE_DATE_EPOCH="$(
  git -C kernel_experiment show -s --format=%ct "$KERNEL_COMMIT"
)"
export SOURCE_DATE_EPOCH
export KBUILD_BUILD_TIMESTAMP="@$SOURCE_DATE_EPOCH"
export KBUILD_BUILD_VERSION=1
build_kernel() {
  local tree="$1"
  local out="$2"
  local log="$3"
  local ccache_stage="$4"

  cd "$BUILD_ROOT/$tree"
  set +e
  if test "$USE_CCACHE" = "true"; then
    CCACHE_DIR="$BUILD_ROOT/.ccache/$ccache_stage" \
    make -j"${BUILD_JOBS:-$(nproc --all)}" O="$out" ARCH=arm64 \
      LLVM=1 LLVM_IAS=1 \
      CC="ccache clang" \
      KSU_VERSION="$SUKISU_DRIVER_VERSION" \
      KCFLAGS="-Wno-error" Image 2>&1 |
      tee "$BUILD_ROOT/$log"
  else
    make -j"${BUILD_JOBS:-$(nproc --all)}" O="$out" ARCH=arm64 \
      LLVM=1 LLVM_IAS=1 \
      KSU_VERSION="$SUKISU_DRIVER_VERSION" \
      KCFLAGS="-Wno-error" Image 2>&1 |
      tee "$BUILD_ROOT/$log"
  fi
  local build_status="${PIPESTATUS[0]}"
  set -e
  test "$build_status" -eq 0
  test -s "$out/arch/arm64/boot/Image"
  test -s "$out/vmlinux"
  test -s "$out/System.map"
  cd "$BUILD_ROOT"
}

# Compile exactly the selected configuration. No baseline or intermediate Image.
build_kernel kernel_experiment "$SELECTED_OUT" audit/build-selected.log "selected-$PROFILE-$CCACHE_HIDE_TAG"
