#!/usr/bin/env python3
"""Check a local delivery or a downloaded kernel artifact without executing it."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify(root):
    kernel = root / 'kernel' if (root / 'kernel').is_dir() else root
    provenance_path = kernel / 'build-provenance.txt'
    provenance_bytes = provenance_path.read_bytes()
    if digest(provenance_bytes) != (kernel / 'build-provenance.txt.sha256').read_text().split()[0]:
        raise ValueError('Provenance hash mismatch')
    fields = dict(line.split('=', 1) for line in provenance_bytes.decode().splitlines() if '=' in line)
    expected = {}
    for line in (kernel / 'selected-build-files.sha256').read_text().splitlines():
        sha, name = line.split(None, 1)
        expected[PurePosixPath(name).name] = sha
    for name in ('selected.config', 'selected.System.map'):
        if digest((kernel / name).read_bytes()) != expected[name]:
            raise ValueError(f'Hash mismatch: {name}')
    config = (kernel / 'selected.config').read_text().splitlines()
    for option in ('KSU', 'SECURITY_SELINUX'):
        if f'CONFIG_{option}=y' not in config:
            raise ValueError(f'Missing {option}')
    for option in ('KPROBES', 'KPM'):
        if f'# CONFIG_{option} is not set' not in config:
            raise ValueError(f'Unexpected {option}')
    for field, option in [('enable_susfs', 'KSU_SUSFS'), ('enable_selinux_hide', 'KSU_SELINUX_HIDE_4_19')]:
        enabled = f'CONFIG_{option}=y' in config
        if enabled != (fields[field] == 'true'):
            raise ValueError(f'Configuration mismatch: {field}')
    members = {}
    if fields['use_anykernel'] == 'true':
        name = fields['package']
        if PurePosixPath(name).name != name or '\\' in name:
            raise ValueError('Unsafe package path')
        package = kernel / name
        if digest(package.read_bytes()) != (kernel / (name + '.sha256')).read_text().split()[0]:
            raise ValueError('Package hash mismatch')
        with zipfile.ZipFile(package) as archive:
            if archive.testzip():
                raise ValueError('ZIP integrity failure')
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError('Duplicate ZIP member')
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                if path.is_absolute() or '..' in path.parts or '\\' in info.filename:
                    raise ValueError('Unsafe ZIP member')
                if not info.is_dir():
                    members[info.filename] = digest(archive.read(info))
            image = archive.read('Image')
            installer = archive.read('anykernel.sh').decode()
            for required in ('device.name3=kebab', 'IS_SLOT_DEVICE=1;', 'BLOCK=/dev/block/by-name/boot;'):
                if required not in installer:
                    raise ValueError(f'Unexpected installer: {required}')
    else:
        image = (kernel / 'Image').read_bytes()
    if image[56:60] != b'ARM\x64' or digest(image) != expected['Image']:
        raise ValueError('Image integrity failure')
    result = {'build_fingerprint': fields['build_fingerprint'], 'builder_commit': fields['builder_commit'],
              'image_sha256': digest(image), 'config_sha256': expected['selected.config'],
              'system_map_sha256': expected['selected.System.map'], 'zip_members': members,
              'device_tested': False}
    tool = root / 'tool/ksu_susfs-v2.3.0-arm64'
    if fields['enable_susfs'] == 'true':
        data = tool.read_bytes()
        if data[:6] != b'\x7fELF\x02\x01' or struct.unpack_from('<H', data, 18)[0] != 183:
            raise ValueError('Wrong SUSFS tool architecture')
        if digest(data) != tool.with_suffix(tool.suffix + '.sha256').read_text().split()[0]:
            raise ValueError('SUSFS tool hash mismatch')
        result['tool_sha256'] = digest(data)
    for warnings in (kernel / 'audit').glob('warnings-new-in-*.txt'):
        if warnings.read_text().strip():
            raise ValueError(f'New compiler warnings: {warnings.name}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    result = verify(args.artifacts)
    if args.compare:
        other = verify(args.compare)
        differences = [key for key in ('builder_commit', 'build_fingerprint', 'image_sha256', 'config_sha256',
                                      'system_map_sha256', 'tool_sha256') if result.get(key) != other.get(key)]
        member_names = result['zip_members'].keys() | other['zip_members'].keys()
        result['zip_content_differences'] = sorted(name for name in member_names
                                                  if result['zip_members'].get(name) != other['zip_members'].get(name))
        result['core_differences'] = differences
        print(json.dumps(result, indent=2))
        if differences or result['zip_content_differences']:
            parser.exit(1, 'Builds differ; investigate before declaring equivalence.\n')
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
