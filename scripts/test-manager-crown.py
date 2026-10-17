#!/usr/bin/env python3
"""Host-test the patched upstream crown_manager function with authorization stubs."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="patched kernel/manager/throne_tracker.c")
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8-sig")
    start = source.index("static int crown_manager(")
    end = source.index("#define DATA_PATH_LEN", start)
    function = source[start:end]
    prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef unsigned int uid_t;
#define KSU_MAX_PACKAGE_NAME 128
#define KSU_PACKAGE_NAME "com.sukisu.ultra"
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
struct uid_data;
struct list_head { struct uid_data *first; };
struct uid_data { struct list_head list; uid_t uid; char package[128]; struct uid_data *next; };
struct crown_state { bool builtin_seen; bool builtin_crowned; };
#define list_for_each_entry(pos, head, member) \
    for ((pos) = (head)->first; (pos); (pos) = (pos)->next)
static const char *apk_package;
static const char *registered_package;
static uid_t registered_uid;
static uid_t crowned_uid;
static bool dynamic_enabled, valid_signature, builtin_signature;
static unsigned verification_calls;
static int get_pkg_from_apk_dir_path(char *out, const char *dir) {
    (void)dir;
    if (!apk_package) return -1;
    snprintf(out, KSU_MAX_PACKAGE_NAME, "%s", apk_package);
    return 0;
}
static bool is_manager_apk(char *apk) { (void)apk; return builtin_signature; }
static void ksu_set_manager_appid(uid_t uid) { crowned_uid = uid; }
static bool ksu_manager_enabled(void) { return dynamic_enabled; }
static bool ksu_dynamic_manager_verify_apk(char *apk, const char *package, uid_t uid) {
    (void)apk;
    verification_calls++;
    return valid_signature && !strcmp(package, registered_package) && uid == registered_uid;
}
'''
    suffix = r'''
static struct uid_data entries[] = {
    { .uid = 10001, .package = KSU_PACKAGE_NAME },
    { .uid = 10002, .package = "com.dynamic.one" },
    { .uid = 10003, .package = "com.dynamic.two" },
};
static struct list_head packages = { .first = entries };
static void reset(const char *package) {
    apk_package = package;
    registered_package = "com.dynamic.one";
    registered_uid = 10002;
    crowned_uid = UINT32_MAX;
    dynamic_enabled = true;
    valid_signature = true;
    builtin_signature = false;
    verification_calls = 0;
    entries[0].next = &entries[1];
    entries[1].next = &entries[2];
    entries[2].next = NULL;
}
static int scan(bool fallback) {
    struct crown_state state = { 0 };
    return crown_manager("base.apk", "apk-dir", &packages, &state, fallback);
}
int main(void) {
    reset("com.dynamic.one");
    assert(scan(false) == 0 && crowned_uid == 10002 && verification_calls == 1);
    reset("com.dynamic.one"); valid_signature = false;
    assert(scan(false) == 0 && crowned_uid == UINT32_MAX);
    reset("com.dynamic.one"); registered_uid = 11002;
    assert(scan(false) == 0 && crowned_uid == UINT32_MAX);
    /* Same certificate must not authorize another package's UID. */
    reset("com.dynamic.two");
    assert(scan(false) == 0 && crowned_uid == UINT32_MAX && verification_calls == 1);
    reset("com.foreign");
    assert(scan(false) == 0 && crowned_uid == UINT32_MAX && verification_calls == 0);
    reset("com.dynamic.one"); dynamic_enabled = false;
    assert(scan(false) == 0 && crowned_uid == UINT32_MAX && verification_calls == 0);
    reset(KSU_PACKAGE_NAME); builtin_signature = true;
    assert(scan(false) == 1 && crowned_uid == 10001 && verification_calls == 0);
    reset(KSU_PACKAGE_NAME);
    assert(scan(false) == -1 && crowned_uid == UINT32_MAX && verification_calls == 0);
    /* The caller verified the built-in certificate before signature fallback. */
    reset("com.dynamic.one"); builtin_signature = true;
    assert(scan(true) == 1 && crowned_uid == 10002 && verification_calls == 0);
    reset(NULL);
    assert(scan(false) == 0 && crowned_uid == UINT32_MAX && verification_calls == 0);
    puts("PASS: 10 Manager package/UID/signature/priority cases");
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="ksu-manager-crown-") as tmp:
        root = Path(tmp)
        cfile = root / "crown.c"
        binary = root / "crown.exe"
        cfile.write_text(prefix + function + suffix, encoding="utf-8")
        subprocess.run([
            args.cc, "-std=gnu11", "-Wall", "-Wextra", "-Werror",
            "-Wno-unused-but-set-variable", str(cfile), "-o", str(binary),
        ], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
