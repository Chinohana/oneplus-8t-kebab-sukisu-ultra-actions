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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(root):
    return dict(line.split('=', 1) for line in (root / 'kernel/build-provenance.txt').read_text().splitlines() if '=' in line)


def check_run(root, candidate, susfs, profile, hide):
    checked = artifacts.verify(root)
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
    for key in ('builder_commit', 'package_sha256', 'image_sha256', 'local_run_id'):
        if phone.get(key) != build[key]:
            raise ValueError(f'Phone test does not match {key}')
    if not isinstance(phone.get('tester'), str) or not phone['tester'].strip():
        raise ValueError('Phone-test operator is required')
    when = datetime.fromisoformat(phone.get('tested_at', ''))
    if when.tzinfo is None or when > datetime.now().astimezone():
        raise ValueError('Phone-test time must include timezone and cannot be in the future')
    if not all(phone.get('checks', {}).get(check) is True for check in CHECKS):
        raise ValueError('All required phone checks must be explicitly true')


def accept(args):
    build = check_run(args.artifacts, args.candidate, 'true', 'extended-full', 'true')
    matrix = json.loads(args.matrix.read_text())
    if (matrix.get('result'), matrix.get('execution_environment'), matrix.get('builder_commit')) != (
            'passed', 'local-wsl2', build['builder_commit']):
        raise ValueError('Local matrix has not passed for this builder commit')
    variants = {}
    for variant, (susfs, profile, hide) in matrix_builder.VARIANTS.items():
        delivery = Path(matrix['variants'][variant]['artifacts'])
        variants[variant] = check_run(delivery, args.candidate, susfs, profile, hide)
    if variants['current-extended-full-hide'] != build:
        raise ValueError('Phone-test package is not the matrix full-feature delivery')
    phone = json.loads(args.phone_test.read_text())
    check_phone(phone, build)
    return {'schema': 2, 'result': 'passed', 'acceptance_environment': 'local', **build,
            'phone_tested': True, 'phone_tester': phone['tester'], 'tested_at': phone['tested_at'],
            'phone_evidence_sha256': sha(args.phone_test), 'matrix_evidence_sha256': sha(args.matrix),
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
    for command in ('accept', 'stage'):
        child = sub.add_parser(command)
        child.add_argument('--candidate', type=Path, required=True, help='Exact build snapshot checkout')
        child.add_argument('--artifacts', type=Path, required=True)
        child.add_argument('--matrix', type=Path, required=True)
        child.add_argument('--phone-test', type=Path, required=True)
        child.add_argument('--output', type=Path, required=True)
        if command == 'stage':
            child.add_argument('--acceptance', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'phone-template':
            checked = artifacts.verify(args.artifacts)
            provenance = fields(args.artifacts)
            write_new(args.output, {'builder_commit': provenance['builder_commit'],
                      'local_run_id': provenance['local_run_id'], 'image_sha256': checked['image_sha256'],
                      'package_sha256': sha(args.artifacts / 'kernel' / provenance['package']),
                      'tester': '', 'tested_at': '', 'checks': dict.fromkeys(CHECKS, False), 'notes': ''})
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
        sources = [args.artifacts / 'kernel' / record['package'],
                   args.artifacts / 'kernel/build-provenance.txt',
                   args.artifacts / 'kernel/selected.config', args.artifacts / 'kernel/selected.System.map',
                   args.artifacts / 'tool/ksu_susfs-v2.3.0-arm64']
        for source in sources:
            shutil.copyfile(source, temporary / source.name)
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
