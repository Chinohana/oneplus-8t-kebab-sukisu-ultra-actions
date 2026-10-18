# LineageOS 24.0 experimental support

This branch targets OnePlus 8T / kebab (tested hardware model KB2000),
LineageOS 24.0 / Android 17 (API 37). It is not yet approved on Android 17.
The starting 23.2 main commit is `7cad005b0ff85497d2c80171725022ce95062db8`.

## Inputs and scope

On 2026-10-17 both official `lineage-23.2` and `lineage-24.0` kernel refs
pointed to `98a7970af93b7e01ee77156e7fa0eb7e059a57f0`. The new 24.0 bookmark
deliberately keeps this SHA. SukiSU builtin 41001, SUSFS v2.3, Clang r563880,
NDK and AnyKernel3 remain fixed to the main branch's inputs. No Android 17
specific kernel-hook rewrite is justified by a branch-name change alone.

The changes select the 24.0 upstream branch and bookmark, distinguish the ROM
in fingerprints, package names, provenance and approval records, and verify
upstream refs even when a platform transition keeps the same kernel SHA.
The old 23.2 migration hashes remain historical evidence only.

Cloud candidates build four combinations: SukiSU only, SELinux hide only,
SUSFS extended-stat, and extended-full with SELinux hide. A manual dispatch
on `experiment/lineage-24.0` also produces a CANDIDATE package. It cannot
produce an approved-channel artifact on that branch.

## Approval prerequisite

The separate `support/lineage-24-approval` branch updates the trusted main
verifier to recognize both legacy 23.2 artifacts and explicitly configured
24.0 artifacts. It leaves the main build target on 23.2. Merge that tested
verifier support before attempting cloud approval of a 24.0 candidate.
Candidate repository code is still never executed by the trusted verifier.

## Android 17 device validation

The kernel/source equality does not transfer the 23.2 phone-test result.
Before testing, obtain the exact installed 24.0 build identity and original
boot images, retain recovery files, and prepare a test boot by replacing only
the kernel in that 24.0 boot. Preserve its ramdisk, DTB and DTBO. Do not use
a complete 23.2 boot image or change slots automatically.

Start with temporary boot and check ADB, storage decryption, SELinux Enforcing,
root authorization and Manager communication, network, camera, fingerprint,
audio, SUSFS and SELinux-hide off/on behavior. Check dmesg/pstore and repeated
cold boots. Test Zygisk/modules separately; a working su shell is insufficient
evidence for module compatibility. Bind approval to the exact candidate head,
artifact hash and Android 17 environment.

## Main transition and 23.2 archive

1. Complete cloud audits and Android 17 device validation on the exact candidate.
2. Record the installed ROM build fingerprint and test evidence with that PR.
3. Immediately before merging, resolve the live main SHA and preserve it as
   `archive/lineage-23.2-final`. Verify the remote archive points to that SHA.
   Never overwrite an existing archive with different contents.
4. Merge the approved 24.0 PR into main. Retain this document as migration history
   and update the README validation status using the actual test evidence.

The archive is intentionally deferred until the final 23.2 main is known.
The experiment does not install a ROM, flash a phone, approve itself, create
an archive prematurely, or merge the platform change automatically.
