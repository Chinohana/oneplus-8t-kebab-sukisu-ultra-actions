#!/usr/bin/env python3
"""Check local acceptance rejects incomplete or mismatched evidence."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_release', ROOT / 'scripts/release/local.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class PhoneEvidence(unittest.TestCase):
    def setUp(self):
        self.build = {'builder_commit': 'a'*40, 'package_sha256': 'b'*64,
                      'image_sha256': 'c'*64, 'tool_sha256': 'd'*64, 'local_run_id': 'local-test'}
        self.phone = {**self.build, 'tester': 'test operator',
                      'tested_at': datetime.now(timezone.utc).isoformat(),
                      'checks': dict.fromkeys(release.CHECKS, True)}

    def test_complete_evidence_passes(self):
        release.check_phone(self.phone, self.build)

    def test_unchecked_form_rejected(self):
        self.phone['checks'] = dict.fromkeys(release.CHECKS, False)
        with self.assertRaisesRegex(ValueError, 'explicitly true'):
            release.check_phone(self.phone, self.build)

    def test_package_or_snapshot_change_invalidates_phone_test(self):
        for key in ('package_sha256', 'builder_commit', 'image_sha256', 'tool_sha256', 'local_run_id'):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                release.check_phone({**self.phone, key: 'changed'}, self.build)

    def test_missing_check_or_truthy_string_is_not_approval(self):
        for checks in ({}, {**self.phone['checks'], 'boot': 'true'}):
            with self.assertRaises(ValueError):
                release.check_phone({**self.phone, 'checks': checks}, self.build)

    def test_future_or_naive_time_rejected(self):
        for when in (datetime.now().isoformat(), (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()):
            with self.assertRaises(ValueError):
                release.check_phone({**self.phone, 'tested_at': when}, self.build)

    def test_optional_record_requires_the_same_full_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matrix = root / 'matrix.json'
            phone = root / 'phone.json'
            phone.write_text(json.dumps(self.phone))
            record = {'result': 'passed', 'execution_environment': 'local-wsl2',
                      'builder_commit': self.build['builder_commit'],
                      'variants': {key: {'artifacts': str(root / key)} for key in release.matrix_builder.VARIANTS}}
            matrix.write_text(json.dumps(record))
            args = SimpleNamespace(artifacts=root, candidate=root, matrix=matrix, phone_test=phone)
            with patch.object(release, 'check_run', return_value=self.build):
                self.assertTrue(release.accept(args)['phone_tested'])
                record['variants'].pop('current-extended-full-hide')
                matrix.write_text(json.dumps(record))
                with self.assertRaises(KeyError):
                    release.accept(args)

    def test_full_delivery_and_phone_evidence_need_no_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phone = root / 'phone.json'
            phone.write_text(json.dumps(self.phone))
            args = SimpleNamespace(artifacts=root, candidate=root, matrix=None, phone_test=phone)
            with patch.object(release, 'check_run', return_value=self.build):
                record = release.accept(args)
            self.assertTrue(record['phone_tested'])
            self.assertEqual(list(record['variants']), ['current-extended-full-hide'])
            self.assertIsNone(record['matrix_evidence_sha256'])

    def test_reduced_configuration_cannot_be_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'kernel').mkdir()
            (root / 'kernel/selected.config').write_text('CONFIG_KSU=y\nCONFIG_KSU_SUSFS=y\n')
            with patch.object(release.artifacts, 'verify', return_value={}):
                with self.assertRaisesRegex(ValueError, 'full-feature configuration'):
                    release.check_run(root, root, 'false', 'smoke', 'false')
                with self.assertRaisesRegex(ValueError, 'configuration is incomplete'):
                    release.check_run(root, root, 'true', 'extended-full', 'true')

    def test_cloud_matrix_does_not_count_as_local_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'matrix.json'
            path.write_text(json.dumps({'result': 'passed', 'execution_environment': 'github-actions',
                                        'builder_commit': self.build['builder_commit']}))
            with patch.object(release, 'check_run', return_value=self.build):
                with self.assertRaisesRegex(ValueError, 'Local matrix'):
                    release.accept(SimpleNamespace(artifacts=Path(tmp), candidate=Path(tmp), matrix=path))

    def test_real_artifacts_and_fingerprints_accept_then_reject_tamper(self):
        fixture_spec = importlib.util.spec_from_file_location('platform_fixture', ROOT / 'scripts/test-platform-approval.py')
        fixture_module = importlib.util.module_from_spec(fixture_spec)
        fixture_spec.loader.exec_module(fixture_module)
        fixture = fixture_module.PlatformApproval()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.platform('24.0')
        candidate = fixture.root
        # A normal clone creates the unpopulated gitlink directory.
        (candidate / 'pins/kernel-lineage-24.0').mkdir(parents=True, exist_ok=True)
        head = subprocess.check_output(['git', '-C', str(candidate), 'rev-parse', 'HEAD'], text=True).strip()
        deliveries = {}
        for variant, (susfs, profile, hide) in release.matrix_builder.VARIANTS.items():
            delivery = candidate.parent / variant
            kernel = delivery / 'kernel'
            audit = kernel / 'audit'
            audit.mkdir(parents=True)
            env = {**os.environ, 'ENABLE_SUSFS': susfs, 'SUSFS_PROFILE': profile,
                   'ENABLE_SELINUX_HIDE': hide, 'USE_ANYKERNEL': 'true', 'BUILD_CHANNEL': 'candidate'}
            fingerprint = subprocess.check_output(['bash', '.github/scripts/compute-build-fingerprint.sh',
                                                   str(candidate), str(audit)], cwd=candidate, env=env, text=True).strip()
            config = 'CONFIG_KSU=y\nCONFIG_SECURITY_SELINUX=y\n# CONFIG_KPROBES is not set\n# CONFIG_KPM is not set\n'
            if susfs == 'true':
                config += 'CONFIG_KSU_SUSFS=y\n'
            if hide == 'true':
                config += 'CONFIG_KSU_SELINUX_HIDE_4_19=y\n'
            config += ''.join(f'CONFIG_{option}=y\n' for option in release.FULL_OPTIONS
                              if f'CONFIG_{option}=y\n' not in config)
            (kernel / 'selected.config').write_text(config)
            (kernel / 'selected.System.map').write_text('test symbol\n')
            image = bytes(56) + b'ARM\x64' + bytes(4)
            with zipfile.ZipFile(kernel / 'candidate.zip', 'w') as archive:
                archive.writestr('Image', image)
                archive.writestr('anykernel.sh', 'device.name3=kebab\nIS_SLOT_DEVICE=1;\nBLOCK=/dev/block/by-name/boot;\n')
            (kernel / 'candidate.zip.sha256').write_text(release.sha(kernel / 'candidate.zip') + '  candidate.zip\n')
            (kernel / 'selected-build-files.sha256').write_text(
                ''.join(release.sha(kernel / name) + '  ' + name + '\n' for name in ('selected.config', 'selected.System.map'))
                + hashlib.sha256(image).hexdigest() + '  Image\n')
            provenance = {'execution_environment': 'local-wsl2', 'build_channel': 'candidate', 'builder_commit': head,
                          'kernel_commit': fixture_module.KERNEL, 'build_fingerprint': fingerprint,
                          'enable_susfs': susfs, 'enable_selinux_hide': hide, 'use_anykernel': 'true',
                          'profile': profile if susfs == 'true' else 'selected', 'local_run_id': variant,
                          'package': 'candidate.zip'}
            (kernel / 'build-provenance.txt').write_text(''.join(f'{key}={value}\n' for key, value in provenance.items()))
            (kernel / 'build-provenance.txt.sha256').write_text(release.sha(kernel / 'build-provenance.txt') + '\n')
            stages = ['baseline-identity', 'fingerprint', 'patch-preflight', 'source', 'patches', 'audit-hooks',
                      'configure', 'compile', 'audit-build', 'package', 'provenance', 'references', 'audit-susfs', 'tool', 'audit-hide']
            (audit / 'local-result.json').write_text(json.dumps({'builder_commit': head, 'run_id': variant,
                'result': 'build-passed', 'stages': [{'stage': name, 'exit_code': 0} for name in stages]}))
            if susfs == 'true':
                tool = delivery / 'tool/ksu_susfs-v2.3.0-arm64'
                tool.parent.mkdir()
                tool.write_bytes(b'\x7fELF\x02\x01' + bytes(12) + bytes((183, 0)) + bytes(44))
                tool.with_name(tool.name + '.sha256').write_text(release.sha(tool) + '\n')
            deliveries[variant] = {'artifacts': str(delivery)}
        full = Path(deliveries['current-extended-full-hide']['artifacts'])
        build = release.check_run(full, candidate, 'true', 'extended-full', 'true')
        phone = candidate.parent / 'phone.json'
        phone.write_text(json.dumps({**self.phone, **{key: build[key] for key in self.build}}))
        matrix = candidate.parent / 'matrix.json'
        matrix.write_text(json.dumps({'result': 'passed', 'execution_environment': 'local-wsl2',
                                      'builder_commit': head, 'variants': deliveries}))
        args = SimpleNamespace(artifacts=full, candidate=candidate, matrix=None, phone_test=phone)
        accepted = release.accept(args)
        self.assertTrue(accepted['phone_tested'])
        acceptance = candidate.parent / 'acceptance.json'
        release.write_new(acceptance, accepted)
        output = candidate.parent / 'release-output'
        command = ['local.py', 'stage', '--candidate', str(candidate), '--artifacts', str(full),
                   '--phone-test', str(phone), '--acceptance', str(acceptance), '--output', str(output)]
        with patch.object(sys, 'argv', command):
            release.main()
        for line in (output / 'SHA256SUMS').read_text().splitlines():
            digest, name = line.split(None, 1)
            self.assertEqual(release.sha(output / name), digest)
        self.assertNotIn(str(candidate.parent), (output / 'matrix-summary.json').read_text())
        (full / 'kernel/candidate.zip').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'Package hash'):
            release.accept(args)


class MaintainedBuildPolicy(unittest.TestCase):
    def test_custom_action_is_manual_and_kept_out_of_the_maintained_repository(self):
        workflow = ROOT / '.github/workflows'
        build = (workflow / 'build-sukisu-ultra.yml').read_text()
        for trigger in ('  push:', '  pull_request:', '  workflow_call:'):
            self.assertNotIn(trigger, build)
        self.assertIn("if: github.repository != 'Chinohana/oneplus-8t-kebab-sukisu-ultra-actions'", build)
        self.assertIn('run: bash scripts/build/custom-action.sh', build)
        for file in workflow.glob('*.yml'):
            text = file.read_text()
            self.assertNotIn('uses: ./.github/workflows/build-sukisu-ultra.yml', text)
            self.assertNotIn('run-stage.sh compile', text)
        approval = (workflow / 'approve-kernel-candidate.yml').read_text()
        self.assertNotIn('gh api', approval)
        self.assertNotIn('actions: write', approval)
        self.assertNotIn('issues: write', approval)
        self.assertNotIn('workflow_run:', (workflow / 'kernel-update-blocked-issue.yml').read_text())


if __name__ == '__main__':
    unittest.main()
