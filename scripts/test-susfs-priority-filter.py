#!/usr/bin/env python3
"""Host-test the actual SUSFS UID lookup and package-name validation."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def function(source, signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--cc', default='cc')
    args = parser.parse_args()
    source = args.source.read_text()
    constants = '\n'.join(line for line in source.splitlines()
                          if line.startswith('#define SUSFS_PRIORITY_UID_FILTER_'))
    prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdlib.h>
typedef unsigned int uid_t;
typedef uint32_t u32;
#define BITS_PER_LONG (sizeof(unsigned long) * 8)
#define BITS_TO_LONGS(n) (((n) + BITS_PER_LONG - 1) / BITS_PER_LONG)
#define rcu_dereference(p) (p)
#define likely(p) (p)
#define test_bit(n, bits) (((bits)[(n) / BITS_PER_LONG] >> ((n) % BITS_PER_LONG)) & 1)
#define SUSFS_LOGE(...) ((void)0)
#define IS_ERR(p) ((intptr_t)(p) < 0)
#define PTR_ERR(p) ((intptr_t)(p))
#define vmalloc malloc
#define vfree free

struct file { const char *data; };
static struct file packages;
static int read_error;

static struct file *filp_open(const char *path, int flags, int mode) {
    assert(!strcmp(path, "/data/system/packages.list"));
    assert(flags == (O_RDONLY | O_NOATIME) && mode == 0);
    return packages.data ? &packages : (struct file *)(intptr_t)-ENOENT;
}

static void filp_close(struct file *fp, void *owner) {
    assert(fp == &packages && !owner);
}

#define file_inode(fp) (fp)
#define i_size_read(fp) strlen((fp)->data)
static int kernel_read(struct file *fp, char *buf, size_t size, loff_t *pos) {
    assert(*pos == 0);
    if (read_error)
        return read_error;
    memcpy(buf, fp->data, size);
    return (int)size;
}

static int kstrtou32(const char *str, int base, u32 *out) {
    char *end;
    unsigned long value = strtoul(str, &end, base);
    if (*end || end == str || value > UINT32_MAX)
        return -EINVAL;
    *out = (u32)value;
    return 0;
}
'''
    state = r'''
struct susfs_priority_uid_filter_bitmap {
    unsigned long bits[SUSFS_PRIORITY_UID_FILTER_BITMAP_LEN];
};
static struct susfs_priority_uid_filter_bitmap *priority_uid_filter_bitmap;
'''
    tests = r'''
int main(void) {
    struct susfs_priority_uid_filter_bitmap bitmap = {0};
    char name[257];
    uid_t resolved;
    assert(susfs_resolve_priority_app_uid("com.test", &resolved) == -EAGAIN);
    packages.data = "\ncom.testing 10001 0\ncom.test 110002 0\ncom.bad wrong 0\n"
                    "com.overflow 4294977296 0\ncom.system 1000 0";
    assert(susfs_resolve_priority_app_uid("com.test", &resolved) == 0);
    assert(resolved == 10002);
    assert(susfs_resolve_priority_app_uid("com.missing", &resolved) == -ENOENT);
    assert(susfs_resolve_priority_app_uid("com.bad", &resolved) == -EINVAL);
    assert(susfs_resolve_priority_app_uid("com.overflow", &resolved) == -EINVAL);
    assert(susfs_resolve_priority_app_uid("com.system", &resolved) == -ERANGE);
    read_error = -EACCES;
    assert(susfs_resolve_priority_app_uid("com.test", &resolved) == -EACCES);
    assert(!susfs_is_priority_uid_filtered(10000));
    priority_uid_filter_bitmap = &bitmap;
    for (uid_t uid = 0; uid < 30000; uid++)
        assert(!susfs_is_priority_uid_filtered(uid));
    for (uid_t uid = 10000; uid <= 19999; uid++) {
        memset(&bitmap, 0, sizeof(bitmap));
        unsigned int bit = uid - 10000;
        bitmap.bits[bit / BITS_PER_LONG] |= 1UL << (bit % BITS_PER_LONG);
        assert(susfs_is_priority_uid_filtered(uid));
        assert(susfs_is_priority_uid_filtered(uid + 100000));
        assert(susfs_is_priority_uid_filtered(uid + 200000));
        assert(!susfs_is_priority_uid_filtered(uid + 1));
        assert(!susfs_is_priority_uid_filtered(uid - 1));
        assert(!susfs_is_priority_uid_filtered(9999));
        assert(!susfs_is_priority_uid_filtered(20000));
    }
    assert(susfs_is_valid_app_name("com.example.app_2"));
    assert(!susfs_is_valid_app_name(""));
    assert(!susfs_is_valid_app_name("."));
    assert(!susfs_is_valid_app_name(".."));
    assert(!susfs_is_valid_app_name("../com.example"));
    assert(!susfs_is_valid_app_name("com.example/app"));
    assert(!susfs_is_valid_app_name("com.example app"));
    memset(name, 'a', 255); name[255] = 0;
    assert(susfs_is_valid_app_name(name));
    name[255] = 'a'; name[256] = 0;
    assert(!susfs_is_valid_app_name(name));
    puts("PASS: SUSFS packages.list resolution, UID boundaries, multi-user lookup and bitmap isolation");
    return 0;
}
'''
    code = prefix + constants + state
    code += function(source, 'static bool susfs_is_valid_app_name(')
    code += function(source, 'static int susfs_resolve_priority_app_uid(')
    code += function(source, 'bool susfs_is_priority_uid_filtered(') + tests
    with tempfile.TemporaryDirectory(prefix='susfs-priority-') as tmp:
        cfile = Path(tmp) / 'priority.c'
        binary = Path(tmp) / 'priority'
        cfile.write_text(code)
        subprocess.run([args.cc, '-D_GNU_SOURCE', '-std=gnu11', '-Wall', '-Wextra', '-Werror',
                        str(cfile), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    main()
