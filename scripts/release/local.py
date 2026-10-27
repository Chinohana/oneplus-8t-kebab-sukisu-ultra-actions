#!/usr/bin/env python3
"""Verify local build and phone evidence, then prepare a local release directory."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


artifacts = load('local_delivery', ROOT / 'scripts/build/verify-artifacts.py')
fingerprints = load('local_fingerprint', ROOT / '.github/scripts/verify-runtime-approval.py')
matrix_builder = load('local_matrix', ROOT / 'scripts/release/matrix.py')
CHECKS = ('boot', 'adb', 'root', 'selinux_enforcing', 'susfs', 'selinux_hide', 'storage_decryption',
          'wifi', 'mobile_network', 'front_camera', 'rear_camera', 'fingerprint', 'audio', 'file_io', 'kernel_logs')
FULL_OPTIONS = ('KSU', 'KSU_SELINUX_HIDE_4_19', 'KSU_SUSFS', 'KSU_SUSFS_SUS_PATH',
                'KSU_SUSFS_SUS_MOUNT', 'KSU_SUSFS_SUS_KSTAT', 'KSU_SUSFS_SUS_MAP',
                'KSU_SUSFS_SPOOF_UNAME', 'KSU_SUSFS_ENABLE_LOG', 'KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS',
                'KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG', 'KSU_SUSFS_OPEN_REDIRECT')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(root):
    return dict(line.split('=', 1) for line in (root / 'kernel/build-provenance.txt').read_text().splitlines() if '=' in line)


def check_run(root, candidate, susfs, profile, hide):
    checked = artifacts.verify(root)
    if (susfs, profile, hide) != ('true', 'extended-full', 'true'):
        raise ValueError('Maintained releases require the full-feature configuration')
    config = set((root / 'kernel/selected.config').read_text().splitlines())
    if any(f'CONFIG_{option}=y' not in config for option in FULL_OPTIONS):
        raise ValueError('Full-feature release configuration is incomplete')
    provenance = fields(root)
    head = fingerprints.git(candidate, 'rev-parse', 'HEAD').decode().strip()
    if subprocess.run(['git', '-C', str(candidate), 'diff', '--quiet', 'HEAD', '--'], check=False).returncode:
        raise ValueError('Candidate tracked files differ from the build snapshot')
    fingerprint, kernel = fingerprints.compute_fingerprint(candidate, enable_susfs=susfs,
                                                           profile=profile, enable_hide=hide)
    required = {'execution_environment': 'local-wsl2', 'build_channel': 'candidate',
                'builder_commit': head, 'kernel_commit': kernel, 'build_fingerprint': fingerprint,
                'enable_susfs': susfs, 'enable_selinux_hide': hide, 'use_anykernel': 'true',
                'profile': profile if susfs == 'true' else 'selected'}
    for key, expected in required.items():
        if provenance.get(key) != expected:
            raise ValueError(f'Local provenance mismatch for {key}')
    inputs = root / 'kernel/audit/build-inputs.txt'
    if sha(inputs) != fingerprint:
        raise ValueError('Build input record does not match the candidate fingerprint')
    result = json.loads((root / 'kernel/audit/local-result.json').read_text())
    if result.get('result') != 'build-passed' or result.get('builder_commit') != head:
        raise ValueError('Local pipeline did not pass for this candidate')
    if result.get('run_id') != provenance.get('local_run_id'):
        raise ValueError('Local run identity mismatch')
    stages = {entry['stage']: entry.get('exit_code') for entry in result.get('stages', [])}
    required_stages = {'baseline-identity', 'fingerprint', 'patch-preflight', 'source', 'patches', 'audit-hooks',
                       'configure', 'compile', 'audit-build', 'package', 'provenance'}
    if susfs == 'true':
        required_stages.update(('references', 'audit-susfs', 'tool'))
    if hide == 'true':
        required_stages.add('audit-hide')
    if any(stages.get(stage) != 0 for stage in required_stages):
        raise ValueError('Required local audit stages are incomplete')
    name = provenance['package']
    package_sha = sha(root / 'kernel' / name)
    return {'builder_commit': head, 'build_fingerprint': fingerprint, 'package': name,
            'package_sha256': package_sha, 'image_sha256': checked['image_sha256'],
            'config_sha256': checked['config_sha256'], 'system_map_sha256': checked['system_map_sha256'],
            'tool_sha256': checked.get('tool_sha256'), 'local_run_id': provenance['local_run_id']}


def check_phone(phone, build):
    keys = ['builder_commit', 'package_sha256', 'image_sha256', 'tool_sha256', 'local_run_id']
    keys += [key for key in ('repair_builder_commit', 'repair_evidence_sha256') if key in build]
    for key in keys:
        if phone.get(key) != build[key]:
            raise ValueError(f'Phone test does not match {key}')
    if not isinstance(phone.get('tester'), str) or not phone['tester'].strip():
        raise ValueError('Phone-test operator is required')
    when = datetime.fromisoformat(phone.get('tested_at', ''))
    if when.tzinfo is None or when > datetime.now().astimezone():
        raise ValueError('Phone-test time must include timezone and cannot be in the future')
    if not all(phone.get('checks', {}).get(check) is True for check in CHECKS):
        raise ValueError('All required phone checks must be explicitly true')


def check_repair(build, root, repair_path):
    if repair_path is None:
        return build
    repair = json.loads(repair_path.read_text())
    name = repair['output_zip']
    if Path(name).name != name or '/' in name or '\\' in name:
        raise ValueError('Unsafe repair package name')
    original = root / 'kernel' / build['package']
    repaired = repair_path.parent / name
    if (repair.get('operation') != 'installer-only-repackage'
            or repair.get('source_zip_sha256') != sha(original)
            or repair.get('output_zip_sha256') != sha(repaired)
            or repair.get('image_sha256') != build['image_sha256']):
        raise ValueError('Repair record does not match the source and repaired package')
    repair_commit = repair['builder_commit']
    subprocess.run(['git', 'merge-base', '--is-ancestor', repair_commit, 'HEAD'], cwd=ROOT, check=True)
    patch_path = 'patches/anykernel3-split-status.patch'
    if subprocess.check_output(['git', 'show', f'{repair_commit}:{patch_path}'], cwd=ROOT) != (ROOT / patch_path).read_bytes():
        raise ValueError('Repair patch differs from its recorded builder')
    core = 'tools/ak3-core.sh'
    with zipfile.ZipFile(original) as before, zipfile.ZipFile(repaired) as after:
        names = before.namelist()
        if len(names) != len(set(names)) or names != after.namelist() or after.testzip() is not None:
            raise ValueError('Repair archive member list or CRC mismatch')
        changed = [name for name in names if before.read(name) != after.read(name)]
        if changed != [core]:
            raise ValueError('Repair may only change the installer core')
        with tempfile.TemporaryDirectory(prefix='release-repair-') as directory:
            tree = Path(directory)
            (tree / 'tools').mkdir()
            script = tree / core
            script.write_bytes(before.read(core))
            subprocess.run(['git', 'apply', str(ROOT / patch_path)], cwd=tree, check=True)
            if script.read_bytes() != after.read(core):
                raise ValueError('Repaired installer does not match the reviewed patch')
            subprocess.run(['python3', str(ROOT / 'scripts/test-anykernel-split.py'), str(script)], check=True)
    return {**build, 'source_package': build['package'], 'source_package_sha256': sha(original),
            'package': repaired.name, 'package_sha256': sha(repaired),
            'repair_builder_commit': repair_commit, 'repair_evidence_sha256': sha(repair_path)}


def accept(args):
    build = check_run(args.artifacts, args.candidate, 'true', 'extended-full', 'true')
    if args.matrix is not None:
        matrix = json.loads(args.matrix.read_text())
        if (matrix.get('result'), matrix.get('execution_environment'), matrix.get('builder_commit')) != (
                'passed', 'local-wsl2', build['builder_commit']):
            raise ValueError('Local matrix has not passed for this builder commit')
        delivery = Path(matrix['variants']['current-extended-full-hide']['artifacts'])
        if check_run(delivery, args.candidate, 'true', 'extended-full', 'true') != build:
            raise ValueError('Phone-test package is not the matrix full-feature delivery')
    build = check_repair(build, args.artifacts, getattr(args, 'repair_record', None))
    variants = {'current-extended-full-hide': build}
    phone = json.loads(args.phone_test.read_text())
    check_phone(phone, build)
    return {'schema': 3, 'result': 'passed', 'acceptance_environment': 'local', **build,
            'phone_tested': True, 'phone_tester': phone['tester'], 'tested_at': phone['tested_at'],
            'phone_evidence_sha256': sha(args.phone_test),
            'matrix_evidence_sha256': sha(args.matrix) if args.matrix is not None else None,
            'variants': variants}


def write_new(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    phone = sub.add_parser('phone-template', help='Write an unconfirmed phone-test form for one delivery')
    phone.add_argument('--artifacts', type=Path, required=True)
    phone.add_argument('--output', type=Path, required=True)
    phone.add_argument('--repair-record', type=Path, help='Verified installer-only repair receipt')
    for command in ('accept', 'stage'):
        child = sub.add_parser(command)
        child.add_argument('--candidate', type=Path, required=True, help='Exact build snapshot checkout')
        child.add_argument('--artifacts', type=Path, required=True)
        child.add_argument('--matrix', type=Path, help='Optional full-feature delivery record')
        child.add_argument('--phone-test', type=Path, required=True)
        child.add_argument('--repair-record', type=Path, help='Verified installer-only repair receipt')
        child.add_argument('--output', type=Path, required=True)
        if command == 'stage':
            child.add_argument('--acceptance', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'phone-template':
            checked = artifacts.verify(args.artifacts)
            provenance = fields(args.artifacts)
            build = {'builder_commit': provenance['builder_commit'], 'package': provenance['package'],
                      'local_run_id': provenance['local_run_id'], 'image_sha256': checked['image_sha256'],
                      'tool_sha256': checked.get('tool_sha256'),
                      'package_sha256': sha(args.artifacts / 'kernel' / provenance['package'])}
            build = check_repair(build, args.artifacts, args.repair_record)
            write_new(args.output, {**build, 'tester': '', 'tested_at': '',
                                   'checks': dict.fromkeys(CHECKS, False), 'notes': ''})
            return
        record = accept(args)
        if args.command == 'accept':
            write_new(args.output, record)
            print(f'Local acceptance passed: {args.output}')
            return
        if json.loads(args.acceptance.read_text()) != record:
            raise ValueError('Acceptance record is stale or does not match the current evidence')
        if args.output.exists():
            raise ValueError('Release destination exists')
        temporary = args.output.with_name(args.output.name + '.partial')
        temporary.mkdir(parents=True)
        package_root = args.repair_record.parent if args.repair_record else args.artifacts / 'kernel'
        sources = [package_root / record['package'],
                   args.artifacts / 'kernel/selected.config', args.artifacts / 'kernel/selected.System.map',
                   args.artifacts / 'tool/ksu_susfs-v2.3.0-arm64']
        for source in sources:
            shutil.copyfile(source, temporary / source.name)
        provenance_name = 'source-build-provenance.txt' if args.repair_record else 'build-provenance.txt'
        shutil.copyfile(args.artifacts / 'kernel/build-provenance.txt', temporary / provenance_name)
        if args.repair_record:
            shutil.copyfile(args.repair_record, temporary / 'installer-repair.json')
        shutil.copyfile(args.acceptance, temporary / 'acceptance.json')
        shutil.copyfile(args.phone_test, temporary / 'phone-test.json')
        # Publish only artifact identities from the matrix, without local filesystem paths.
        (temporary / 'matrix-summary.json').write_text(json.dumps(record['variants'], indent=2) + '\n')
        (temporary / 'SHA256SUMS').write_text(''.join(f'{sha(path)}  {path.name}\n' for path in sorted(temporary.iterdir())))
        # Recheck the package after copying, before declaring a release ready.
        if sha(temporary / record['package']) != record['package_sha256']:
            raise ValueError('Release copy hash mismatch')
        temporary.rename(args.output)
        print(f'Local release staged: {args.output}')
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
