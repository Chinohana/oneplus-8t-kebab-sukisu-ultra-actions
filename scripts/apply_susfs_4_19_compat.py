#!/usr/bin/env python3
"""Apply the narrow SUSFS compatibility fix for LineageOS SM8250 4.19.

Run this only after the upstream kernel-4.19 patch.  The upstream patch is
written for the pre-fs_context mount path; this kernel creates mounts in
vfs_create_mount() instead.  Every edit below is guarded by exact matches.
"""

from pathlib import Path


ROOT = Path.cwd()
EXPECTED_REJECTS = {
    Path("fs/namespace.c.rej"),
    Path("fs/proc/task_mmu.c.rej"),
    Path("include/linux/mount.h.rej"),
}


def read(path: str) -> str:
    return (ROOT / path).read_text()


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content)


def replace_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return content.replace(old, new, 1)


def replace_once_in_region(
    content: str,
    start_marker: str,
    end_marker: str,
    old: str,
    new: str,
    label: str,
) -> str:
    start = content.find(start_marker)
    if start < 0:
        raise RuntimeError(f"{label}: start marker not found")
    end = content.find(end_marker, start)
    if end < 0:
        raise RuntimeError(f"{label}: end marker not found")
    region = content[start:end]
    region = replace_once(region, old, new, label)
    return content[:start] + region + content[end:]


rejects = {
    path.relative_to(ROOT)
    for path in ROOT.rglob("*.rej")
}
if rejects != EXPECTED_REJECTS:
    raise RuntimeError(
        "unexpected upstream patch rejects: "
        f"expected {sorted(map(str, EXPECTED_REJECTS))}, "
        f"found {sorted(map(str, rejects))}"
    )


namespace_path = "fs/namespace.c"
namespace = read(namespace_path)

namespace = replace_once(
    namespace,
    """#include <linux/fs_context.h>
#include "pnode.h"
#include "internal.h"

/* Maximum number of mounts in a mount namespace */
""",
    """#include <linux/fs_context.h>
#if defined(CONFIG_KSU_SUSFS_SUS_MOUNT) || defined(CONFIG_KSU_SUSFS_TRY_UMOUNT)
#include <linux/susfs_def.h>
#endif

#include "pnode.h"
#include "internal.h"

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
extern bool susfs_is_current_ksu_domain(void);
extern bool susfs_is_current_zygote_domain(void);

static DEFINE_IDA(susfs_mnt_id_ida);
static DEFINE_IDA(susfs_mnt_group_ida);

#define CL_ZYGOTE_COPY_MNT_NS BIT(24) /* used by copy_mnt_ns() */
#define CL_COPY_MNT_NS BIT(25) /* used by copy_mnt_ns() */
#endif

#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
extern void susfs_auto_add_sus_ksu_default_mount(const char __user *to_pathname);
bool susfs_is_auto_add_sus_ksu_default_mount_enabled = true;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
extern int susfs_auto_add_sus_bind_mount(const char *pathname, struct path *path_target);
bool susfs_is_auto_add_sus_bind_mount_enabled = true;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
extern void susfs_auto_add_try_umount_for_bind_mount(struct path *path);
bool susfs_is_auto_add_try_umount_for_bind_mount_enabled = true;
#endif

/* Maximum number of mounts in a mount namespace */
""",
    "namespace includes and SUSFS declarations",
)

namespace = replace_once_in_region(
    namespace,
    "struct vfsmount *vfs_create_mount(struct fs_context *fc)",
    "EXPORT_SYMBOL(vfs_create_mount);",
    '\tmnt = alloc_vfsmnt(fc->source ?: "none");\n',
    """#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	/* fs_context kernels allocate new mounts here, not in vfs_kern_mount(). */
	if (unlikely(susfs_is_current_ksu_domain()))
		mnt = alloc_vfsmnt(fc->source ?: "none", true, 0);
	else
		mnt = alloc_vfsmnt(fc->source ?: "none", false, 0);
#else
	mnt = alloc_vfsmnt(fc->source ?: "none");
#endif
""",
    "vfs_create_mount SUSFS allocation",
)

vfs_start = namespace.find("struct vfsmount *vfs_create_mount(struct fs_context *fc)")
vfs_end = namespace.find("EXPORT_SYMBOL(vfs_create_mount);", vfs_start)
vfs_region = namespace[vfs_start:vfs_end]
if "susfs_last_fake_mnt_id" not in vfs_region:
    namespace = replace_once_in_region(
        namespace,
        "struct vfsmount *vfs_create_mount(struct fs_context *fc)",
        "EXPORT_SYMBOL(vfs_create_mount);",
        """	mnt->mnt_mountpoint	= mnt->mnt.mnt_root;
	mnt->mnt_parent		= mnt;

	lock_mount_hash();
""",
        """	mnt->mnt_mountpoint	= mnt->mnt.mnt_root;
	mnt->mnt_parent		= mnt;

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	/* Normal zygote mounts retain their original ID as a backup. */
	if (susfs_is_current_zygote_domain()) {
		mnt->mnt.susfs_mnt_id_backup = mnt->mnt_id;
		mnt->mnt_id = current->susfs_last_fake_mnt_id++;
	}
#endif

	lock_mount_hash();
""",
        "vfs_create_mount zygote mount ID",
    )

