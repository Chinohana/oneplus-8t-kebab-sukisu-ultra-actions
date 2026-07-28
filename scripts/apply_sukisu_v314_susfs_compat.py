#!/usr/bin/env python3
"""Finish the official SUSFS 1.5.5 integration for SukiSU Ultra v3.1.4.

Run this only after 10_enable_susfs_for_ksu.patch.  That patch targets a
nearby legacy KernelSU revision; SukiSU v3.1.4 has the same ABI but differs
at a small set of guarded locations.  Every edit below requires an exact
match.
"""

from pathlib import Path


ROOT = Path.cwd() / "KernelSU"
KERNEL_ROOT = ROOT.parent
EXPECTED_REJECTS = {
    Path("kernel/Makefile.rej"),
    Path("kernel/core_hook.c.rej"),
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def read_kernel(path: str) -> str:
    return (KERNEL_ROOT / path).read_text(encoding="utf-8")


def write_kernel(path: str, content: str) -> None:
    (KERNEL_ROOT / path).write_text(content, encoding="utf-8")


def replace_once(content: str, old: str, new: str, label: str) -> str:
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return content.replace(old, new, 1)


def require_absent(content: str, needle: str, label: str) -> None:
    if needle in content:
        raise RuntimeError(f"{label}: target is already present")


rejects = {
    path.relative_to(ROOT)
    for path in ROOT.rglob("*.rej")
}
if rejects != EXPECTED_REJECTS:
    raise RuntimeError(
        "unexpected SukiSU integration rejects: "
        f"expected {sorted(map(str, EXPECTED_REJECTS))}, "
        f"found {sorted(map(str, rejects))}"
    )


makefile_path = "kernel/Makefile"
makefile = read(makefile_path)
makefile_marker = """\
ccflags-y += -Wno-implicit-function-declaration -Wno-strict-prototypes -Wno-int-conversion -Wno-gcc-compat
ccflags-y += -Wno-declaration-after-statement -Wno-unused-function

# Keep a new line here!! Because someone may append config
"""
makefile_replacement = r"""ccflags-y += -Wno-implicit-function-declaration -Wno-strict-prototypes -Wno-int-conversion -Wno-gcc-compat
ccflags-y += -Wno-declaration-after-statement -Wno-unused-function

## SUSFS legacy non-GKI compatibility ##
ifeq ($(shell grep -q " current_sid(void)" $(srctree)/security/selinux/include/objsec.h; echo $$?),0)
ccflags-y += -DKSU_COMPAT_HAS_CURRENT_SID
endif

ifeq ($(shell grep -q "struct selinux_state " $(srctree)/security/selinux/include/security.h; echo $$?),0)
ccflags-y += -DKSU_COMPAT_HAS_SELINUX_STATE
endif

ccflags-y += -DKSU_UMOUNT

ifneq ($(shell grep -Eq "get_cred_rcu" $(srctree)/include/linux/cred.h; echo $$?),0)
$(info -- KSU_SUSFS: backporting get_cred_rcu() to include/linux/cred.h)
GET_CRED_RCU = static inline const struct cred *get_cred_rcu(const struct cred *cred)\n\
{\n\t\
	struct cred *nonconst_cred = (struct cred *) cred;\n\t\
	if (!cred)\n\t\t\
		return NULL;\n\t\
	if (!atomic_inc_not_zero(&nonconst_cred->usage))\n\t\t\
		return NULL;\n\t\
	validate_creds(cred);\n\t\
	return cred;\n\
}\n
$(shell sed -i '/^static inline void put_cred/i $(GET_CRED_RCU)' $(srctree)/include/linux/cred.h;)
endif

ifneq ($(shell grep -Eq "^static int can_umount" $(srctree)/fs/namespace.c; echo $$?),0)
$(info -- KSU_SUSFS: backporting can_umount() to fs/namespace.c)
CAN_UMOUNT = static int can_umount(const struct path *path, int flags)\n\
{\n\t\
	struct mount *mnt = real_mount(path->mnt);\n\t\
	if (flags & ~(MNT_FORCE | MNT_DETACH | MNT_EXPIRE | UMOUNT_NOFOLLOW))\n\t\t\
		return -EINVAL;\n\t\
	if (!may_mount())\n\t\t\
		return -EPERM;\n\t\
	if (path->dentry != path->mnt->mnt_root)\n\t\t\
		return -EINVAL;\n\t\
	if (!check_mnt(mnt))\n\t\t\
		return -EINVAL;\n\t\
	if (mnt->mnt.mnt_flags & MNT_LOCKED)\n\t\t\
		return -EINVAL;\n\t\
	if (flags & MNT_FORCE && !capable(CAP_SYS_ADMIN))\n\t\t\
		return -EPERM;\n\t\
	return 0;\n\
}\n
$(shell sed -i '/^static bool is_mnt_ns_file/i $(CAN_UMOUNT)' $(srctree)/fs/namespace.c;)
endif

ifneq ($(shell grep -Eq "^int path_umount" $(srctree)/fs/namespace.c; echo $$?),0)
$(info -- KSU_SUSFS: backporting path_umount() to fs/namespace.c)
PATH_UMOUNT = int path_umount(struct path *path, int flags)\n\
{\n\t\
	struct mount *mnt = real_mount(path->mnt);\n\t\
	int ret;\n\t\
	ret = can_umount(path, flags);\n\t\
	if (!ret)\n\t\t\
		ret = do_umount(mnt, flags);\n\t\
	dput(path->dentry);\n\t\
	mntput_no_expire(mnt);\n\t\
	return ret;\n\
}\n
$(shell sed -i '/^static bool is_mnt_ns_file/i $(PATH_UMOUNT)' $(srctree)/fs/namespace.c;)
endif

ifneq ($(shell grep -Eq "^int path_umount" $(srctree)/fs/internal.h; echo $$?),0)
$(shell sed -i '/^extern void __init mnt_init/a int path_umount(struct path *path, int flags);' $(srctree)/fs/internal.h;)
$(info -- KSU_SUSFS: declaring path_umount() in fs/internal.h)
endif

ifeq ($(shell test -e $(srctree)/fs/susfs.c; echo $$?),0)
$(eval SUSFS_VERSION=$(shell grep -E '^#define SUSFS_VERSION' $(srctree)/include/linux/susfs.h | cut -d' ' -f3 | sed 's/"//g'))
$(info -- SUSFS_VERSION: $(SUSFS_VERSION))
else
$(error SUSFS source is missing from the kernel tree)
endif

# Keep a new line here!! Because someone may append config
"""
makefile = replace_once(
    makefile,
    makefile_marker,
    makefile_replacement,
    "KernelSU Makefile SUSFS flags",
)
write(makefile_path, makefile)


# The official legacy patch performs these API backports from KernelSU's
# Makefile.  Apply them before parallel compilation so namespace.o cannot race
# the Makefile's source mutation.
cred_path = "include/linux/cred.h"
cred = read_kernel(cred_path)
require_absent(cred, "get_cred_rcu", "get_cred_rcu backport")
cred_marker = "static inline void put_cred(const struct cred *_cred)\n"
cred_backport = """\
static inline const struct cred *get_cred_rcu(const struct cred *cred)
{
	struct cred *nonconst_cred = (struct cred *)cred;

	if (!cred)
		return NULL;
	if (!atomic_inc_not_zero(&nonconst_cred->usage))
		return NULL;
	validate_creds(cred);
	return cred;
}

"""
cred = replace_once(
    cred,
    cred_marker,
    cred_backport + cred_marker,
    "get_cred_rcu insertion point",
)
write_kernel(cred_path, cred)

namespace_path = "fs/namespace.c"
namespace = read_kernel(namespace_path)
require_absent(namespace, "int path_umount(", "path_umount backport")
require_absent(namespace, "static int can_umount(", "can_umount backport")
namespace_marker = "static bool is_mnt_ns_file(struct dentry *dentry)\n"
namespace_backport = """\
static int can_umount(const struct path *path, int flags)
{
	struct mount *mnt = real_mount(path->mnt);

	if (flags & ~(MNT_FORCE | MNT_DETACH | MNT_EXPIRE | UMOUNT_NOFOLLOW))
		return -EINVAL;
	if (!may_mount())
		return -EPERM;
	if (path->dentry != path->mnt->mnt_root)
		return -EINVAL;
	if (!check_mnt(mnt))
		return -EINVAL;
	if (mnt->mnt.mnt_flags & MNT_LOCKED)
		return -EINVAL;
	if (flags & MNT_FORCE && !capable(CAP_SYS_ADMIN))
		return -EPERM;
	return 0;
}

int path_umount(struct path *path, int flags)
{
	struct mount *mnt = real_mount(path->mnt);
	int ret;

	ret = can_umount(path, flags);
	if (!ret)
		ret = do_umount(mnt, flags);
	dput(path->dentry);
	mntput_no_expire(mnt);
	return ret;
}

"""
namespace = replace_once(
    namespace,
    namespace_marker,
    namespace_backport + namespace_marker,
    "mount API insertion point",
)
write_kernel(namespace_path, namespace)

internal_path = "fs/internal.h"
internal = read_kernel(internal_path)
require_absent(internal, "int path_umount(", "path_umount declaration")
internal_marker = "extern void __init mnt_init(void);\n"
internal = replace_once(
    internal,
    internal_marker,
    internal_marker + "int path_umount(struct path *path, int flags);\n",
    "path_umount declaration point",
)
write_kernel(internal_path, internal)


core_path = "kernel/core_hook.c"
core = read(core_path)
core_header_old = """\
#include "kpm/kpm.h"

static bool ksu_module_mounted = false;

extern int handle_sepolicy(unsigned long arg3, void __user *arg4);

static bool ksu_su_compat_enabled = true;
extern void ksu_sucompat_init();
extern void ksu_sucompat_exit();

static inline bool is_allow_su()
{
	if (is_manager()) {
		// we are manager, allow!
		return true;
	}
	return ksu_is_allow_uid(current_uid().val);
}
"""
core_header_new = """\
#include "kpm/kpm.h"

#ifdef CONFIG_KSU_SUSFS
bool susfs_is_allow_su(void)
{
	if (ksu_is_manager()) {
		// we are manager, allow!
		return true;
	}
	return ksu_is_allow_uid(current_uid().val);
}

extern u32 susfs_zygote_sid;
extern bool susfs_is_mnt_devname_ksu(struct path *path);
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
extern bool susfs_is_log_enabled __read_mostly;
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
extern void susfs_run_try_umount_for_current_mnt_ns(void);
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
static bool susfs_is_umount_for_zygote_system_process_enabled;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
extern bool susfs_is_auto_add_sus_bind_mount_enabled;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
extern bool susfs_is_auto_add_sus_ksu_default_mount_enabled;
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
extern bool susfs_is_auto_add_try_umount_for_bind_mount_enabled;
#endif

static inline void susfs_on_post_fs_data(void)
{
	struct path path;
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
	if (!kern_path(DATA_ADB_UMOUNT_FOR_ZYGOTE_SYSTEM_PROCESS, 0, &path)) {
		susfs_is_umount_for_zygote_system_process_enabled = true;
		path_put(&path);
	}
	pr_info("susfs_is_umount_for_zygote_system_process_enabled: %d\\n",
		susfs_is_umount_for_zygote_system_process_enabled);
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_BIND_MOUNT
	if (!kern_path(DATA_ADB_NO_AUTO_ADD_SUS_BIND_MOUNT, 0, &path)) {
		susfs_is_auto_add_sus_bind_mount_enabled = false;
		path_put(&path);
	}
	pr_info("susfs_is_auto_add_sus_bind_mount_enabled: %d\\n",
		susfs_is_auto_add_sus_bind_mount_enabled);
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT
	if (!kern_path(DATA_ADB_NO_AUTO_ADD_SUS_KSU_DEFAULT_MOUNT, 0, &path)) {
		susfs_is_auto_add_sus_ksu_default_mount_enabled = false;
		path_put(&path);
	}
	pr_info("susfs_is_auto_add_sus_ksu_default_mount_enabled: %d\\n",
		susfs_is_auto_add_sus_ksu_default_mount_enabled);
#endif
#ifdef CONFIG_KSU_SUSFS_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT
	if (!kern_path(DATA_ADB_NO_AUTO_ADD_TRY_UMOUNT_FOR_BIND_MOUNT, 0, &path)) {
		susfs_is_auto_add_try_umount_for_bind_mount_enabled = false;
		path_put(&path);
	}
	pr_info("susfs_is_auto_add_try_umount_for_bind_mount_enabled: %d\\n",
		susfs_is_auto_add_try_umount_for_bind_mount_enabled);
#endif
}
#endif

static bool ksu_module_mounted = false;

extern int ksu_handle_sepolicy(unsigned long arg3, void __user *arg4);

static bool ksu_su_compat_enabled = true;
extern void ksu_sucompat_init();
extern void ksu_sucompat_exit();

static inline bool is_allow_su()
{
	if (ksu_is_manager()) {
		// we are manager, allow!
		return true;
	}
	return ksu_is_allow_uid(current_uid().val);
}
"""
core = replace_once(
    core,
    core_header_old,
    core_header_new,
    "core_hook SUSFS declarations",
)

umount_tail_old = """\
	if (check_mnt && !should_umount(&path)) {
		return;
	}

	ksu_umount_mnt(&path, flags);
}

int ksu_handle_setuid(struct cred *new, const struct cred *old)
"""
umount_tail_new = """\
	if (check_mnt && !should_umount(&path)) {
		return;
	}

#if defined(CONFIG_KSU_SUSFS_TRY_UMOUNT) && defined(CONFIG_KSU_SUSFS_ENABLE_LOG)
	if (susfs_is_log_enabled) {
		pr_info("susfs: umounting '%s' for uid: %d\\n", mnt, uid);
	}
#endif

	ksu_umount_mnt(&path, flags);
}

#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
void susfs_try_umount_all(uid_t uid)
{
	susfs_try_umount(uid);
	ksu_try_umount("/system", true, 0, uid);
	ksu_try_umount("/system_ext", true, 0, uid);
	ksu_try_umount("/vendor", true, 0, uid);
	ksu_try_umount("/product", true, 0, uid);
	ksu_try_umount("/odm", true, 0, uid);
	ksu_try_umount("/data/adb/modules", false, MNT_DETACH, uid);
	ksu_try_umount("/debug_ramdisk", true, MNT_DETACH, uid);
}
#endif

int ksu_handle_setuid(struct cred *new, const struct cred *old)
"""
core = replace_once(
    core,
    umount_tail_old,
    umount_tail_new,
    "core_hook SUSFS try-umount bridge",
)

setuid_old = """\
	// check old process's selinux context, if it is not zygote, ignore it!
	// because some su apps may setuid to untrusted_app but they are in global mount namespace
	// when we umount for such process, that is a disaster!
	bool is_zygote_child = is_zygote(old->security);
	if (!is_zygote_child) {
		pr_info("handle umount ignore non zygote child: %d\\n",
			current->pid);
		return 0;
	}
#ifdef CONFIG_KSU_DEBUG
	// umount the target mnt
	pr_info("handle umount for uid: %d, pid: %d\\n", new_uid.val,
		current->pid);
#endif

	// fixme: use `collect_mounts` and `iterate_mount` to iterate all mountpoint and
	// filter the mountpoint whose target is `/data/adb`
	try_umount("/system", true, 0);
	try_umount("/vendor", true, 0);
	try_umount("/product", true, 0);
	try_umount("/system_ext", true, 0);
	try_umount("/data/adb/modules", false, MNT_DETACH);

	// try umount ksu temp path
	try_umount("/debug_ramdisk", false, MNT_DETACH);
"""
setuid_new = """\
#ifndef CONFIG_KSU_SUSFS_SUS_MOUNT
	// check old process's selinux context, if it is not zygote, ignore it!
	// because some su apps may setuid to untrusted_app but they are in global mount namespace
	// when we umount for such process, that is a disaster!
	bool is_zygote_child = ksu_is_zygote(old->security);
#endif
	if (!is_zygote_child) {
		pr_info("handle umount ignore non zygote child: %d\\n",
			current->pid);
		return 0;
	}
#ifdef CONFIG_KSU_DEBUG
	// umount the target mnt
	pr_info("handle umount for uid: %d, pid: %d\\n", new_uid.val,
		current->pid);
#endif

#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
	// SUSFS rules run first; KernelSU mountpoints are unmounted afterwards.
	susfs_try_umount_all(new_uid.val);
#else
	// fixme: use `collect_mounts` and `iterate_mount` to iterate all mountpoint and
	// filter the mountpoint whose target is `/data/adb`
	ksu_try_umount("/system", true, 0);
	ksu_try_umount("/vendor", true, 0);
	ksu_try_umount("/product", true, 0);
	ksu_try_umount("/system_ext", true, 0);
	ksu_try_umount("/data/adb/modules", false, MNT_DETACH);

	// try umount ksu temp path
	ksu_try_umount("/debug_ramdisk", false, MNT_DETACH);
#endif
"""
core = replace_once(
    core,
    setuid_old,
    setuid_new,
    "core_hook setuid integration",
)
write(core_path, core)


ksu_path = "kernel/ksu.c"
ksu = read(ksu_path)
ksu = replace_once(
    ksu,
    "MODULE_IMPORT_NS(VFS_internal_I_am_really_a_filesystem_and_am_NOT_a_driver);\n",
    """\
#ifdef MODULE_IMPORT_NS
MODULE_IMPORT_NS(VFS_internal_I_am_really_a_filesystem_and_am_NOT_a_driver);
#endif
""",
    "Linux 4.19 module namespace compatibility",
)
write(ksu_path, ksu)


kpm_path = "kernel/kpm/compact.c"
kpm = read(kpm_path)
kpm = replace_once(
    kpm,
    "    return is_manager();\n",
    "    return ksu_is_manager();\n",
    "KPM manager symbol rename",
)
write(kpm_path, kpm)


for reject in EXPECTED_REJECTS:
    (ROOT / reject).unlink()

for original in ROOT.rglob("*.orig"):
    original.unlink()

print("Applied guarded SukiSU v3.1.4 / SUSFS 1.5.5 compatibility edits.")
