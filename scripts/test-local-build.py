#!/usr/bin/env python3
"""Exercise failure handling without downloading dependencies or compiling a kernel."""
import importlib.util
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts/build' / file)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


local = module('local', 'local.py')
verifier = module('artifacts', 'verify-artifacts.py')


class Delivery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        kernel = self.root / 'kernel'
        kernel.mkdir()
        (kernel / 'audit').mkdir()
        image = bytes(56) + b'ARM\x64' + bytes(4)
        config = b'CONFIG_KSU=y\nCONFIG_SECURITY_SELINUX=y\n# CONFIG_KPROBES is not set\n# CONFIG_KPM is not set\n'
        (kernel / 'selected.config').write_bytes(config)
        (kernel / 'selected.System.map').write_bytes(b'test symbol\n')
        (kernel / 'Image').write_bytes(image)
        hashes = {name: hashlib.sha256((kernel / name).read_bytes()).hexdigest()
                  for name in ('Image', 'selected.config', 'selected.System.map')}
        (kernel / 'selected-build-files.sha256').write_text(''.join(f'{sha}  {name}\n' for name, sha in hashes.items()))
        self.provenance = dict(builder_commit='a'*40, build_fingerprint='b'*64,
                               enable_susfs='false', enable_selinux_hide='false', use_anykernel='false')
        self.write_provenance()

    def write_provenance(self):
        path = self.root / 'kernel/build-provenance.txt'
        path.write_text(''.join(f'{key}={value}\n' for key, value in self.provenance.items()))
        path.with_suffix('.txt.sha256').write_text(hashlib.sha256(path.read_bytes()).hexdigest() + '  build-provenance.txt\n')

    def test_valid_raw_delivery(self):
        self.assertFalse(verifier.verify(self.root)['device_tested'])

    def test_tampered_image(self):
        (self.root / 'kernel/Image').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Image integrity'):
            verifier.verify(self.root)

    def test_tampered_provenance(self):
        (self.root / 'kernel/build-provenance.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'Provenance hash'):
            verifier.verify(self.root)

    def test_feature_config_mismatch(self):
        self.provenance['enable_selinux_hide'] = 'true'
        self.write_provenance()
        with self.assertRaisesRegex(ValueError, 'Configuration mismatch'):
            verifier.verify(self.root)

    def test_warning_blocks_export(self):
        (self.root / 'kernel/audit/warnings-new-in-smoke.txt').write_text('warning')
        with self.assertRaisesRegex(ValueError, 'compiler warnings'):
            verifier.verify(self.root)

    def test_failed_export_can_retry_to_new_destination(self):
        run = self.root / 'runs/local-full-test'
        run.mkdir(parents=True)
        import shutil
        (run / 'scripts/build').mkdir(parents=True)
        shutil.copyfile(ROOT / 'scripts/build/verify-artifacts.py', run / 'scripts/build/verify-artifacts.py')
        shutil.copytree(self.root / 'kernel', run / 'artifacts/kernel')
        export = self.root / 'export'
        export.mkdir()
        with patch.object(local.shutil, 'copytree', side_effect=OSError('export unavailable')):
            with self.assertRaisesRegex(OSError, 'unavailable'):
                local.export_artifacts(run, export)
        self.assertEqual(local.export_artifacts(run, export), export / run.name)


class Preflight(unittest.TestCase):
    def test_failed_stage_stops_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / 'scripts/build/run-stage.sh'
            runner.parent.mkdir(parents=True)
            runner.write_text('test "$1" != compile || exit 7\n')
            records = []
            with (root / 'log').open('w') as log:
                with self.assertRaisesRegex(RuntimeError, 'compile failed \\(7\\)'):
                    local.execute_stages(root, {}, ['configure', 'compile', 'package'], log, records)
            self.assertEqual([entry['stage'] for entry in records], ['configure', 'compile'])
            self.assertEqual(records[-1]['exit_code'], 7)

    def test_wrong_toolchain_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'bin').mkdir()
            for name in ('clang', 'ld.lld', 'llvm-nm', '../ndk-build'):
                executable = root / 'bin' / name
                executable.touch()
                executable.chmod(0o755)
            (root / 'source.properties').write_text('Pkg.Revision = 0\n')
            args = SimpleNamespace(workspace=root, clang=root, ndk=root, enable_susfs='true')
            with patch.object(local.shutil, 'which', return_value='/test/bin'), patch.object(local, 'run',
                    side_effect=['x86_64', 'ext4', 'wrong clang']):
                with self.assertRaisesRegex(ValueError, 'Clang revision'):
                    local.preflight(args)
            with patch.object(local.shutil, 'which', return_value='/test/bin'), patch.object(local, 'run',
                    side_effect=['x86_64', 'ext4', 'Android clang r563880']):
                with self.assertRaisesRegex(ValueError, 'NDK revision'):
                    local.preflight(args)

    def test_insufficient_host_space(self):
        with patch.object(local.shutil, 'disk_usage', return_value=type('Usage', (), {'free': 49 * 2**30})()):
            with self.assertRaisesRegex(ValueError, 'Insufficient space'):
                local.check_space([Path('/')], 50)

    def test_no_default_reserve_and_smaller_explicit_reserve(self):
        with patch.object(local.shutil, 'disk_usage', return_value=SimpleNamespace(free=5 * 2**30)):
            local.check_space([Path('/')], 0)
            local.check_space([Path('/')], 2)
            with self.assertRaisesRegex(ValueError, 'Insufficient space'):
                local.check_space([Path('/')], 10)

    def test_usage_excludes_linked_cache_and_distinguishes_sparse_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'run'
            target.mkdir()
            external = root / 'cache'
            external.mkdir()
            (external / 'existing').write_bytes(b'x' * 10000)
            (target / '.ccache').symlink_to(external, target_is_directory=True)
            with (target / 'sparse').open('wb') as file:
                file.truncate(16 * 2**20)
            usage = local.tree_usage(target)
            self.assertEqual(usage['files'], 1)
            self.assertEqual(usage['symlinks'], 1)
            self.assertGreaterEqual(usage['logical_bytes'], 16 * 2**20)
            self.assertLess(usage['allocated_bytes'], 16 * 2**20)

    def test_usage_counts_hardlink_paths_but_not_duplicate_content(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'file').write_bytes(b'x' * 10000)
            before = local.tree_usage(root)
            os.link(root / 'file', root / 'second-name')
            after = local.tree_usage(root)
            self.assertEqual(after['files'], before['files'] + 1)
            self.assertEqual(after['logical_bytes'], before['logical_bytes'])
            self.assertEqual(after['allocated_bytes'], before['allocated_bytes'])

    def test_missing_dependency(self):
        with patch.object(local.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(ValueError, 'Missing dependency'):
                local.preflight(None)

    def test_build_lock_rejects_second_owner(self):
        import fcntl
        with tempfile.TemporaryDirectory() as tmp:
            with (Path(tmp) / 'lock').open('a') as first, (Path(tmp) / 'lock').open('a') as second:
                fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)


if __name__ == '__main__':
    unittest.main()
