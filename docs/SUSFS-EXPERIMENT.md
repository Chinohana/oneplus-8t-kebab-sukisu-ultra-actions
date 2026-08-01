# SUSFS v2.2 build and device gates

This document applies to the canonical `main` SUSFS line. The original
non-SUSFS baseline is preserved at `legacy@1bc3fb3`; the historical
`experiment/susfs-v2.2-sm8250-4.19` branch remains as development provenance.

## Fixed inputs

- LineageOS kernel:
  `4238ee49a84bd418c8515c297563bb29f95ab40b`
- SukiSU Ultra `builtin`:
  `b1d534bc41941b2c818d7a1a1dac341e4aabfc2d`
- Official SUSFS v2.2 source:
  `8eade9cd4aed3efddc9ff30b2e48d2d9667ad77d`
- Exact-base SM8250 v2.1 placement reference:
  `ac5f7e57d3f1d4ed065940960d7348c8baae3fb9`
- Android Clang: `r563880`
- Kernel configuration:
  `vendor/kona-perf_defconfig + vendor/oplus.config`

The v2.1 reference is placement evidence only. Its `KernelSU-Next/`,
`drivers/kernelsu`, KPM, input hooks, defconfig and third-party root changes
must never enter this branch.

## Deliberate v2.2 adaptations

The port keeps the official v2.2 headers and command ABI, with only the
following exact-base changes:

- use Linux 4.19 `fsnotify_ops.handle_event` while preserving v2.2's deferred
  monitor cleanup;
- prevent the official `susfs_get_enabled_features()` allocation-failure path
  from dereferencing a null pointer;
- disable the early-boot sdcard static key if monitor setup fails, instead of
  leaving every later exec on the early-boot path;
- retain the exact-base `vfs_create_mount()` allocation point and continue its
  full superblock/root initialization;
- upgrade mount controls to v2.2 static keys, high mount-ID ranges and the
  kernel's native ID allocators;
- adapt the combined exec/access/stat hooks to the pinned SukiSU `builtin`
  branch's real bool/static-key types;
- call `susfs_set_batch_sid()` after the Linux 4.19 SELinux policy update, as
  required by the official v2.2 integration, so zygote children receive the
  manager fd and expected seccomp handling.

These adaptations are kept in the static combined patch and audited in CI.
They are not generated or rewritten during a build.

## CI gates

1. Confirm the original workflow still has SHA-256
   `cd654904e8bf96032c1990ada83125894ece23daf41cdba7da514fd17d6afe31`
   for its LF-normalized Git blob.
2. Build the unchanged non-SUSFS baseline.
3. Apply the combined experimental patch using `git apply --check`, without
   fuzz, three-way application or compatibility source rewriting.
4. Reject files outside the explicit kernel and KernelSU whitelists.
5. Force KPM and kprobes off. Disable every SUSFS child option before enabling
   the exact requested profile.
6. Build `smoke` for every run. A `minimal-mount` request may build only after
   smoke succeeds in the same audit. An `extended-stat` request additionally
   builds `minimal-mount`, verifies that the three runtime-approved patch blobs
   still exactly match commit
   `73c1484584a40dd41a9ccc2d0593d47de5b66dc6`, then enables only
   `CONFIG_KSU_SUSFS_SUS_KSTAT`.
   An `extended-full` request uses the same immutable-patch gate and enables
   all nine child options still defined by pinned official SUSFS v2.2. It must
   not reintroduce deprecated try-umount, automatic mount or overlay options.
7. Verify manual-hook and SUSFS symbols, compare final configs/System.map/Image
   size, require both modern and Linux 4.19 SID-cache call sites, and fail on
   build warnings or abnormal growth.
8. Build the pinned `ksu_susfs` userspace tool as a separate artifact. Never
   install or invoke it automatically.
9. Publish only short-lived Actions artifacts with SHA-256 and provenance. Do
   not create a GitHub Release.

## Device gates

No CI artifact is approved for direct flashing.

1. Read the active slot dynamically. Back up and hash `boot_a` and `boot_b`;
   retain a directly flashable copy of the active boot partition.
2. Confirm battery, USB, ADB, Fastboot and the actual bootloader unlock state.
   Stop unless `fastboot getvar unlocked` confirms unlock.
3. Keep the external `susfs4ksu` module disabled. Use SukiSU Safe Mode for the
   first boot to isolate other modules.
