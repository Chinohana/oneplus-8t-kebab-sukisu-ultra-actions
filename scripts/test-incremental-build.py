#!/usr/bin/env python3
"""Check safe object reuse, source invalidation and linker cache routing."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


incremental = load('incremental', 'scripts/build/incremental.py')
local = load('builder', 'scripts/build/local.py')


class IncrementalBuild(unittest.TestCase):
    def test_jobs_respect_cpu_memory_and_cap(self):
        gib = 1024**3
        self.assertEqual(local.automatic_jobs(20, 14 * gib), 16)
        self.assertEqual(local.automatic_jobs(4, 14 * gib), 4)
        self.assertEqual(local.automatic_jobs(20, 3 * gib), 4)
        self.assertEqual(local.automatic_jobs(20, 0), 1)

    def test_sync_preserves_unchanged_mtimes_and_objects_but_refreshes_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'source', Path(tmp) / 'target'
            source.mkdir()
            target.mkdir()
            (source / 'file.c').write_text('original\n')
            (target / 'out-extended-full').mkdir()
            obj = target / 'out-extended-full/file.o'
            obj.write_text('compiled')
            incremental.synchronize(source, target)
            before = (target / 'file.c').stat().st_mtime_ns
            os.utime(source / 'file.c', (2000000000, 2000000000))
            incremental.synchronize(source, target)
            self.assertEqual((target / 'file.c').stat().st_mtime_ns, before)
            (source / 'file.c').write_text('changed\n')
            incremental.synchronize(source, target)
            self.assertEqual((target / 'file.c').read_text(), 'changed\n')
            (source / 'file.c').unlink()
            incremental.synchronize(source, target)
            self.assertFalse((target / 'file.c').exists())
            self.assertEqual(obj.read_text(), 'compiled')

    def test_configuration_copy_does_not_touch_unchanged_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp) / 'source', Path(tmp) / 'target'
            source.write_text('CONFIG_KSU=y\n')
            incremental.copy_config(source, target)
            timestamp = target.stat().st_mtime_ns
            incremental.copy_config(source, target)
            self.assertEqual(target.stat().st_mtime_ns, timestamp)
            source.write_text('CONFIG_KSU_SUSFS=y\n')
            incremental.copy_config(source, target)
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_workspace_identity_invalidates_config_and_toolchain_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'out').mkdir()
            (root / 'bin').mkdir()
            (root / 'out/.config').write_text('CONFIG_KSU=y\n')
            (root / 'bin/clang').write_text('compiler one')
            (root / 'bin/ld.lld').write_text('linker one')
            first = incremental.workspace_identity(root, 'out', root, 'kernel')
            (root / 'out/.config').write_text('CONFIG_KSU=n\n')
            second = incremental.workspace_identity(root, 'out', root, 'kernel')
            self.assertNotEqual(first, second)
            (root / 'bin/clang').write_text('compiler two')
            self.assertNotEqual(second, incremental.workspace_identity(root, 'out', root, 'kernel'))

    def test_thinlto_flags_only_reach_the_lto_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            linker = root / 'ld'
            linker.write_text('#!/usr/bin/env python3\nimport json,sys\nprint(json.dumps(sys.argv[1:]))\n')
            linker.chmod(0o755)
            env = {**os.environ, 'REAL_LD': str(linker), 'THINLTO_CACHE_DIR': str(root / 'lto'), 'BUILD_JOBS': '12'}
            wrapper = ROOT / 'scripts/build/ld-cache.sh'
            normal = json.loads(subprocess.check_output(['bash', str(wrapper), '-v'], env=env, text=True))
            self.assertEqual(normal, ['-v'])
            cached = json.loads(subprocess.check_output(['bash', str(wrapper), '-r', '-o', 'vmlinux.o', 'input.a'], env=env, text=True))
            self.assertIn('--thinlto-jobs=12', cached)
            self.assertIn('--thinlto-cache-policy=cache_size_bytes=8g:cache_size=0%', cached)
            self.assertEqual(cached[-4:], ['-r', '-o', 'vmlinux.o', 'input.a'])


if __name__ == '__main__':
    unittest.main()
