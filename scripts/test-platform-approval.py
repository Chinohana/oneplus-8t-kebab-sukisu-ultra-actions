#!/usr/bin/env python3
"""Regression tests for trusted verification of legacy and Android 17 artifacts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERIFIER = ROOT / ".github/scripts/verify-runtime-approval.py"
spec = importlib.util.spec_from_file_location("verifier", VERIFIER)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)
BASH = os.environ.get("BASH_EXE", "bash")
KERNEL = "98a7970af93b7e01ee77156e7fa0eb7e059a57f0"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE).decode().strip()


class PlatformApproval(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "candidate"
        self.root.mkdir()
        tracked = git(ROOT, "ls-files").splitlines()
        for name in tracked:
            source = ROOT / name
            if source.is_file():
                target = self.root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "test@example.invalid")
        git(self.root, "config", "user.name", "Platform tests")
        git(self.root, "config", "core.autocrlf", "false")

    def platform(self, version, legacy=False):
        path = self.root / "config/build-pins.env"
        lines = path.read_text().splitlines()
        lines = [line for line in lines if not line.startswith(("ROM_VERSION=", "ANDROID_API="))]
        for i, line in enumerate(lines):
            if line.startswith("KERNEL_BRANCH="):
                lines[i] = f"KERNEL_BRANCH=lineage-{version}"
            if line.startswith("KERNEL_PIN_PATH="):
                lines[i] = f"KERNEL_PIN_PATH=pins/kernel-lineage-{version}"
        if not legacy:
            lines += [f"ROM_VERSION={version}", f"ANDROID_API={'37' if version == '24.0' else '36'}"]
        path.write_text("\n".join(lines) + "\n", newline="\n")
        # A tiny control repository with an unpopulated gitlink; no kernel clone.
        git(self.root, "add", ".")
        git(self.root, "update-index", "--add", "--cacheinfo", f"160000,{KERNEL},pins/kernel-lineage-{version}")
        git(self.root, "commit", "-qm", f"Fixture {version}")

    def artifact(self, version, legacy=False, **overrides):
        fingerprint, _ = verifier.compute_fingerprint(self.root)
        package = b"test-only inert kernel package"
        fields = {
            "status": "CANDIDATE_DO_NOT_AUTO_INSTALL", "device": "kebab",
            "rom": f"LineageOS {version}", "profile": "extended-full",
            "enable_susfs": "true", "enable_selinux_hide": "true",
            "use_anykernel": "true", "build_channel": "candidate",
            "build_fingerprint": fingerprint, "github_run_id": "123",
            "kernel_branch": f"lineage-{version}", "kernel_commit": KERNEL,
        }
        if not legacy:
            fields["android_api"] = "37" if version == "24.0" else "36"
        fields.update(overrides)
        artifact = Path(self.temp.name) / "artifact.zip"
        with zipfile.ZipFile(artifact, "w") as archive:
            archive.writestr("candidate.zip", package)
            archive.writestr("build-provenance.txt", "".join(f"{k}={v}\n" for k, v in fields.items()))
        result = Path(self.temp.name) / "approval.json"
        command = ["python3" if os.name != "nt" else "python", str(VERIFIER),
                   "--candidate", str(self.root), "--artifact", str(artifact),
                   "--head-sha", git(self.root, "rev-parse", "HEAD"), "--run-id", "123",
                   "--pr", "1", "--output", str(result)]
        run = subprocess.run(command, capture_output=True, text=True)
        return run, result, package

    def test_legacy_23_artifact_still_approved(self):
        self.platform("23.2", legacy=True)
        run, result, package = self.artifact("23.2", legacy=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(result.read_text())["package_sha256"], hashlib.sha256(package).hexdigest())

    def test_android17_artifact_approved_with_platform_record(self):
        self.platform("24.0")
        run, result, _ = self.artifact("24.0")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(result.read_text())["android_api"], "37")

    def test_old_rom_provenance_rejected_on_new_platform(self):
        self.platform("24.0")
        run, _, _ = self.artifact("24.0", rom="LineageOS 23.2")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("provenance mismatch for rom", run.stderr)

    def test_wrong_api_rejected(self):
        self.platform("24.0")
        run, _, _ = self.artifact("24.0", android_api="36")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("provenance mismatch for android_api", run.stderr)

    def test_mismatched_platform_inputs_rejected(self):
        self.platform("24.0")
        pins = verifier.load_pins(self.root)
        for key, value in (("ROM_VERSION", "23.2"), ("ANDROID_API", "36"),
                           ("KERNEL_PIN_PATH", "pins/kernel-lineage-23.2"),
                           ("KERNEL_BRANCH", "lineage-99.0"),
                           ("KERNEL_REPOSITORY", "https://example.invalid/kernel.git")):
            with self.subTest(key=key), self.assertRaises(SystemExit):
                verifier.target_platform({**pins, key: value})

    def test_same_kernel_does_not_reuse_platform_fingerprint(self):
        self.platform("23.2", legacy=True)
        old, _ = verifier.compute_fingerprint(self.root)
        self.platform("24.0")
        new, _ = verifier.compute_fingerprint(self.root)
        self.assertNotEqual(old, new)

    def test_shell_and_trusted_python_fingerprints_agree(self):
        # The bootstrap shell still targets 23.2; the migration shell uses pins.
        shell = (self.root / ".github/scripts/compute-build-fingerprint.sh").read_text()
        versions = ("23.2", "24.0") if "$ROM_VERSION" in shell else ("23.2",)
        for version in versions:
            with self.subTest(version=version):
                self.platform(version, legacy=version == "23.2" and len(versions) == 1)
                run = subprocess.run([BASH, ".github/scripts/compute-build-fingerprint.sh", ".", "audit"],
                                     cwd=self.root, capture_output=True, text=True)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout.strip(), verifier.compute_fingerprint(self.root)[0])

    def check_transition(self, upstream_sha):
        script = self.root / ".github/scripts/validate-kernel-candidate.sh"
        if "platform_changed" not in script.read_text():
            self.skipTest("Transition inspection is introduced by the experimental branch")
        self.platform("23.2")
        old_head = git(self.root, "rev-parse", "HEAD")
        self.platform("24.0")
        wrapper = self.root / "fake-bin/git"
        wrapper.parent.mkdir()
        wrapper.write_text('''#!/usr/bin/env bash
if test "$1" = ls-remote; then
  test "$3" = refs/heads/lineage-24.0 || exit 92
  echo checked > upstream-ref-checked
  printf '%s\\trefs/heads/lineage-24.0\\n' "$TEST_UPSTREAM_SHA"
else
  exec "$REAL_GIT" "$@"
fi
''', newline="\n")
        wrapper.chmod(0o755)
        env = {**os.environ, "TEST_UPSTREAM_SHA": upstream_sha, "TEST_BASE": old_head}
        command = '''export REAL_GIT="$(command -v git)"
export PATH="$PWD/fake-bin:$PATH"
export GITHUB_OUTPUT="$PWD/inspection.txt"
bash .github/scripts/validate-kernel-candidate.sh . "$TEST_BASE"
'''
        run = subprocess.run([BASH, "-c", command], cwd=self.root, env=env,
                             capture_output=True, text=True)
        return run

    def test_same_sha_transition_checks_ref_and_requires_build(self):
        run = self.check_transition(KERNEL)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue((self.root / "upstream-ref-checked").exists())
        outputs = (self.root / "inspection.txt").read_text()
        self.assertIn("needs_build=true", outputs)
        self.assertIn("platform_changed=true", outputs)
        self.assertIn("kernel_changed=false", outputs)
        self.assertIn(f"old_kernel={KERNEL}", outputs)

    def test_same_sha_transition_rejects_stale_upstream_pin(self):
        run = self.check_transition("1" * 40)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("no longer the latest lineage-24.0", run.stdout)


if __name__ == "__main__":
    unittest.main()
