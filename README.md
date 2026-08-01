# OnePlus 8T `kebab` — SukiSU Ultra + SUSFS v2.2 builder

> [!CAUTION]
> `main` is the canonical **SUSFS v2.2** line for one exact OnePlus 8T
> (`kebab`) LineageOS 23.2 kernel revision. **TESTING ONLY / 仅供测试.** The
> `smoke` and `minimal-mount` profiles boot on the development device, but the
> planned 24-hour stability observation was deliberately skipped. The newer
> `extended-stat` profile remains build-only. `extended-full` has passed an
> isolated temporary boot, a current-slot installation and one module-enabled
> reboot, but not repeated cold boots or long-duration validation. Long-term
> stability is unknown and crashes,
> boot failure, or data loss remain possible. Do not use it on another device,
> do not flash an Actions ZIP directly, and do not treat the results below as a
> production-stability guarantee.

## Current status

The non-SUSFS `legacy@1bc3fb3` built-in/manual-hook baseline is confirmed
working on the target phone and remains available as the recovery/reference
line. `main` keeps that known-good kernel, Clang, SukiSU, defconfig and
packaging baseline fixed while adding the audited SUSFS v2.2 port.

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
were empty, and pstore remained empty. Initial kernel validation kept the
external `susfs4ksu` module disabled. After those gates passed,
`susfs4ksu v2.2.0-R28` was enabled with the pinned official v2.2 userspace tool
and completed one normal boot with an active marker, clean module logs and
empty pstore. This profile likewise has no completed 24-hour stability evidence
and remains testing-only.

`extended-stat` is the next isolated experiment. It adds only `SUS_KSTAT` on
top of the runtime-tested `minimal-mount` feature set. `SUS_PATH`, `SUS_MAP`,
uname/cmdline spoofing, open redirect and symbol hiding remain forced off. No
`extended-stat` artifact is runtime-approved merely because it compiles.

`extended-full` is a separate high-risk convenience profile requested by the
tester. It enables every feature still present in the pinned official v2.2
Kconfig: `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`, `SUS_MAP`, uname and cmdline
spoofing, open redirect, symbol hiding and logging. Deprecated v1.5-era mount
and try-umount options remain absent. This all-at-once profile does not replace
the staged artifacts or their recovery value. The exact image built from
experimental commit `c60b11c91935` passed CI and one `fastboot boot` on the
development KB2000. Android completed boot, root worked, SELinux remained
Enforcing, encrypted storage was available, and the pinned official tool
reported `v2.2.0 / NON-GKI` with exactly all nine options above. Pstore was
empty and a strict fatal-pattern scan found no panic, oops, BUG, UAF or lockup.
The tester also reported normal network, camera, fingerprint, audio and file
I/O during the temporary boot.

After that check, the identical locally repacked image (SHA-256
`a01d5add6f898fa756585c35c51c49b9687eb10501f81c1d7170064f379fcac3`)
was written only to the already-active `boot_b`; no slot was switched. It
completed one persistent boot with `susfs4ksu` still disabled, followed by one
boot with official `susfs4ksu v2.2.0-R28` enabled. Before enabling the module,
all custom SUSFS rule lists and spoof settings were verified empty. The module
created its active marker, completed all boot stages, started the sdcard monitor
and reported all nine intended features enabled; deprecated options remained
deprecated. Root, Enforcing SELinux, encrypted storage and file I/O remained
healthy, while pstore and strict fatal scans remained empty. Repeated cold-boot
and long-duration stability evidence still does not exist, so this remains a
testing-only result rather than a production recommendation.

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

The `legacy` branch preserves the original `build-sukisu.yml`, which disables
SUSFS unconditionally, byte-for-byte at commit `1bc3fb3`. The canonical
`build-sukisu-susfs.yml` workflow on `main` verifies that immutable legacy
baseline before building and pins official SUSFS v2.2 source commit
`8eade9cd4aed3efddc9ff30b2e48d2d9667ad77d` and offers four profiles:

- `smoke`: SUSFS core plus logging, with every hiding feature disabled.
- `minimal-mount`: the smoke configuration plus `SUS_MOUNT` only.
- `extended-stat`: `minimal-mount` plus `SUS_KSTAT` only; build-only until its
  separate controlled device test succeeds.
- `extended-full`: all options still provided by the pinned official v2.2
  Kconfig; temporary boot, current-slot installation and one module-enabled
  reboot passed, but it remains higher risk and testing-only, with deprecated
  options still excluded.

Pushes to `main` and manual runs default to the runtime-tested `extended-full`
profile. The staged profiles remain available for regression isolation.

The exact-base v2.1 SM8250 case is used only to locate Linux 4.19 integration
points. Its KernelSU-Next tree, KPM, input hooks, defconfig and third-party
root code are not imported. The canonical workflow builds the known-good
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
- Test `extended-stat` only after confirming that the exact runtime-approved
  `minimal-mount` patch inputs are unchanged. A successful build is not
  authorization to flash it.
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
