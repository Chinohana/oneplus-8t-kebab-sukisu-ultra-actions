#!/usr/bin/env python3
"""Repair an existing candidate's installer without changing its kernel payload."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-image-sha256', required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    temporary = output.with_suffix(output.suffix + '.partial')
    if source == output or any(path.exists() for path in (
            output, temporary, output.with_suffix(output.suffix + '.sha256'),
            output.with_suffix(output.suffix + '.repair.json'))):
        raise ValueError('Output must be a new file; preserve the original candidate')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'],
                               cwd=ROOT, text=True).strip():
        raise ValueError('Commit builder changes before repairing a candidate')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    source_sha = sha(source.read_bytes())
    core_name = 'tools/ak3-core.sh'
    with zipfile.ZipFile(source) as original:
        if len(set(original.namelist())) != len(original.namelist()):
            raise ValueError('Duplicate ZIP entries')
        image_sha = sha(original.read('Image'))
        if image_sha != args.expected_image_sha256:
            raise ValueError('Source Image hash does not match the audited candidate')
        with tempfile.TemporaryDirectory(prefix='ak3-repair-') as directory:
            work = Path(directory)
            core = work / core_name
            core.parent.mkdir()
            core.write_bytes(original.read(core_name))
            patch = ROOT / 'patches/anykernel3-split-status.patch'
            for options in (['--check'], []):
                subprocess.run(['git', 'apply', '--whitespace=error-all', *options, str(patch)],
                               cwd=work, check=True)
            subprocess.run(['python3', str(ROOT / 'scripts/test-anykernel-split.py'), str(core)],
                           check=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(temporary, 'x') as repaired:
                repaired.comment = original.comment
                for entry in original.infolist():
                    repaired.writestr(copy.copy(entry), core.read_bytes() if entry.filename == core_name
                                      else original.read(entry.filename))
        with zipfile.ZipFile(temporary) as repaired:
            assert original.namelist() == repaired.namelist()
            changes = [name for name in original.namelist()
                       if sha(original.read(name)) != sha(repaired.read(name))]
            assert changes == [core_name], changes
            assert repaired.testzip() is None
        assert sha(source.read_bytes()) == source_sha
    temporary.rename(output)
    output_sha = sha(output.read_bytes())
    output.with_suffix(output.suffix + '.sha256').write_text(f'{output_sha}  {output.name}\n')
    record = {'operation': 'installer-only-repackage', 'builder_commit': commit,
              'source_zip': str(source), 'source_zip_sha256': source_sha,
              'output_zip': output.name, 'output_zip_sha256': output_sha,
              'image_sha256': image_sha, 'changed_members': changes,
              'split_boot_cases_passed': 4, 'device_tested': False}
    output.with_suffix(output.suffix + '.repair.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
