#!/usr/bin/env python3
"""Host-test the actual upstream mount-file classifier with filesystem stubs."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    start = source.index("enum ksu_mount_file {")
    end = source.index("int ksu_mount_hide_file_permission", start)
    classifier = source[start:end]
    prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define PROC_SUPER_MAGIC 0x9fa0
#define unlikely(x) (x)
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
struct super_block { unsigned long s_magic; };
struct inode { struct super_block *i_sb; };
struct dentry { struct { const char *name; } d_name; struct super_block *d_sb; };
struct file { struct { struct dentry *dentry; } f_path; struct inode *inode; };
'''
    suffix = r'''
int main(void) {
    struct super_block sb = { .s_magic = PROC_SUPER_MAGIC };
    struct inode inode = { .i_sb = &sb };
    struct dentry dentry = { .d_name = { .name = "mounts" }, .d_sb = &sb };
    struct file file = { .f_path = { .dentry = &dentry }, .inode = &inode };
    const char *targets[] = { "mounts", "mountinfo", "mountstats" };
    assert(ksu_mount_file_type(NULL) == KSU_MOUNT_FILE_NONE);
    file.f_path.dentry = NULL;
    assert(ksu_mount_file_type(&file) == KSU_MOUNT_FILE_NONE);
    file.f_path.dentry = &dentry;
    for (size_t i = 0; i < ARRAY_SIZE(targets); i++) {
        dentry.d_name.name = targets[i];
        sb.s_magic = PROC_SUPER_MAGIC;
        assert(ksu_mount_file_type(&file) == KSU_MOUNT_FILE_MOUNTS + i);
        sb.s_magic = 0xef53; /* ext4 */
        assert(ksu_mount_file_type(&file) == KSU_MOUNT_FILE_NONE);
        sb.s_magic = 0x01021994; /* tmpfs */
        assert(ksu_mount_file_type(&file) == KSU_MOUNT_FILE_NONE);
    }
    sb.s_magic = PROC_SUPER_MAGIC;
    dentry.d_name.name = "mountinfo.backup";
    assert(ksu_mount_file_type(&file) == KSU_MOUNT_FILE_NONE);
    puts("PASS: mount classifier handles procfs, ext4, tmpfs and non-target names");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="ksu-mount-hide-") as tmp:
        root = Path(tmp)
        cfile = root / "mount.c"
        binary = root / "mount.exe"
        cfile.write_text(prefix + classifier + suffix, encoding="utf-8")
        subprocess.run([
            args.cc, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
            str(cfile), "-o", str(binary),
        ], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
