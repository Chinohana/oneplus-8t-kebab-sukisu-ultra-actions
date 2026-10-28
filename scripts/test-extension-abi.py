#!/usr/bin/env python3
"""Host-test the actual pinned extension ABI, validation and GET/probe paths."""
from pathlib import Path
import subprocess
import sys
import tempfile


def function(source, name):
    at = source.index(name + '(')
    start = source.rfind('\n', 0, at) + 1
    opening = source.index('{', at)
    end, depth = opening + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main(kernel):
    kernel = Path(kernel).resolve()
    header = (kernel / 'extension/extension.h').read_text()
    structures = header[header.index('struct ksu_extension_handler;'):
                        header.index('int ksu_register_extension_handler(')]
    source = (kernel / 'extension/extension.c').read_text()
    dispatch = (kernel / 'supercall/dispatch.c').read_text()
    prefix = r'''
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <linux/types.h>
typedef uint32_t u32;
typedef uint64_t u64;
#define __user
#define KSU_FEATURE_FLAG_SUPPORTED 1u
#define pr_err(...) ((void)0)
#define pr_warn(...) ((void)0)
#define mutex_lock(p) ((void)(p))
#define mutex_unlock(p) ((void)(p))
'''
    supercall = (kernel / 'include/uapi/supercall.h').read_text()
    at = supercall.index('struct ksu_add_try_umount_cmd {')
    prefix += supercall[at:supercall.index('};', at) + 2] + '\n'
    prefix += '#include "' + str(kernel / 'include/uapi/extension.h') + '"\n'
    helpers = r'''
static int extension_mutex;
static const struct ksu_extension_handler *extension_handlers[KSU_EXTENSION_MAX];
static bool ksu_extension_is_forced(u32 id) { return false; }
static int ksu_extension_set(u32 id, u32 api, u64 value) { return -EOPNOTSUPP; }
static int ksu_extension_ioctl(u32 id, u32 api, void *arg) { return -EOPNOTSUPP; }
static int ksu_extension_wipe(u32 id, u32 api) { return -EOPNOTSUPP; }
static int copy_from_user(void *to, const void *from, size_t n) {
    if (!from) return 1; memcpy(to, from, n); return 0;
}
static int copy_to_user(void *to, const void *from, size_t n) {
    if (!to) return 1; memcpy(to, from, n); return 0;
}
'''
    functions = '\n'.join(function(source, name) for name in (
        'extension_api_allowed', 'extension_handler_validate', 'ksu_extension_get'))
    functions += '\n' + function(dispatch, 'extension_reply_caps') + '\n' + function(dispatch, 'do_extension')
    tests = r'''
_Static_assert(sizeof(struct ksu_extension_cmd) == 32, "ioctl payload size changed");
_Static_assert(offsetof(struct ksu_extension_cmd, api_version) == 12, "legacy reserved slot changed");
static int setter(u32 id, u64 value) { return 0; }
static int failing_get(u32 id, u64 *value) { return -EIO; }
int main(void) {
    struct ksu_extension_handler_ops ops = { .set = setter };
    struct ksu_extension_handler h = { .extension_id = 1, .min_api_version = 1 };
    assert(extension_api_allowed(&h, 0));  /* legacy callers negotiate ABI 1 */
    assert(extension_api_allowed(&h, 1));
    assert(extension_api_allowed(&h, 2));  /* newer Manager, ABI-1 builtin */
    assert(extension_handler_validate(&h) == 0);
    h.caps = KSU_EXTENSION_FLAG_STICKY;
    assert(extension_handler_validate(&h) == -EINVAL);
    h.ops = &ops;
    assert(extension_handler_validate(&h) == 0);
    h.caps |= KSU_EXTENSION_FLAG_PERSIST;
    assert(extension_handler_validate(&h) == 0);
    h.ops = NULL;
    assert(extension_handler_validate(&h) == -EINVAL);
    h.caps = KSU_FEATURE_FLAG_SUPPORTED;
    assert(extension_handler_validate(&h) == -EINVAL);
    h.caps = KSU_EXTENSION_FLAG_FORCED;
    assert(extension_handler_validate(&h) == -EINVAL);
    h.caps = 0; h.min_api_version = KSU_EXTENSION_API_VERSION + 1;
    assert(extension_handler_validate(&h) == -EINVAL);
    assert(!extension_api_allowed(&h, 0));
    extension_handlers[1] = &h;
    u32 caps = 99; u64 value = 99;
    assert(ksu_extension_get(1, 0, &value, &caps) == 0 && caps == 0 && value == 0);
    h.min_api_version = 1; h.caps = KSU_EXTENSION_FLAG_REBOOT;
    struct ksu_extension_cmd cmd = { .id = KSU_EXTENSION_ABI_PROBE_ID, .op = KSU_EXTENSION_ABI };
    assert(do_extension(&cmd) == 0 && cmd.api_version == 1);
    cmd.id = 1;
    assert(do_extension(&cmd) == -EINVAL);  /* probe requires out-of-range id */
    cmd.op = KSU_EXTENSION_GET; cmd.api_version = 0;
    assert(do_extension(&cmd) == 0);
    assert(cmd.supported == (KSU_FEATURE_FLAG_SUPPORTED | KSU_EXTENSION_FLAG_REBOOT));
    assert(cmd.api_version == 1);
    cmd.id = KSU_EXTENSION_MAX - 1;
    assert(do_extension(&cmd) == -EOPNOTSUPP);
    ops.get = failing_get; h.ops = &ops;
    assert(ksu_extension_get(1, 1, &value, &caps) == -EIO && caps == 0);
    assert(do_extension(NULL) == -EFAULT);
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='extension-abi-') as directory:
        target = Path(directory)
        c = target / 'check.c'
        c.write_text(prefix + structures + helpers + functions + tests)
        subprocess.run(['cc', '-std=gnu11', str(c), '-o', str(target / 'check')], check=True)
        subprocess.run([str(target / 'check')], check=True)
    print('Extension ABI: legacy/new caller, layout, capability validation and probe/GET checks passed')


if __name__ == '__main__':
    main(sys.argv[1])
