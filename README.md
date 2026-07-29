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
5. integrate the pinned current SukiSU Ultra release through the official
   non-GKI kprobe path;
6. enable the SukiSU root baseline;
7. reject incompatible, unaudited SUSFS and KPM combinations;
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

The workflow pins the official SukiSU Ultra `v4.1.3` release at
`0ca744a88835144c58d8256ebb32c279edabfcde` and enables its documented
non-GKI kprobe path. This uses the 4.x driver ABI required by the current
v4.1.3 manager. The previous v3.1.4 integration was not compatible with that
manager and is no longer used.

SUSFS is deliberately disabled in this baseline. The official
`kernel-4.19` SUSFS branch exposes the legacy 1.5.5 interface. Mixing it into
this 4.x baseline is blocked explicitly. First establish a clean current
SukiSU root build; a separate verified backport is required before enabling
SUSFS.

KPM is also disabled in this baseline. SukiSU v4.1.3's KPM code uses the
newer two-argument `access_ok` API, while this arm64 4.19 kernel uses the
legacy three-argument form. KPM needs a separate code and user-pointer audit
before it is enabled; it is not required for normal SukiSU root management.

## Safety

- Do not use this artifact on another device or ROM/kernel revision.
- Keep the original boot image and a working Fastboot recovery path.
- Do not install over a boot image already patched by APatch, Magisk or another
  KernelSU implementation.
- Verify the SHA-256 and build provenance before testing.
- Prefer a temporary boot test when supported. Flashing is never automated by
  this repository.
