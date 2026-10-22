#!/usr/bin/env python3
"""Print storage usage and possible cleanup targets; never remove files."""
import argparse
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, default=Path.home() / 'oneplus8t-kernel')
args = parser.parse_args()
for name in ('runs', 'cache', 'toolchains', 'src'):
    path = args.workspace / name
    if path.exists():
        subprocess.run(['du', '-sh', str(path)], check=True)
for path in sorted((args.workspace / 'runs').glob('*')):
    subprocess.run(['du', '-sh', str(path)], check=True)
print(f'Linux free: {shutil.disk_usage(args.workspace).free / 2**30:.1f} GiB')
print('Cleanup preview only. Retain audit logs, delivery hashes and tested artifacts; review each run before deletion.')
