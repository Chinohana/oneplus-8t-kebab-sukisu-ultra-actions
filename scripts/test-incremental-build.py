#!/usr/bin/env python3
"""Check safe object reuse, source invalidation and linker cache routing."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


incremental = load('incremental', 'scripts/build/incremental.py')
local = load('builder', 'scripts/build/local.py')


class IncrementalBuild(unittest.TestCase):
    def fixture(self, root, status):
        source = root / 'kernel_experiment'
        for tree in (source, source / 'KernelSU'):
            tree.mkdir(parents=True, exist_ok=True)
            subprocess.run(['git', 'init', str(tree)], check=True, capture_output=True)
            (tree / 'source.c').write_text('int original;\n')
            subprocess.run(['git', '-C', str(tree), 'add', 'source.c'], check=True)
            subprocess.run(['git', '-C', str(tree), '-c', 'user.name=test', '-c', 'user.email=test@localhost',
                            'commit', '-m', 'test'], check=True, capture_output=True)
        (source / 'out-extended-full').mkdir()
        (source / 'out-extended-full/.config').write_text('CONFIG_KSU=y\n')
        (root / 'audit').mkdir()
        (root / 'toolchains/clang/bin').mkdir(parents=True)
        for name in ('clang', 'ld.lld'):
            (root / 'toolchains/clang/bin' / name).write_text(name)
        (root / 'scripts/build/stages').mkdir(parents=True)
        (root / 'scripts/build/ld-cache.sh').write_bytes((ROOT / 'scripts/build/ld-cache.sh').read_bytes())
        (root / 'scripts/build/stages/compile.sh').write_text('''
set -eu
out="$COMPILE_TREE/$COMPILE_OUT"
mkdir -p "$out/arch/arm64/boot"
for file in vmlinux System.map arch/arm64/boot/Image; do printf verified > "$out/$file"; done
exit ''' + str(status) + '\n')
        return {'BUILD_ROOT': str(root), 'SELECTED_OUT': 'out-extended-full', 'KERNEL_COMMIT': 'test',
                'BUILD_OBJECT_CACHE': str(root / 'objects'), 'BUILD_LTO_CACHE': str(root / 'lto')}

    def test_success_snapshots_outputs_without_moving_the_run_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, self.fixture(root, 0)):
                incremental.main()
            report = json.loads((root / 'audit/incremental-build.json').read_text())
            self.assertEqual(report['result'], 'passed')
            self.assertFalse(report['warm_workspace'])
            image = root / 'kernel_experiment/out-extended-full/arch/arm64/boot/Image'
            self.assertEqual(image.read_text(), 'verified')
            self.assertFalse(image.is_symlink())
            self.assertEqual((root / 'kernel_experiment/source.c').read_text(), 'int original;\n')

    def test_failed_compile_never_publishes_cached_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict(os.environ, self.fixture(root, 7)):
                with self.assertRaises(SystemExit) as result:
                    incremental.main()
            self.assertEqual(result.exception.code, 7)
            self.assertFalse((root / 'kernel_experiment/out-extended-full/arch/arm64/boot/Image').exists())
            self.assertEqual(json.loads((root / 'audit/incremental-build.json').read_text())['result'], 'failed')

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
