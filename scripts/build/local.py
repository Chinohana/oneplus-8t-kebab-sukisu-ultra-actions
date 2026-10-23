#!/usr/bin/env python3
"""Run the shared audited pipeline in an isolated Linux build checkout."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORAGE = Path(os.environ.get('BUILD_STORAGE', str(Path.home() / 'oneplus8t-build')))


def run(*args, **kwargs):
    return subprocess.check_output(args, text=True, **kwargs).strip()


def pins(root):
    result = {}
    for line in (root / 'config/build-pins.env').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*=[A-Za-z0-9._:/+\-]+', line):
            raise ValueError('Unsafe build pin')
        key, value = line.split('=', 1)
        result[key] = value
    return result


def check_space(paths, minimum_gib):
    if not minimum_gib:
        return
    for path in paths:
        available = shutil.disk_usage(path).free / 2**30
        if available < minimum_gib:
            raise ValueError(f'Insufficient space at {path}: {available:.1f} GiB, require {minimum_gib} GiB')


def tree_usage(root):
    """Count directory entries without following links or charging hardlinks twice."""
    result = {'files': 0, 'directories': 0, 'symlinks': 0,
              'logical_bytes': 0, 'allocated_bytes': 0}
    pending = [Path(root)]
    seen = set()
    while pending:
        path = pending.pop()
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue  # A compiler temporary may disappear during a sample.
        identity = (info.st_dev, info.st_ino)
        if identity not in seen:
            seen.add(identity)
            result['allocated_bytes'] += info.st_blocks * 512
            if not stat.S_ISDIR(info.st_mode):
                result['logical_bytes'] += info.st_size
        if stat.S_ISLNK(info.st_mode):
            result['symlinks'] += 1
        elif stat.S_ISDIR(info.st_mode):
            result['directories'] += 1
            try:
                with os.scandir(path) as entries:
                    pending.extend(Path(entry.path) for entry in entries)
            except FileNotFoundError:
                continue
        elif stat.S_ISREG(info.st_mode):
            result['files'] += 1
    return result


def usage_breakdown(target):
    result = {}
    for child in sorted(target.iterdir()):
        result[child.name] = tree_usage(child)
        if child.name in ('kernel_baseline', 'kernel_experiment'):
            for output in sorted(child.glob('out-*')):
                result[f'{child.name}/{output.name}'] = tree_usage(output)
    return result


def preflight(args):
    p = pins(ROOT)
    for command in ('bash', 'git', 'make', 'bc', 'bison', 'flex', 'ccache', 'cpio', 'curl',
                    'file', 'jq', 'rsync', 'unzip', 'wget', 'zip', 'xz', 'patch', 'readelf'):
        if not shutil.which(command):
            raise ValueError(f'Missing dependency: {command}')
    if run('uname', '-m') != 'x86_64':
        raise ValueError('Linux x86_64 is required')
    if run('findmnt', '-n', '-T', str(args.workspace), '-o', 'FSTYPE') != 'ext4':
        raise ValueError('Build workspace must be on ext4')
    for name in ('clang', 'ld.lld', 'llvm-nm'):
        if not os.access(args.clang / 'bin' / name, os.X_OK):
            raise ValueError(f'Missing Clang tool: {name}')
    clang_version = run(str(args.clang / 'bin/clang'), '--version')
    if p['CLANG_REVISION'].removeprefix('clang-') not in clang_version:
        raise ValueError('Clang revision does not match pins')
    if args.enable_susfs == 'true':
        if not os.access(args.ndk / 'ndk-build', os.X_OK):
            raise ValueError('Missing Linux NDK')
        if f"Pkg.Revision = {p['ANDROID_NDK_VERSION']}" not in (args.ndk / 'source.properties').read_text().splitlines():
            raise ValueError('NDK revision does not match pins')
    if run('git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('Commit builder changes before creating a build snapshot')
    for path in (args.storage, args.export_dir):
        if not path.is_dir():
            raise ValueError(f'Directory does not exist: {path}')
    check_space((args.workspace, args.storage, args.export_dir), args.minimum_free_gib)
    if args.jobs < 1:
        raise ValueError('jobs must be positive')
    return p


def export_artifacts(run_dir, export_dir):
    # Verify both sides. A failed export can be retried without rebuilding.
    verifier = run_dir / 'scripts/build/verify-artifacts.py'
    subprocess.run([sys.executable, str(verifier), str(run_dir / 'artifacts')], check=True)
    destination = export_dir / run_dir.name
    if destination.exists():
        raise ValueError(f'Export destination exists: {destination}')
    temporary = export_dir / (run_dir.name + '.partial')
    if temporary.exists():
        raise ValueError(f'Incomplete export exists; inspect before retry: {temporary}')
    shutil.copytree(run_dir / 'artifacts', temporary, copy_function=shutil.copyfile)
    subprocess.run([sys.executable, str(verifier), str(temporary)], check=True)
    temporary.rename(destination)
    return destination


def execute_stages(target, env, stages, log, records):
    for stage in stages:
        print(f'STAGE {stage}', flush=True)
        record = {'stage': stage, 'started': datetime.now().astimezone().isoformat()}
        records.append(record)
        result = subprocess.run(['bash', 'scripts/build/run-stage.sh', stage], cwd=target, env=env,
                                stdout=log, stderr=subprocess.STDOUT)
        record['exit_code'] = result.returncode
        if result.returncode:
            raise RuntimeError(f'{stage} failed ({result.returncode}); log: {log.name}')


def build(args):
    p = preflight(args)
    if args.check_only:
        print(json.dumps({'result': 'passed', 'builder_commit': run('git', '-C', str(ROOT), 'rev-parse', 'HEAD'),
                          'workspace': str(args.workspace), 'jobs': args.jobs, 'build_started': False}, indent=2))
        return
    cache = args.cache_dir
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / 'build.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('A local build is already running') from None
        space = {'schema': 1, 'initial_workspace_used_bytes': shutil.disk_usage(args.workspace).used,
                 'initial_host_free_bytes': shutil.disk_usage(args.storage).free,
                 'initial_export_free_bytes': shutil.disk_usage(args.export_dir).free,
                 'cache_before': tree_usage(cache), 'samples': []}
        run_id = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('local-full-%Y%m%d-%H%M%S')
        target = args.workspace / 'runs' / run_id
        target.parent.mkdir(exist_ok=True)
        commit = run('git', '-C', str(ROOT), 'rev-parse', 'HEAD')
        subprocess.run(['git', 'clone', '--no-hardlinks', str(ROOT), str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', commit], check=True)
        subprocess.run(['git', '-C', str(target), 'remote', 'set-url', 'origin',
                        'https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions.git'], check=True)
        temp = target / 'build-temp'
        temp.mkdir()
        audit = target / 'audit'
        audit.mkdir()
        (target / 'toolchains').mkdir()
        (target / 'toolchains/clang').symlink_to(args.clang)
        (target / '.ccache').symlink_to(cache)
        env_file = temp / 'environment'
        env_file.touch()
        env = {**os.environ, **p, 'BUILD_ROOT': str(target), 'BUILD_TEMP': str(temp),
               'BUILD_ENV': str(env_file), 'BUILD_SUMMARY': str(temp / 'summary.md'),
               'BUILDER_COMMIT': commit, 'BUILD_CHANNEL': 'candidate', 'LOCAL_RUN_ID': run_id,
               'EXECUTION_ENVIRONMENT': 'local-wsl2', 'ENABLE_SUSFS': args.enable_susfs,
               'ENABLE_SELINUX_HIDE': args.enable_selinux_hide, 'USE_ANYKERNEL': args.use_anykernel,
               'USE_CCACHE': args.use_ccache, 'SUSFS_PROFILE': args.profile, 'BUILD_JOBS': str(args.jobs),
               'ANDROID_NDK_ROOT': str(args.ndk)}
        # Actions variables from a parent shell must not change local execution.
        env = {k: v for k, v in env.items() if not k.startswith('GITHUB_')}
        pinned = run('bash', str(target / '.github/scripts/resolve-kernel-pin.sh'), str(target), env=env)
        kernel = pinned.splitlines()[-1]
        env['BASE_KERNEL_COMMIT'] = kernel
        if args.kernel_source == 'latest-lineage-24.0':
            kernel = run('git', 'ls-remote', p['KERNEL_REPOSITORY'], 'refs/heads/' + p['KERNEL_BRANCH']).split()[0]
            history = temp / 'kernel-history'
            subprocess.run(['git', 'init', '--bare', str(history)], check=True)
            subprocess.run(['git', '-C', str(history), 'fetch', '--filter=blob:none', p['KERNEL_REPOSITORY'],
                            'refs/heads/' + p['KERNEL_BRANCH']], check=True)
            if run('git', '-C', str(history), 'rev-parse', 'FETCH_HEAD') != kernel:
                raise ValueError('Upstream branch moved during source resolution; retry')
            subprocess.run(['git', '-C', str(history), 'merge-base', '--is-ancestor', env['BASE_KERNEL_COMMIT'], kernel], check=True)
            env['BUILD_CHANNEL'] = 'unapproved_latest'
            env['KERNEL_COMMIT_OVERRIDE'] = kernel
        env['KERNEL_COMMIT'] = kernel
        for name, seed, sha in [('KERNEL_SEED', args.kernel_seed, kernel),
                                ('SUKISU_SEED', args.sukisu_seed, p['SUKISU_COMMIT']),
                                ('SM8250_SEED', args.sm8250_seed, p['SM8250_REFERENCE_COMMIT'])]:
            if seed.exists():
                if subprocess.run(['git', '-C', str(seed), 'cat-file', '-e', sha + '^{commit}'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                    env[name] = str(seed)
        stages = ['baseline-identity', 'fingerprint']
        if args.enable_susfs == 'true':
            stages += ['references']
        stages += ['patch-preflight', 'source', 'patches', 'audit-hide', 'audit-susfs', 'audit-hooks', 'configure']
        if args.use_ccache == 'true':
            stages += ['cache-configure']
        stages += ['compile']
        if args.use_ccache == 'true':
            stages += ['cache-stats']
        stages += ['audit-build']
        if args.enable_susfs == 'true':
            stages += ['tool']
        stages += ['package' if args.use_anykernel == 'true' else 'raw', 'provenance']
        baseline = args.export_dir
        telemetry = {'builder_commit': commit, 'run_id': run_id, 'jobs': args.jobs, 'stages': [],
                     'peak_workspace_bytes': 0, 'minimum_host_free_bytes': shutil.disk_usage(baseline).free}
        space.update(builder_commit=commit, run_id=run_id)
        space['minimum_host_free_bytes'] = space['initial_host_free_bytes']
        (audit / 'space-usage.json').write_text('{}\n')
        done = threading.Event()
        def sample_space():
            record = {'time': datetime.now().astimezone().isoformat(),
                      'stage': telemetry['stages'][-1]['stage'] if telemetry['stages'] else 'snapshot',
                      'workspace_used_bytes': shutil.disk_usage(args.workspace).used,
                      'host_free_bytes': shutil.disk_usage(args.storage).free,
                      'export_free_bytes': shutil.disk_usage(args.export_dir).free,
                      'run': tree_usage(target)}
            space['samples'].append(record)
            with (audit / 'space-samples.jsonl').open('a') as trace:
                trace.write(json.dumps(record) + '\n')
        def sample():
            next_tree_sample = 0
            while not done.is_set():
                telemetry['minimum_host_free_bytes'] = min(telemetry['minimum_host_free_bytes'], shutil.disk_usage(baseline).free)
                space['minimum_host_free_bytes'] = min(space['minimum_host_free_bytes'], shutil.disk_usage(args.storage).free)
                telemetry['peak_workspace_bytes'] = max(telemetry['peak_workspace_bytes'], shutil.disk_usage(args.workspace).used)
                memory = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
                used = int(memory['MemTotal'].split()[0]) - int(memory['MemAvailable'].split()[0])
                telemetry['peak_wsl_used_memory_bytes'] = max(telemetry.get('peak_wsl_used_memory_bytes', 0), used * 1024)
                if time.monotonic() >= next_tree_sample:
                    try:
                        sample_space()
                    except OSError as error:
                        space.setdefault('measurement_errors', []).append(str(error))
                    next_tree_sample = time.monotonic() + 60
                done.wait(5)
        monitor = threading.Thread(target=sample, daemon=True)
        monitor.start()
        started = time.monotonic()
        try:
            with (audit / 'local-pipeline.log').open('w') as log:
                execute_stages(target, env, stages, log, telemetry['stages'])
            telemetry['result'] = 'build-passed'
        except BaseException as error:
            telemetry['result'] = 'failed'
            telemetry['error'] = str(error)
            raise
        finally:
            done.set()
            monitor.join()
            telemetry['elapsed_seconds'] = round(time.monotonic() - started, 2)
            (audit / 'local-result.json').write_text(json.dumps(telemetry, indent=2) + '\n')
            sample_space()
            space.update(result=telemetry['result'], run=tree_usage(target),
                         breakdown=usage_breakdown(target), cache_after=tree_usage(cache))
            (audit / 'space-usage.json').write_text(json.dumps(space, indent=2) + '\n')
        shutil.copyfile(audit / 'local-result.json', target / 'artifacts/kernel/audit/local-result.json')
        destination = export_artifacts(target, args.export_dir)
        sample_space()
        space.update(export=tree_usage(destination), export_path=str(destination))
        space['minimum_host_free_bytes'] = min(space['minimum_host_free_bytes'], shutil.disk_usage(args.storage).free)
        space['sampled_peak_run_allocated_bytes'] = max(item['run']['allocated_bytes'] for item in space['samples'])
        space['host_free_decrease_bytes'] = space['initial_host_free_bytes'] - space['minimum_host_free_bytes']
        space['net_cache_allocated_bytes'] = space['cache_after']['allocated_bytes'] - space['cache_before']['allocated_bytes']
        (audit / 'space-usage.json').write_text(json.dumps(space, indent=2) + '\n')
        print(f'Build, audit and export passed: {destination}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path.home() / 'oneplus8t-kernel')
    parser.add_argument('--storage', type=Path, default=DEFAULT_STORAGE)
    parser.add_argument('--clang', type=Path)
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--export-dir', type=Path)
    parser.add_argument('--kernel-seed', type=Path)
    parser.add_argument('--sukisu-seed', type=Path)
    parser.add_argument('--sm8250-seed', type=Path)
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument('--minimum-free-gib', type=float, default=0,
                        help='Optional free-space threshold in GiB; default: no threshold')
    parser.add_argument('--profile', choices=['smoke', 'minimal-mount', 'extended-stat', 'extended-full'], default='extended-full')
    for option in ('enable-susfs', 'enable-selinux-hide', 'use-anykernel', 'use-ccache'):
        parser.add_argument('--' + option, choices=['true', 'false'], default='true')
    parser.add_argument('--kernel-source', choices=['approved-pin', 'latest-lineage-24.0'], default='approved-pin')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--export-run', type=Path, help='Retry export of a completed run without rebuilding')
    args = parser.parse_args()
    p = pins(ROOT)
    defaults = {'clang': args.workspace / 'toolchains' / p['CLANG_REVISION'],
                'ndk': args.workspace / 'toolchains/android-ndk-r27c',
                'cache_dir': args.workspace / 'cache/pipeline-ccache',
                'export_dir': args.storage / 'artifacts', 'kernel_seed': args.workspace / 'src/kernel',
                'sukisu_seed': args.workspace / 'cache/sukisu.git',
                'sm8250_seed': args.workspace / 'cache/sm8250-reference.git'}
    for key, default in defaults.items():
        setattr(args, key, (getattr(args, key) or default).resolve())
    if not 0 <= args.minimum_free_gib < float('inf'):
        parser.error('--minimum-free-gib must be finite and non-negative')
    try:
        if args.export_run:
            print(export_artifacts(args.export_run.resolve(), args.export_dir))
        else:
            build(args)
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
