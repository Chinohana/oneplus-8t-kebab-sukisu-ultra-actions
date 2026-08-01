# OnePlus 8T `kebab` — LineageOS 23.2 SukiSU Ultra cloud builder

> [!CAUTION]
> This branch is an **EXPERIMENTAL SUSFS v2.2 port** for one exact OnePlus 8T
> (`kebab`) LineageOS 23.2 kernel revision. **TESTING ONLY / 仅供测试.** The
> `smoke` and `minimal-mount` profiles boot on the development device, but the
> planned 24-hour stability observation was deliberately skipped. Long-term
> stability is unknown and crashes, boot failure, or data loss remain possible.
> Do not use it on another device, do not flash an Actions ZIP directly, and do
> not treat the results below as a production-stability guarantee.

## Current status

The non-SUSFS `main@1bc3fb3` built-in/manual-hook baseline is confirmed working
on the target phone. This experimental branch keeps that known-good kernel,
Clang, SukiSU, defconfig and packaging baseline fixed while adding a separately
audited SUSFS v2.2 port.

The exact `smoke` image built from experimental commit `19283953cc7f` has passed
CI audit, repeated temporary boots, manual camera/fingerprint/audio/daily-use
checks, a current-slot-only `boot_b` installation, and three physical cold
boots. Root, SUSFS v2.2.0, SELinux Enforcing, encrypted storage and the sdcard
monitor remained healthy, with empty strict fatal scans and pstore. However,
the tester explicitly waived the planned 24-hour observation on 2026-08-01.
Accordingly, this is evidence of short-run boot and functional viability only;
it is not evidence of long-term stability.

The `minimal-mount` image built from experimental commit `73c1484584a4` also
passed CI audit, exact artifact/config/provenance verification, temporary boot,
manual functional testing, current-slot-only `boot_b` installation, and three
physical cold boots. The official v2.2 tool reported exactly `SUS_MOUNT` plus
logging; all other hiding features remained disabled. Root, SELinux Enforcing,
encrypted storage and the sdcard monitor remained healthy, strict fatal scans
were empty, and pstore remained empty. The external `susfs4ksu` module was kept
disabled. This profile likewise has no completed 24-hour stability evidence and
remains testing-only.

This public repository builds a device-specific SukiSU Ultra kernel for:

- OnePlus 8T (`kebab`, SM8250)
- LineageOS 23.2 / Android 16
- Linux 4.19
- LineageOS kernel commit `4238ee49a84b`

The workflow produces an AnyKernel3 ZIP only. It deliberately does not create a
standalone `boot.img`, because repacking the user's known-good, unmodified boot
image locally avoids mixing in a ramdisk or DTB from a different ROM build.
The package uses AnyKernel3's `split_boot`/`flash_boot` path so the existing
ramdisk is not unpacked, edited, or repacked.

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

The original `build-sukisu.yml` still disables SUSFS unconditionally and is
kept byte-for-byte identical to `main`. The separate
`build-sukisu-susfs.yml` workflow pins official SUSFS v2.2 source commit
`8eade9cd4aed3efddc9ff30b2e48d2d9667ad77d` and offers two profiles:

- `smoke`: SUSFS core plus logging, with every hiding feature disabled.
- `minimal-mount`: the smoke configuration plus `SUS_MOUNT` only.

The exact-base v2.1 SM8250 case is used only to locate Linux 4.19 integration
points. Its KernelSU-Next tree, KPM, input hooks, defconfig and third-party
root code are not imported. The experimental workflow builds the known-good
baseline first, applies one combined manual-hook/SUSFS patch with strict
`git apply --check`, audits a file whitelist, then builds the selected profile.

KPM is also unconditionally disabled. Its current code uses the newer
two-argument `access_ok` API, while this arm64 4.19 kernel uses the legacy
three-argument form. KPM is not required for normal SukiSU root management.
The manual integration also explicitly disables kprobes after the vendor
configuration is merged.

## Safety

- Start with `smoke`. Advancing to `minimal-mount` without completing the
  24-hour smoke observation is an explicit risk acceptance, not a passed
  stability gate.
- Do not use this artifact on another device or ROM/kernel revision.
- Keep the original boot image and a working Fastboot recovery path.
- Do not install over a boot image already patched by APatch, Magisk or another
  KernelSU implementation.
- Verify the SHA-256 and build provenance before testing.
- Keep the existing `susfs4ksu` userspace module disabled for the first boot.
- Back up both boot slots and verify that the bootloader is actually unlocked.
- Test only a locally repacked boot image with `fastboot boot`. If temporary
  boot is unsupported, stop; do not substitute a direct flash.
- Flashing, slot switching and boot-image repacking are never automated by this
  repository.
