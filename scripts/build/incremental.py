#!/usr/bin/env python3
"""Reuse managed compiler objects without modifying any saved run checkout."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def workspace_identity(source, out, clang, kernel):
    return {'schema': 1, 'kernel_commit': kernel, 'arch': 'arm64',
            'config_sha256': digest(source / out / '.config'),
            'clang_root': str(clang), 'clang_sha256': digest(clang / 'bin/clang'),
            'lld_sha256': digest(clang / 'bin/ld.lld')}


def synchronize(source, destination):
    # --checksum detects content changes; omitting --times leaves identical
    # destination files untouched even when a fresh checkout has new mtimes.
    # --delete is confined to the dedicated managed source copy, never a run.
    subprocess.run(['rsync', '-rclp', '--delete', '--exclude=/out-*',
                    str(source) + '/', str(destination) + '/'], check=True)


def copy_config(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists() or source.read_bytes() != destination.read_bytes():
        shutil.copyfile(source, destination)


def main():
    started = time.monotonic()
    root = Path(os.environ['BUILD_ROOT']).resolve()
    source = root / 'kernel_experiment'
    out = os.environ['SELECTED_OUT']
    if out not in ('out-smoke', 'out-minimal-mount', 'out-extended-stat', 'out-extended-full', 'out-selected'):
        raise ValueError('Unsafe output directory')
    clang = (root / 'toolchains/clang').resolve()
    cache = Path(os.environ['BUILD_OBJECT_CACHE']).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    identity = workspace_identity(source, out, clang, os.environ['KERNEL_COMMIT'])
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    managed = cache / key
    marker = managed / 'identity.json'
    if managed.exists():
        if managed.is_symlink() or not marker.is_file() or json.loads(marker.read_text()) != identity:
            raise ValueError('Object workspace is not an intact managed build directory')
    else:
        managed.mkdir()
        marker.write_text(json.dumps(identity, indent=2) + '\n')
    if managed.resolve().parent != cache:
        raise ValueError('Object workspace escapes the configured cache')
    record = {'schema': 1, 'workspace_key': key, 'workspace': str(managed),
              'identity': identity, 'result': 'in-progress'}
    report = root / 'audit/incremental-build.json'
    report.write_text(json.dumps(record, indent=2) + '\n')
    with (managed / 'build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        tree = managed / 'kernel'
        if tree.is_symlink():
            raise ValueError('Managed source tree must not be a symlink')
        tree.mkdir(exist_ok=True)
        if (tree / out).is_symlink():
            raise ValueError('Managed compiler output must not be a symlink')
        record['warm_workspace'] = (tree / out / 'vmlinux').exists()
        synchronize(source, tree)
        copy_config(source / out / '.config', tree / out / '.config')
        lto = Path(os.environ['BUILD_LTO_CACHE']).resolve() / identity['lld_sha256'][:16]
        lto.mkdir(parents=True, exist_ok=True)
        wrapper = root / 'scripts/build/ld-cache.sh'
        linker_dir = cache / 'linkers' / digest(wrapper)
        linker_dir.mkdir(parents=True, exist_ok=True)
        linker = linker_dir / 'ld.lld'
        if not linker.exists():
            shutil.copyfile(wrapper, linker)
            linker.chmod(0o700)
        if linker.read_bytes() != wrapper.read_bytes():
            raise ValueError('Cached linker wrapper content mismatch')
        env = {**os.environ, 'INCREMENTAL_ACTIVE': 'true', 'COMPILE_TREE': str(tree),
               'COMPILE_OUT': out, 'BUILD_LD': str(linker), 'REAL_LD': str(clang / 'bin/ld.lld'),
               'THINLTO_CACHE_DIR': str(lto)}
        compiled = time.monotonic()
        status = subprocess.run(['bash', str(root / 'scripts/build/stages/compile.sh')], env=env).returncode
        record.update(make_seconds=round(time.monotonic() - compiled, 3), exit_code=status)
        if status:
            record.update(result='failed', elapsed_seconds=round(time.monotonic() - started, 3))
            report.write_text(json.dumps(record, indent=2) + '\n')
            raise SystemExit(status)
        if digest(tree / out / '.config') != identity['config_sha256']:
            raise ValueError('Incremental build changed the selected configuration')
        for relative in ('.', 'KernelSU'):
            expected = subprocess.check_output(['git', '-C', str(source / relative), 'diff', '--binary', 'HEAD'])
            actual = subprocess.check_output(['git', '-C', str(tree / relative), 'diff', '--binary', 'HEAD'])
            if expected != actual:
                raise ValueError('Compiler workspace source differs from the audited run snapshot')
        # Snapshot only the audited deliverables. Compiler objects stay in the
        # managed cache; old run sources, audit evidence and Images stay intact.
        for name in ('.config', 'System.map', 'vmlinux', 'arch/arm64/boot/Image'):
            destination = source / out / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(tree / out / name, destination)
        record.update(result='passed', image_sha256=digest(source / out / 'arch/arm64/boot/Image'),
                      elapsed_seconds=round(time.monotonic() - started, 3))
        report.write_text(json.dumps(record, indent=2) + '\n')
        print(f"Incremental workspace warm={record['warm_workspace']}; make={record['make_seconds']:.3f}s", flush=True)


if __name__ == '__main__':
    main()
