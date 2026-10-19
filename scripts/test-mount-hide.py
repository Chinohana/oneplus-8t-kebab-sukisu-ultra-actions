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
    start = source.index("#define KSU_PROC_MAGIC_NAME_MAX")
    end = source.index("static bool ksu_should_hide_mount_for_current", start)
    classifier = source[start:end]
    prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#define PROC_SUPER_MAGIC 0x9fa0
#define ARRAY_SIZE(a) (sizeof(a) / sizeof((a)[0]))
struct super_block { unsigned long s_magic; };
struct inode { struct super_block *i_sb; };
struct dentry { struct { const char *name; } d_name; };
struct file { struct { struct dentry *dentry; } f_path; struct inode *inode; };
static struct inode *file_inode(struct file *file) { return file->inode; }
'''
    suffix = r'''
int main(void) {
    struct super_block sb = { .s_magic = PROC_SUPER_MAGIC };
    struct inode inode = { .i_sb = &sb };
    struct dentry dentry = { .d_name = { .name = "mounts" } };
    struct file file = { .f_path = { .dentry = &dentry }, .inode = &inode };
    const char *targets[] = { "mounts", "mountinfo", "mountstats" };
    assert(!ksu_path_is_proc_mount_file(NULL));
    file.f_path.dentry = NULL;
    assert(!ksu_path_is_proc_mount_file(&file));
    file.f_path.dentry = &dentry;
    for (size_t i = 0; i < ARRAY_SIZE(targets); i++) {
        dentry.d_name.name = targets[i];
        sb.s_magic = PROC_SUPER_MAGIC;
        assert(ksu_path_is_proc_mount_file(&file));
        sb.s_magic = 0xef53; /* ext4 */
        assert(!ksu_path_is_proc_mount_file(&file));
        sb.s_magic = 0x01021994; /* tmpfs */
        assert(!ksu_path_is_proc_mount_file(&file));
    }
    sb.s_magic = PROC_SUPER_MAGIC;
    dentry.d_name.name = "mountinfo.backup";
    assert(!ksu_path_is_proc_mount_file(&file));
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
