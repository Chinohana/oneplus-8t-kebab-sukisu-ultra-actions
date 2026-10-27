#!/usr/bin/env python3
"""Exercise one-configuration orchestration without compiling a kernel."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SelectedBuild(unittest.TestCase):
    def test_local_cli_rejects_reduced_variants(self):
        for flags in (['--enable-susfs', 'false'], ['--enable-selinux-hide', 'false'],
                      ['--profile', 'smoke'], ['--use-anykernel', 'false']):
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/build/local.py'), *flags],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_configure_and_compile_exactly_one_image(self):
        for susfs, profile, hide in [('true', 'extended-full', 'true'),
                                     ('true', 'extended-stat', 'false'),
                                     ('true', 'smoke', 'true'), ('false', 'smoke', 'false')]:
            with self.subTest(susfs=susfs, profile=profile, hide=hide), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                tree = root / 'kernel_experiment'
                (tree / 'scripts/kconfig').mkdir(parents=True)
                (root / 'bin').mkdir()
                (root / 'audit').mkdir()
                (root / 'build-temp').mkdir()
                make = root / 'bin/make'
                make.write_text('''#!/usr/bin/env python3
import os, pathlib, sys
out = pathlib.Path(next(arg[2:] for arg in sys.argv if arg.startswith('O=')))
out.mkdir(exist_ok=True)
with open(os.environ['CALL_LOG'], 'a') as stream: stream.write(' '.join(sys.argv[1:]) + '\\n')
if 'Image' in sys.argv:
    (out/'arch/arm64/boot').mkdir(parents=True, exist_ok=True)
    for name in ['arch/arm64/boot/Image', 'vmlinux', 'System.map']: (out/name).write_text('test')
elif 'olddefconfig' not in sys.argv:
    (out/'.config').write_text('CONFIG_SECURITY_SELINUX=y\\nCONFIG_SECURITY_SELINUX_DEVELOP=y\\n')
''')
                config = tree / 'scripts/config'
                config.write_text('''#!/usr/bin/env python3
from pathlib import Path
import sys
path=Path(sys.argv[sys.argv.index('--file')+1]); lines=path.read_text().splitlines()
args=sys.argv[3:]
for index in range(0,len(args),2):
    flag,key=args[index:index+2]; key='CONFIG_'+key
    lines=[line for line in lines if not line.startswith(key+'=') and line != '# '+key+' is not set']
    lines.append(key+'=y' if flag=='-e' else '# '+key+' is not set')
path.write_text('\\n'.join(lines)+'\\n')
''')
                merge = tree / 'scripts/kconfig/merge_config.sh'
                merge.write_text('#!/usr/bin/env bash\nexit 0\n')
                for executable in (make, config, merge): executable.chmod(0o755)
                environment = root / 'build-temp/environment'
                environment.touch()
                env = {**os.environ, 'PATH': str(root/'bin')+':'+os.environ['PATH'],
                       'CALL_LOG': str(root/'calls'), 'BUILD_ROOT': str(root),
                       'BUILD_TEMP': str(root/'build-temp'), 'BUILD_ENV': str(environment),
                       'ENABLE_SUSFS': susfs, 'ENABLE_SELINUX_HIDE': hide, 'PROFILE': profile,
                       'KERNEL_DEFCONFIG': 'vendor/kona-perf_defconfig', 'OPLUS_CONFIG': 'vendor/oplus.config',
                       'SUKISU_DRIVER_VERSION': '41095', 'USE_CCACHE': 'false', 'BUILD_JOBS': '2',
                       'KERNEL_COMMIT': 'test-commit', 'CCACHE_HIDE_TAG': 'test'}
                git = root / 'bin/git'
                git.write_text('#!/usr/bin/env bash\nprintf 12345\n')
                git.chmod(0o755)
                subprocess.run(['bash', str(ROOT/'scripts/build/stages/configure.sh')], env=env, cwd=root, check=True)
                env['SELECTED_OUT'] = environment.read_text().strip().split('=',1)[1]
                subprocess.run(['bash', str(ROOT/'scripts/build/stages/compile.sh')], env=env, cwd=root, check=True)
                calls = (root/'calls').read_text().splitlines()
                self.assertEqual(len(calls), 3)
                self.assertEqual(sum(line.endswith(' Image') for line in calls), 1)
                self.assertFalse((root/'kernel_baseline').exists())
                self.assertTrue(all('out-baseline' not in line for line in calls))


if __name__ == '__main__':
    unittest.main()