namespace = replace_once_in_region(
    namespace,
    "static struct mount *clone_mnt(struct mount *old, struct dentry *root,",
    "\nstruct mount *copy_tree(",
    '\tmnt = alloc_vfsmnt(old->mnt_devname);\n',
    """#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	bool is_current_ksu_domain = susfs_is_current_ksu_domain();
	bool is_current_zygote_domain = susfs_is_current_zygote_domain();

	/*
	 * CL_COPY_MNT_NS distinguishes a namespace copy from a single clone.
	 * Preserve the upstream SUSFS mount-ID behavior for KSU, zygote, and
	 * ordinary namespace copies.
	 */
	if (unlikely(is_current_ksu_domain)) {
		if (!(flag & CL_COPY_MNT_NS)) {
			mnt = alloc_vfsmnt(old->mnt_devname, true, 0);
			goto bypass_orig_flow;
		}
		mnt = alloc_vfsmnt(old->mnt_devname, true, old->mnt_id);
		if (mnt)
			mnt->mnt.susfs_mnt_id_backup =
				DEFAULT_SUS_MNT_ID_FOR_KSU_PROC_UNSHARE;
		goto bypass_orig_flow;
	}
	if (likely(is_current_zygote_domain) &&
	    old->mnt_id >= DEFAULT_SUS_MNT_ID) {
		mnt = alloc_vfsmnt(old->mnt_devname, true, 0);
		goto bypass_orig_flow;
	}
	if ((flag & CL_COPY_MNT_NS) &&
	    old->mnt_id >= DEFAULT_SUS_MNT_ID) {
		mnt = alloc_vfsmnt(old->mnt_devname, true, 0);
		goto bypass_orig_flow;
	}
	mnt = alloc_vfsmnt(old->mnt_devname, false, 0);
bypass_orig_flow:
#else
	mnt = alloc_vfsmnt(old->mnt_devname);
#endif
""",
    "clone_mnt SUSFS allocation",
)

namespace = replace_once_in_region(
    namespace,
    "static struct mount *clone_mnt(struct mount *old, struct dentry *root,",
    "\nstruct mount *copy_tree(",
    """	mnt->mnt_mountpoint = mnt->mnt.mnt_root;
	mnt->mnt_parent = mnt;

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	// If caller process is zygote, then it is a normal mount, so we just reorder the mnt_id
	if (susfs_is_current_zygote_domain()) {
		mnt->mnt.susfs_mnt_id_backup = mnt->mnt_id;
		mnt->mnt_id = current->susfs_last_fake_mnt_id++;
	}
#endif

	lock_mount_hash();
""",
    """	mnt->mnt_mountpoint = mnt->mnt.mnt_root;
	mnt->mnt_parent = mnt;

#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (likely(is_current_zygote_domain) &&
	    !(flag & CL_ZYGOTE_COPY_MNT_NS)) {
		mnt->mnt.susfs_mnt_id_backup = mnt->mnt_id;
		mnt->mnt_id = current->susfs_last_fake_mnt_id++;
	}
#endif

	lock_mount_hash();
""",
    "clone_mnt zygote mount ID",
)

write(namespace_path, namespace)


task_mmu_path = "fs/proc/task_mmu.c"
task_mmu = read(task_mmu_path)
task_mmu = replace_once(
    task_mmu,
    """#include <linux/mm_inline.h>
#include <linux/ctype.h>
""",
    """#include <linux/mm_inline.h>
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
#include <linux/susfs_def.h>
#endif
#include <linux/ctype.h>
""",
    "task_mmu SUSFS include",
)
write(task_mmu_path, task_mmu)


mount_path = "include/linux/mount.h"
mount = read(mount_path)
mount = replace_once(
    mount,
    """	ANDROID_KABI_RESERVE(3);
	ANDROID_KABI_RESERVE(4);
""",
    """	ANDROID_KABI_RESERVE(3);
#ifdef CONFIG_KSU_SUSFS
	ANDROID_KABI_USE(4, u64 susfs_mnt_id_backup);
#else
	ANDROID_KABI_RESERVE(4);
#endif
#if defined(CONFIG_KSU_SUSFS) && !defined(ANDROID_KABI_RESERVE)
	u64 susfs_mnt_id_backup;
#endif
""",
    "vfsmount SUSFS KABI field",
)
write(mount_path, mount)


for reject in EXPECTED_REJECTS:
    (ROOT / reject).unlink()

for original in ROOT.rglob("*.orig"):
    original.unlink()

remaining = list(ROOT.rglob("*.rej"))
if remaining:
    raise RuntimeError(f"unhandled rejects remain: {remaining}")

print("Applied verified LineageOS SM8250 4.19 SUSFS compatibility edits.")
