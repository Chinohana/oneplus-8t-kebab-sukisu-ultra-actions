# Upstream alignment candidate: 2026-10-13

| Input | Candidate | Result of live upstream check |
| --- | --- | --- |
| LineageOS `lineage-23.2` | `98a7970af93b7e01ee77156e7fa0eb7e059a57f0` | Already at branch tip |
| SukiSU `builtin` | `6c284e957feaa9a388a9f1c37dc4ec80d95e434b` | Includes official missing-arch-header repair |
| SukiSU Manager reference | `223897c72cc5c23b6fea84d6542aa8ef24459998`, version `40971` | Successful Manager run `38049351380`; functional changes since 40959 |
| Official SUSFS | `5192aa2d33b381b58c1051532f9e1dfa5de6e8d3`, `v2.3.0` | Latest `gki-android14-6.1` source used by this port |
| AnyKernel3 | `020dfeccf9d7e962a48400fc94d3e451df92eead` | Latest HEAD; updates Magisk tools to v31 beta |
| Android Clang | `r563880` | Retained by explicit user choice |
| Android NDK | `27.2.12479018` | Retained by explicit user choice |

The legacy builder identity and SM8250 placement reference remain historical
audit anchors. They are not moving source dependencies. The actual build
kernel comes from the LineageOS gitlink, SukiSU from its supported `builtin`
branch, and SUSFS from its pinned official source. The Manager's `main` branch
is not substituted for the kernel's manual-hook branch.

## SukiSU and Manager

The upstream builtin repair supplies `arch.h` and `EVENT_SERVICES`, allowing
removal of our temporary arm64 macro replacement and duplicate event insertion.
Retain UAPI version 5 and the optional bundled-LKM flag declaration; builtin
does not set that flag. Keep modern-only policy pointers inside their version
guard and preserve the existing Linux 4.19 SELinux hide backport.

The ordinary Manager artifact from
[run 38049351380](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/38049351380)
is named `SukiSU_v4.2.0_40971-release.apk`. Compared with 40959, its source adds
accurate module-repository error states, Android 8–12 compatibility, Zygisk Next
daemon detection and translation fixes. The candidate driver version therefore
advances to 40971 under the user's established alignment rule. No APK was
installed on the device.

## SUSFS v2.3 on Linux 4.19

Use the exact official v2.3 headers and core, retaining the Linux 4.19 fsnotify
callback ABI and failed sdcard-watch cleanup. The allocation-failure fix is now
present upstream, so its old local workaround is removed.

Port the v2.3 Kstat behavior to the old VFS interfaces:

- distinguish FUSE and ordinary inode markers, and spoof attributes after the
  filesystem's getattr callback;
- preserve statfs security checks before returning cached Kstat filesystem data;
- supply statfs/flags wrappers for the new core;
- spoof Kstat inode/device/mount identity in inotify and proc fdinfo;
- allow both zygote and zygote_next umounted apps to resolve original mounts.

Linux 4.19 does not expose modern statx mount IDs, and the official core already
guards writes to that kstat member by kernel version. The port passes private
Kstat markers directly to the core rather than exposing them in syscall result
masks. Public syscall structure layouts are unchanged.

AnyKernel3's split/flash policy still replaces only the kernel Image; the new
Magisk utilities do not authorize ramdisk modification or automatic flashing.

## Validation and adoption

Local strict patch application passed for the kernel v2.3 port, exec-compat
patch, SELinux kernel patch, latest builtin compatibility patch and SukiSU
SELinux hide patch. Official-header identity checks passed. Full compilation,
warning/configuration/symbol/image-size audits run in the four cloud candidate
variants. The resulting candidate still needs fresh device testing and exact
head approval before merge or installation.
