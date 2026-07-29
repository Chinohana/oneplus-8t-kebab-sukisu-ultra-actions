# OnePlus 8T `kebab` — LineageOS 23.2 SukiSU Ultra cloud builder

## Current status

There is currently **no tested flashable artifact** from this revised workflow.
The previous `main + kprobe` experiment reached an unsafe Linux 4.19 seccomp
layout mismatch and has been abandoned. This revision instead follows the
official built-in, manual-hook route for non-GKI kernels. A cloud build and
offline artifact review must pass before any ZIP is considered for testing.

This public repository builds a device-specific SukiSU Ultra kernel for:

- OnePlus 8T (`kebab`, SM8250)
- LineageOS 23.2 / Android 16
- Linux 4.19
- LineageOS kernel commit `4238ee49a84b`

The workflow produces an AnyKernel3 ZIP only. It deliberately does not create a
standalone `boot.img`, because repacking the user's known-good, unmodified boot
image locally avoids mixing in a ramdisk or DTB from a different ROM build.

## Upstream workflow provenance

The workflow structure follows
[`ShirkNeko/Action_OnePlus_MKSU_SUSFS`](https://github.com/ShirkNeko/Action_OnePlus_MKSU_SUSFS/blob/main/.github/workflows/Build-SukiSU.yml):

1. verify sufficient native runner storage;
2. configure Git and install dependencies;
3. initialize and sync kernel sources;
4. remove the `-dirty` suffix;
5. integrate a pinned commit from SukiSU Ultra's official `builtin` branch;
6. apply the four documented non-GKI manual hooks plus the current reboot
   bootstrap hook;
7. force SUSFS, KPM and kprobes off and assert the final configuration;
8. build the kernel and verify the manual-hook symbols;
9. package with a pinned AnyKernel3 commit;
10. record full provenance and upload the result as an Actions artifact.

The exact upstream file reviewed when this repository was created contained 442
lines and had SHA-256:

```text
71A59CF8B6A5B93E56267F8442F69E4A2432C1088D047BFA65BA4F714DC7AC21
```

The upstream workflow targets newer OnePlus 5.10+ GKI devices. This repository
keeps its workflow order while replacing the incompatible OnePlus manifest,
device choices, GKI patches and Bazel build with the exact LineageOS SM8250
4.19 source, `kernel-4.19` SUSFS branch, `kona-perf_defconfig` plus
`vendor/oplus.config`, and the Android Clang revision observed on the target
device.

The workflow pins the official SukiSU Ultra `builtin` branch at
`b1d534bc41941b2c818d7a1a1dac341e4aabfc2d`. This branch uses the 4.x driver
ABI required by the v4.1.3 manager and already contains the old-kernel
`seccomp`, `iopoll` and `remap_file_range` compatibility paths missing from
the abandoned `main` experiment. No version number or ABI is forged.

The target-kernel patch in
`patches/sukisu-builtin-manual-hooks-sm8250-4.19.patch` is tied to the exact
LineageOS commit and adds calls at `do_execveat_common`, `do_faccessat`,
`vfs_read`, `vfs_statx`, and the reboot syscall bootstrap. The small driver
patch in `patches/sukisu-builtin-b1-linux-4.19.patch` only prevents the
current built-in branch from calling its 5.10+ SELinux-hide feature on 4.19.
SukiSU's own input handler provides Safe Mode; no obsolete input hook is
added.

SUSFS is deliberately and unconditionally disabled. The official
`kernel-4.19` SUSFS branch exposes the legacy 1.5.5 interface, while this
SukiSU generation expects a newer interface. The built-in branch defaults
SUSFS to enabled, so the workflow explicitly writes
`CONFIG_KSU_SUSFS=n` and fails if it is re-enabled.

KPM is also unconditionally disabled. Its current code uses the newer
two-argument `access_ok` API, while this arm64 4.19 kernel uses the legacy
three-argument form. KPM is not required for normal SukiSU root management.
The manual integration also explicitly disables kprobes after the vendor
configuration is merged.

## Safety

- Do not use this artifact on another device or ROM/kernel revision.
- Keep the original boot image and a working Fastboot recovery path.
- Do not install over a boot image already patched by APatch, Magisk or another
  KernelSU implementation.
- Verify the SHA-256 and build provenance before testing.
- Prefer a temporary boot test when supported. Flashing is never automated by
  this repository.
