# OnePlus 8T `kebab` — LineageOS 23.2 SukiSU Ultra cloud builder

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

1. maximize runner storage;
2. configure Git and install dependencies;
3. initialize and sync kernel sources;
4. remove the `-dirty` suffix;
5. integrate the pinned SukiSU Ultra legacy-compatible tag;
6. apply SUSFS and hide-stuff patches;
7. enable SukiSU, KPM and SUSFS configuration;
8. build the kernel;
9. apply `patch_linux` for KPM;
10. package with AnyKernel3;
11. upload the result as an Actions artifact.

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

SUSFS `kernel-4.19` is the official v1.5.5-era branch. The workflow pins
SukiSU Ultra `v3.1.4` (`d7430733090f40870bc6d4b6b50ef08a91a92088`), whose
official documentation still used manual SUSFS integration for non-GKI
kernels. Current `builtin` expects the incompatible SUSFS v2.2.0 interface.
Because this vendor kernel retains the legacy SELinux `flex_array` policydb
layout, the workflow also reverses only the `sepolicy.c` portion of SukiSU's
own `898e9d4f` non-GKI removal commit before applying SUSFS. This restores the
upstream-maintained 4.x policydb paths without replacing SukiSU v3.1.4.

## Safety

- Do not use this artifact on another device or ROM/kernel revision.
- Keep the original boot image and a working Fastboot recovery path.
- Do not install over a boot image already patched by APatch, Magisk or another
  KernelSU implementation.
- Verify the SHA-256 and build provenance before testing.
- Prefer a temporary boot test when supported. Flashing is never automated by
  this repository.