4. Replace only `Image` inside a local copy of the current active boot image.
   Do not alter ramdisk, DTB, DTBO, `vendor_boot`, `init_boot` or SELinux.
5. Run `fastboot boot` first. If the device cannot temporary-boot the image,
   stop instead of flashing it.
6. For `smoke`, require a normal boot within five minutes; working ADB/root,
   enforcing SELinux, decrypted storage and expected SUSFS version/features;
   clean dmesg/pstore; and normal network, camera, fingerprint, audio, charging
   and file I/O.
7. Only then write that exact tested image to the current active boot slot.
   Never switch slots or overwrite both slots. Require three cold boots and at
   least 24 hours of observation.
8. Repeat the same sequence for `minimal-mount` only after smoke is stable.
9. Test `extended-stat` only after `minimal-mount`; require the reported feature
   list to add exactly `SUS_KSTAT`, keep every persistent kstat rule empty for
   the first boot, and add one harmless temporary-file rule only after the boot
   checks pass.
10. Treat `extended-full` as a separate high-risk test. Disable the userspace
    module and clear all persistent SUSFS rule lists for the first temporary
    boot; confirm the feature list before adding any rule or spoof value.
11. On any panic, oops, BUG, use-after-free, lockup, SELinux failure or functional
   regression, restore the saved active boot image in Fastboot, collect
   dmesg/pstore and stop the experiment.

Passing compilation is not a stability claim. Passing temporary boot is not a
24-hour stability claim. Each gate must be recorded independently.

## Recorded `extended-full` device evidence

The exact `extended-full` artifact from experimental workflow commit
`c60b11c91935` passed its CI audit and was locally repacked by replacing only
the kernel in the saved active-slot boot image. The repacked image was started
with `fastboot boot`; it was not flashed and no slot was switched.

During this single isolated boot, Android reported boot completion, SukiSU root
worked, SELinux remained Enforcing and encrypted storage was available. The
pinned official `ksu_susfs` v2.2 tool reported `v2.2.0`, `NON-GKI`, and exactly
these enabled options:

- `CONFIG_KSU_SUSFS_SUS_PATH`
- `CONFIG_KSU_SUSFS_SUS_MOUNT`
- `CONFIG_KSU_SUSFS_SUS_KSTAT`
- `CONFIG_KSU_SUSFS_SPOOF_UNAME`
- `CONFIG_KSU_SUSFS_ENABLE_LOG`
- `CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS`
- `CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG`
- `CONFIG_KSU_SUSFS_OPEN_REDIRECT`
- `CONFIG_KSU_SUSFS_SUS_MAP`

The external `susfs4ksu v2.2.0-R28` module remained disabled for this first
boot. Pstore was empty, and a strict fatal-pattern scan found no kernel panic,
oops, BUG, use-after-free or lockup. The tester reported normal network,
camera, fingerprint, audio and file I/O. The known baseline display-driver GPIO
diagnostic is not counted as a SUSFS regression.

After that temporary test, the identical locally repacked image (SHA-256
`a01d5add6f898fa756585c35c51c49b9687eb10501f81c1d7170064f379fcac3`)
was written only to the already-active `boot_b`. The saved original `boot_b`
backup retained SHA-256
`37ccb46cc368027e2fef746577859b414d9963041956c093cb69fc72df107bae`.
No slot was switched. The installed image completed one normal boot with the
userspace module still disabled; root, Enforcing SELinux, encrypted storage and
file I/O remained available, with empty pstore and fatal scans.

Before the next boot, every non-comment entry in `sus_path.txt`,
`sus_path_loop.txt`, `sus_maps.txt`, `sus_mount.txt`, `try_umount.txt` and
`sus_open_redirect.txt` was confirmed empty, `sus_kstat_statically.json` was
`[]`, and all optional spoof settings were zero. Official
`susfs4ksu v2.2.0-R28` was then enabled. The next boot completed normally; its
active marker and boot-stage log were present, the sdcard monitor started, and
the module reported all nine intended v2.2 features enabled. The deprecated
try-umount, automatic mount, magic-mount and overlay options remained marked
deprecated. Root, Enforcing SELinux, encrypted storage and file I/O stayed
healthy, while pstore and strict fatal scans stayed empty.

This is still deliberately narrow evidence: custom SUSFS rules and spoof
values were not exercised, repeated physical cold boots and long-duration
observation were not completed, and the Actions ZIP itself was not directly
flashed. `extended-full` therefore remains testing-only rather than a
production-stability recommendation.
