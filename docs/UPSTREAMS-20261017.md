# PR 25 upstream alignment: 2026-10-17

This update continues the existing PR rather than replacing it. The previous
candidate at `0d23ba58` passed all four variants in run `38285889576`; those
results do not validate this new candidate.

| Input | Selected revision | Change since the previous candidate |
| --- | --- | --- |
| LineageOS `lineage-23.2` | `98a7970af93b7e01ee77156e7fa0eb7e059a57f0` | Still the live branch tip |
| SukiSU `builtin` | `0af2cf9cef7dc2239fa7ebb3f7898830a1087e26` | Seven commits, including dynamic Manager authorization, forced features and ADB-only shell root |
| SukiSU Manager | `2aed04fcfdff9ad53041ffd84a291573993fa538`, `v4.2.1_41001` | Successful run `38760810020`; functional Manager and module workflow updates |
| SUSFS v2.3 | `5369359dbd10f6dd8cbdd59d1df7b788b29b168c` | SELinux status-open ordering fix and removal of unused GKI helpers |
| AnyKernel3 | `020dfeccf9d7e962a48400fc94d3e451df92eead` | Still the live HEAD |
| Clang / NDK | `r563880` / `27.2.12479018` | Retained per the user's earlier explicit choice |

The historical builder and SM8250 patch-placement pins remain audit anchors.
The kernel continues using SukiSU's supported `builtin` branch, not its
GKI-oriented `main` branch.

## Manager and SukiSU compatibility

The ordinary Manager artifact from
[run 38760810020](https://github.com/SukiSU-Ultra/SukiSU-Ultra/actions/runs/38760810020)
is `SukiSU_v4.2.1_41001-release.apk`, SHA-256
`cd4945d3f4491ea2869ed374887202c85154a86205dd04d81991bf4dc4340d6f`.
It includes substantive module-repository, dynamic-Manager, one-shot script,
hot-install and UI changes, so the candidate driver version advances to 41001.
The APK was downloaded for inspection and was not installed on the phone.

Rebase both Linux 4.19 compatibility patches onto the new builtin source:

- retain all upstream dynamic-Manager initialization and loading calls;
- keep forced-feature retries outside the modern-only SELinux callback guard;
- preserve ADB-only shell-root registration alongside the optional 4.19 hide
  initialization;
- guard the forced-feature name table's SELinux entry when its enum is absent
  in a Linux 4.19 build with SELinux hide disabled;
- retain UAPI version 5 and existing su-session/SELinux adaptations.

## SUSFS status-page fix

The official comparison changes the integration patches, not the v2.3 core or
the two SUSFS headers. Its status-open fix selects an already initialized fake
page before late initialization; it does not expose a newly initialized page
through an earlier real-status assignment.

The existing Linux 4.19 port already implements this ordering through
`ksu_sel_open_handle_status`: select the existing fake page first; otherwise
call the original status-open function, which assigns the real page before
attempting late initialization. The fake status page is retained for the
builtin kernel lifetime. The independent 4.19 implementation therefore needs
no additional status-open code change for these upstream commits. GKI-only
helper removals do not alter its 4.19 status path.

## Validation

Both rebased SukiSU patches passed strict application checks. Checks confirm
that the upstream dynamic-Manager and forced-feature call sites remain present.
The existing v2.3 kernel/exec/SELinux patch sequence is unchanged. Four fresh
cloud builds, warning/configuration/symbol/image-size audits and fresh device
testing remain required. No Manager installation, flash, approval or merge is
performed by this update.
