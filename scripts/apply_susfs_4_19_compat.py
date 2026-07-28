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


def require_once(content: str, needle: str, label: str) -> None:
    count = content.count(needle)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")


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

require_once(
    namespace,
    "#define CL_COPY_MNT_NS BIT(25) /* used by copy_mnt_ns() */",
    "upstream SUSFS namespace declarations",
)

# With fuzz 3, the two upstream mount-ID blocks apply to syntactically similar
# sites rather than the fs_context-specific sites. Remove those exact upstream
# blocks first, then place them in the correct functions below.
upstream_vfs_id_block = """
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	// If caller process is zygote, then it is a normal mount, so we just reorder the mnt_id
	if (susfs_is_current_zygote_domain()) {
		mnt->mnt.susfs_mnt_id_backup = mnt->mnt_id;
		mnt->mnt_id = current->susfs_last_fake_mnt_id++;
	}
#endif

"""
namespace = replace_once(
    namespace,
    upstream_vfs_id_block,
    "",
    "remove fuzz-relocated vfs mount-ID block",
)

upstream_clone_id_block = """
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	// If caller process is zygote and not doing unshare, so we just reorder the mnt_id
	if (likely(is_current_zygote_domain) && !(flag & CL_ZYGOTE_COPY_MNT_NS)) {
		mnt->mnt.susfs_mnt_id_backup = mnt->mnt_id;
		mnt->mnt_id = current->susfs_last_fake_mnt_id++;
	}
#endif

"""
namespace = replace_once(
    namespace,
    upstream_clone_id_block,
    "",
    "remove fuzz-relocated clone mount-ID block",
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
require_once(
    task_mmu,
    "CONFIG_KSU_SUSFS_SUS_KSTAT",
    "upstream task_mmu SUSFS include",
)


mount_path = "include/linux/mount.h"
mount = read(mount_path)
require_once(
    mount,
    "susfs_mnt_id_backup",
    "upstream vfsmount SUSFS KABI field",
)


for reject in EXPECTED_REJECTS:
    (ROOT / reject).unlink()

for original in ROOT.rglob("*.orig"):
    original.unlink()

remaining = list(ROOT.rglob("*.rej"))
if remaining:
    raise RuntimeError(f"unhandled rejects remain: {remaining}")

print("Applied verified LineageOS SM8250 4.19 SUSFS compatibility edits.")
