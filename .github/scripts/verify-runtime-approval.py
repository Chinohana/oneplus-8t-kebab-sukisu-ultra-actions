#!/usr/bin/env python3
"""Verify a candidate artifact as data; never execute candidate repository code."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
PIN = re.compile(r"^([A-Z][A-Z0-9_]*)=([A-Za-z0-9._:/+\-]+)$")
MAX_MEMBER = 512 * 1024 * 1024
MAX_TOTAL = 1024 * 1024 * 1024


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def load_pins(root: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in (root / "config/build-pins.env").read_text(encoding="utf-8").splitlines():
        if not raw or raw.startswith("#"):
            continue
        match = PIN.fullmatch(raw)
        if not match:
            raise SystemExit(f"Unsafe build pin line: {raw}")
        pins[match.group(1)] = match.group(2)
    return pins


def kernel_commit(root: Path, pin_path: str) -> str:
    fields = git(root, "ls-tree", "HEAD", "--", pin_path).decode().split()
    if len(fields) < 3 or fields[0] != "160000" or not HEX40.fullmatch(fields[2]):
        raise SystemExit("Candidate kernel bookmark is not a full gitlink commit")
    return fields[2]


def compute_fingerprint(root: Path) -> tuple[str, str]:
    pins = load_pins(root)
    commit = kernel_commit(root, pins["KERNEL_PIN_PATH"])
    pathspecs = [
        ".gitmodules",
        "config/build-pins.env",
        "config/migration-baseline-lineage-23.2.sha256",
        ".github/scripts/*.sh",
        ".github/workflows/build-sukisu-ultra.yml",
        "patches/*.patch",
    ]
    tracked = git(root, "ls-files", "-z", "--", *pathspecs).split(b"\0")
    paths = sorted(item.decode() for item in tracked if item)
    if not paths:
        raise SystemExit("No fingerprint input files found")
    file_hashes = "".join(
        f"{hashlib.sha256((root / path).read_bytes()).hexdigest()}  {path}\n"
        for path in paths
    )
    ordered = [
        ("fingerprint_schema", "1"),
        ("device", "kebab"),
        ("rom", "LineageOS 23.2"),
        ("kernel_repository", pins["KERNEL_REPOSITORY"]),
        ("kernel_branch", pins["KERNEL_BRANCH"]),
        ("kernel_commit", commit),
        ("kernel_defconfig", pins["KERNEL_DEFCONFIG"]),
        ("oplus_config", pins["OPLUS_CONFIG"]),
        ("sukisu_repository", pins["SUKISU_REPOSITORY"]),
        ("sukisu_branch", pins["SUKISU_BRANCH"]),
        ("sukisu_commit", pins["SUKISU_COMMIT"]),
        ("sukisu_driver_version", pins["SUKISU_DRIVER_VERSION"]),
        ("susfs_repository", pins["SUSFS_REPOSITORY"]),
        ("susfs_commit", pins["SUSFS_COMMIT"]),
        ("susfs_version", pins["SUSFS_VERSION"]),
        ("sm8250_reference_repository", pins["SM8250_REFERENCE_REPOSITORY"]),
        ("sm8250_reference_commit", pins["SM8250_REFERENCE_COMMIT"]),
        ("sm8250_reference_base_commit", pins["SM8250_REFERENCE_BASE_COMMIT"]),
        ("clang_revision", pins["CLANG_REVISION"]),
        ("clang_archive_commit", pins["CLANG_ARCHIVE_COMMIT"]),
        ("anykernel_repository", pins["ANYKERNEL_REPOSITORY"]),
        ("anykernel_commit", pins["ANYKERNEL_COMMIT"]),
        ("android_ndk_version", pins["ANDROID_NDK_VERSION"]),
        ("enable_susfs", "true"),
        ("susfs_profile", "extended-full"),
        ("enable_selinux_hide", "true"),
        ("use_anykernel", "true"),
    ]
    canonical = "".join(f"{key}={value}\n" for key, value in ordered) + file_hashes
    return hashlib.sha256(canonical.encode()).hexdigest(), commit


def safe_members(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    infos = archive.infolist()
    if len(infos) > 500:
        raise SystemExit("Candidate artifact contains too many files")
    total = 0
    for info in infos:
        path = PurePosixPath(info.filename)
        if path.is_absolute() or ".." in path.parts or "\\" in info.filename:
            raise SystemExit(f"Unsafe artifact path: {info.filename}")
        if info.file_size > MAX_MEMBER:
            raise SystemExit(f"Artifact member is too large: {info.filename}")
        total += info.file_size
    if total > MAX_TOTAL:
        raise SystemExit("Candidate artifact expands beyond the verification limit")
    return infos


def one_by_suffix(infos: list[zipfile.ZipInfo], suffix: str) -> zipfile.ZipInfo:
    matches = [info for info in infos if info.filename.endswith(suffix)]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {suffix}; found {len(matches)}")
    return matches[0]


def parse_provenance(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            if re.fullmatch(r"[a-z_]+", key):
                result[key] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    for label, value, regex in (("PR head SHA", args.head_sha, HEX40),):
        if not regex.fullmatch(value):
            raise SystemExit(f"Invalid {label}")
    if args.artifact.stat().st_size > MAX_MEMBER:
        raise SystemExit("Downloaded artifact is unexpectedly large")
    actual_head = git(args.candidate, "rev-parse", "HEAD").decode().strip()
    if actual_head != args.head_sha:
        raise SystemExit("Checked-out PR head changed during approval")

    expected_fingerprint, commit = compute_fingerprint(args.candidate)

    with zipfile.ZipFile(args.artifact) as outer:
        infos = safe_members(outer)
        provenance_info = one_by_suffix(infos, "build-provenance.txt")
        package_infos = [
            info for info in infos
            if info.filename.endswith(".zip") and not info.is_dir()
        ]
        if len(package_infos) != 1:
            raise SystemExit("Expected exactly one flashable candidate ZIP")
        package_info = package_infos[0]
        package_bytes = outer.read(package_info)
        provenance = parse_provenance(outer.read(provenance_info).decode("utf-8"))

    actual_package_sha = hashlib.sha256(package_bytes).hexdigest()
    required = {
        "status": "CANDIDATE_DO_NOT_AUTO_INSTALL",
        "device": "kebab",
        "rom": "LineageOS 23.2",
        "profile": "extended-full",
        "enable_susfs": "true",
        "enable_selinux_hide": "true",
        "use_anykernel": "true",
        "build_channel": "candidate",
        "build_fingerprint": expected_fingerprint,
        "github_run_id": args.run_id,
        "kernel_branch": "lineage-23.2",
        "kernel_commit": commit,
    }
    for key, expected in required.items():
        if provenance.get(key) != expected:
            raise SystemExit(
                f"Candidate provenance mismatch for {key}: "
                f"expected {expected!r}, got {provenance.get(key)!r}"
            )

    record = {
        "schema": 1,
        "result": "passed",
        "pr": args.pr,
        "head_sha": args.head_sha,
        "kernel_commit": commit,
        "build_fingerprint": expected_fingerprint,
        "package_sha256": actual_package_sha,
        "phone_test_attested": True,
        "phone_test_environment": "physical device; details retained by operator",
        "candidate_run_id": int(args.run_id),
    }
    args.output.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
