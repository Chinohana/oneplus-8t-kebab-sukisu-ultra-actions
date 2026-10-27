#!/usr/bin/env python3
"""Build the single full-feature local acceptance delivery."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
VARIANTS = {
    'current-extended-full-hide': ('true', 'extended-full', 'true'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.home() / 'oneplus8t-kernel')
    parser.add_argument('--storage', type=Path, default=Path(os.environ.get('BUILD_STORAGE', str(Path.home() / 'oneplus8t-build'))))
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    builder = ROOT / 'scripts/build/local.py'
    common = ['--workspace', str(args.workspace), '--storage', str(args.storage), '--jobs', str(args.jobs)]
    if args.check_only:
        subprocess.run([sys.executable, str(builder), *common, '--check-only'], check=True)
        print('Local matrix: ' + ', '.join(VARIANTS))
        return
    if not args.output:
        parser.error('--output is required for a build')
    if args.output.exists():
        parser.error('Matrix record already exists; choose a new output path')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cache = args.workspace / 'cache'
    cache.mkdir(exist_ok=True)
    with (cache / 'matrix.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        record = {'schema': 1, 'execution_environment': 'local-wsl2', 'builder_commit': head,
                  'result': 'in-progress', 'variants': {}}
        args.output.write_text(json.dumps(record, indent=2) + '\n')
        export = args.storage / 'artifacts'
        for variant, (susfs, profile, hide) in VARIANTS.items():
            before = set(export.iterdir())
            command = [sys.executable, str(builder), *common, '--enable-susfs', susfs,
                       '--profile', profile, '--enable-selinux-hide', hide]
            status = subprocess.run(command).returncode
            if status:
                record.update(result='failed', failed_variant=variant, exit_code=status)
                args.output.write_text(json.dumps(record, indent=2) + '\n')
                raise SystemExit(status)
            if subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip() != head:
                raise SystemExit('Builder checkout changed during matrix; matrix is not accepted')
            added = [path for path in set(export.iterdir()) - before if path.is_dir() and not path.name.endswith('.partial')]
            if len(added) != 1:
                raise SystemExit('Expected exactly one new delivery for this variant')
            record['variants'][variant] = {'artifacts': str(added[0].resolve())}
            args.output.write_text(json.dumps(record, indent=2) + '\n')
        record['result'] = 'passed'
        args.output.write_text(json.dumps(record, indent=2) + '\n')
        print(f'Local matrix passed: {args.output}')


if __name__ == '__main__':
    main()
