# SukiSU 40959 candidate

## Manager comparison

Compared the official `v4.2.0` release APK with the ordinary `Manager` artifact
from [Build Manager run 37357680570](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/37357680570),
whose source is `42d7fda3d787b7df90fc440a50bb9c8216a3fdef`.
The APKs were downloaded for inspection, not installed on the phone.

| APK | SHA-256 |
| --- | --- |
| `SukiSU_v4.2.0_40900-release.apk` | `4ca9810e6355fbff0bbe4bf5ce159808e64a40d85987a11894030cd990a6bdf3` |
| `SukiSU_v4.2.0_40959-release.apk` | `dedf9dce69a5a8cfa766a52f8c681eda20a11d3592b7754e5773854c7fea4c7c` |

The release APK hash matches the digest published by GitHub. The APK DEX payloads
differ. More importantly, the [source comparison](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.2.0...42d7fda3d787b7df90fc440a50bb9c8216a3fdef)
contains functional changes, including:

- module downloads through MediaStore;
- crash fixes for absent root access and incomplete kernel version information;
- search focus/back handling, page refresh and navigation fixes;
- an unexported Magica boot receiver;
- home layout and splash screen updates.

These are substantive updates, so the candidate driver version is set to `40959`
at the user's request. Matching version numbers alone do not establish ABI or
device compatibility. The Actions APK remains a development build; no runtime
Manager validation was performed in this comparison.

## Kernel source and manual-hook adaptations

SukiSU remains on `builtin`, pinned to
`70fa0e092a2c81060823f8ae526eac14fdda2930`. The Manager's `main` source is not
used as this project's kernel source. LineageOS remains pinned to `98a7970`.

The builtin update brings signature-validation, custom-profile, SELinux and
service-stage fixes. Two additional Linux 4.19 adaptations are required:

- Replace the upstream reference to absent `arch.h` with arm64 register accessors
  used by its new `ksyscall` helpers. Other architectures are rejected explicitly.
- Install the su-session descriptor only after a successful su-to-ksud exec,
  after exec has closed CLOEXEC descriptors. The SUSFS path tracks the upstream
  pre-hook result; the non-SUSFS path requires both the original su path and the
  actual rewrite to ksud. Ordinary execs and failed execs do not receive it.

Local checks passed strict application of the builtin compatibility and SELinux
hide patches, and both kernel hook sequences. The workflow checks for exactly
one su-session descriptor installation call in each kernel layout. Full cloud
compilation and fresh phone testing are still required for adoption.
