#!/usr/bin/env bash
# Install user-downloaded Linux tools into this distro's ext4 workspace.
set -Eeuo pipefail
toolchain_failure() {
  local failure_status="$?"
  printf 'Toolchain installation failed (exit %s); env.sh was not updated.\n' "$failure_status" >&2
  exit "$failure_status"
}
trap toolchain_failure ERR
storage="${BUILD_STORAGE:-$HOME/oneplus8t-build}"
workspace="${BUILD_WORKSPACE:-$HOME/oneplus8t-kernel}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$root/.github/scripts/load-build-pins.sh" "$root"
clang_archive="$storage/downloads/clang-r614150-linux-x86.tar.gz"
ndk_archive="$storage/downloads/android-ndk-r30-linux.zip"
if ! test -f "$clang_archive"; then
  clang_archive="$storage/downloads/linux-x86-a83b2dbffadbe45e7ec16e68498723a1e418fa19-clang-r614150.tar.gz"
fi
test "$(uname -m)" = x86_64
for archive in "$clang_archive" "$ndk_archive"; do
  if ! test -f "$archive"; then
    printf 'Required download not found: %s\n' "$archive" >&2
    exit 1
  fi
done
test -d "$workspace/audit"
test "$(findmnt -n -T "$workspace" -o FSTYPE)" = ext4
test ! -e "$workspace/toolchains/clang-r614150"
test ! -e "$workspace/toolchains/android-ndk-r30"
printf '%s  %s\n' 5107f898313790e449e87eee2183d9a20602dee9 "$ndk_archive" | sha1sum -c -
printf 'Recording download hashes...\n'
sha256sum "$clang_archive" "$ndk_archive" > "$workspace/audit/toolchain-downloads.sha256"
mkdir -p "$workspace/toolchains/clang-r614150"
printf 'Extracting Clang into ext4 workspace...\n'
tar -xzf "$clang_archive" -C "$workspace/toolchains/clang-r614150"
printf 'Extracting NDK into ext4 workspace...\n'
unzip -q "$ndk_archive" -d "$workspace/toolchains"
clang_root="$workspace/toolchains/clang-r614150"
ndk_root="$workspace/toolchains/android-ndk-r30"
test -x "$clang_root/bin/clang"
test -x "$clang_root/bin/ld.lld"
test -x "$clang_root/bin/llvm-nm"
test -x "$ndk_root/ndk-build"
grep -Fq "Pkg.Revision = $ANDROID_NDK_VERSION" "$ndk_root/source.properties"
"$clang_root/bin/clang" --version | tee "$workspace/audit/clang-version.txt"
cat > "$workspace/env.sh" <<'EOF'
export KERNEL_LAB="$HOME/oneplus8t-kernel"
export CLANG_ROOT="$KERNEL_LAB/toolchains/clang-r614150"
export ANDROID_NDK_ROOT="$KERNEL_LAB/toolchains/android-ndk-r30"
export PATH="$CLANG_ROOT/bin:$ANDROID_NDK_ROOT:$PATH"
export CCACHE_DIR="$KERNEL_LAB/cache/ccache"
export ARCH=arm64
export LLVM=1
export LLVM_IAS=1
EOF
printf 'Tools ready. Run: source ~/oneplus8t-kernel/env.sh\n'
