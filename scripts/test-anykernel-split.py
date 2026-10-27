#!/usr/bin/env python3
"""Exercise the packaged split_boot function against harmless local files."""
from pathlib import Path
import subprocess
import sys
import tempfile


def check(script):
    source = Path(script).read_text()
    function = source[source.index('split_boot() {'):source.index('# unpack_vendorrd')]
    cases = [(0, False, False), (1, False, True), (2, False, False), (0, True, True)]
    for unpack_status, tee_failure, should_abort in cases:
        with tempfile.TemporaryDirectory(prefix='ak3-split-') as name:
            root = Path(name)
            (root / 'tools').mkdir()
            (root / 'partition').write_bytes(b'test boot partition\n')
            harness = '''
AKHOME=$PWD
BIN=$PWD/tools
SPLITIMG=$PWD/split_img
BLOCK=$PWD/partition
BOOTIMG=$PWD/boot.img
abort() { echo "ABORT: $*" >&2; exit 42; }
magiskboot() { return "$UNPACK_STATUS"; }
if [ "$TEE_FAILURE" = 1 ]; then
  tee() { cat >/dev/null; return 1; }
fi
''' + function + '\nsplit_boot\nprintf "SPLIT_PASSED\\n"\n'
            # No set -e: Recovery uses the installer's explicit status handling.
            result = subprocess.run(
                ['bash', '-c', harness], cwd=root,
                env={'PATH': '/usr/bin:/bin', 'UNPACK_STATUS': str(unpack_status),
                     'TEE_FAILURE': str(int(tee_failure))},
                capture_output=True, text=True)
            expected = 42 if should_abort else 0
            if result.returncode != expected:
                raise AssertionError(
                    f'unpack={unpack_status}, tee_failure={tee_failure}: '
                    f'expected {expected}, got {result.returncode}\n{result.stderr}')
            assert (root / 'partition').read_bytes() == b'test boot partition\n'
    print('AnyKernel3 split_boot: 4 status/pipeline cases passed')


if __name__ == '__main__':
    check(sys.argv[1])
