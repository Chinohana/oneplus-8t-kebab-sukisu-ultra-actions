#!/usr/bin/env python3
"""Host-test upstream built-in and signature-fallback package-to-UID selection."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def function(source, name):
    start = source.index(name)
    start = source.rfind("static ", 0, start)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="patched kernel/manager/throne_tracker.c")
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    source = args.source.read_text()
    fallback = (args.source.parent.parent / "extension/dynamic_sig_fallback.c").read_text()
    # Both scan paths must authenticate the APK before mapping its package to a UID.
    assert source.index("is_manager_apk(candidate_path)") < source.index("crown_manager(candidate_path, uid_data)")
    assert "if (unlikely(!is_manager))" in source
    assert "!c->matched && (is_manager_apk(dirpath) ||" in fallback
    assert "fb_verify_dynamic(dirpath, c->parent_dir, c->uid_data)" in fallback
    assert "if (!ctx.matched)" in fallback
    assert fallback.index("if (!ctx.matched)") < fallback.index("crowned = fb_crown_by_pkg(pkg, uid_data)")
    prefix = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
typedef unsigned int uid_t;
#define KSU_MAX_PACKAGE_NAME 128
#define KSU_PACKAGE_NAME "com.sukisu.ultra"
#define pr_info(...) ((void)0)
#define pr_warn(...) ((void)0)
struct uid_data;
struct list_head { struct uid_data *first; };
struct uid_data { struct list_head list; uid_t uid; char package[128]; struct uid_data *next; };
#define list_for_each_entry(pos, head, member) \
    for ((pos) = (head)->first; (pos); (pos) = (pos)->next)
static uid_t crowned_uid;
static const char *apk_package;
static const char *registered_package = "com.signed.manager";
static uid_t registered_uid = 10002;
static bool enabled = true, valid_signature = true;
static unsigned verification_calls;
static bool ksu_manager_enabled(void) { return enabled; }
static int get_pkg_from_apk_dir_path(char *out, const char *dir) {
    (void)dir;
    if (!apk_package) return -1;
    strcpy(out, apk_package);
    return 0;
}
static bool ksu_dynamic_manager_verify_apk(char *apk, const char *package, uid_t uid) {
    (void)apk;
    verification_calls++;
    return valid_signature && !strcmp(package, registered_package) && uid == registered_uid;
}
static void ksu_set_manager_appid(uid_t uid) { crowned_uid = uid; }
'''
    suffix = r'''
int main(void) {
    struct uid_data second = { .uid = 10002, .package = "com.signed.manager" };
    struct uid_data first = { .uid = 10001, .package = KSU_PACKAGE_NAME, .next = &second };
    struct list_head packages = { .first = &first };
    crowned_uid = UINT32_MAX;
    crown_manager("base.apk", &packages);
    assert(crowned_uid == 10001);
    crowned_uid = UINT32_MAX;
    assert(fb_crown_by_pkg("com.signed.manager", &packages));
    assert(crowned_uid == 10002);
    crowned_uid = UINT32_MAX;
    assert(!fb_crown_by_pkg("com.foreign", &packages));
    assert(crowned_uid == UINT32_MAX);
    assert(!fb_crown_by_pkg("com.signed", &packages));
    assert(crowned_uid == UINT32_MAX);
    apk_package = "com.signed.manager";
    assert(fb_verify_dynamic("base.apk", "dir", &packages));
    valid_signature = false;
    assert(!fb_verify_dynamic("base.apk", "dir", &packages));
    valid_signature = true; registered_uid = 11002;
    assert(!fb_verify_dynamic("base.apk", "dir", &packages));
    registered_uid = 10002; registered_package = "com.foreign";
    assert(!fb_verify_dynamic("base.apk", "dir", &packages));
    registered_package = "com.signed.manager"; enabled = false;
    verification_calls = 0;
    assert(!fb_verify_dynamic("base.apk", "dir", &packages) && !verification_calls);
    enabled = true; apk_package = "com.foreign";
    assert(!fb_verify_dynamic("base.apk", "dir", &packages) && !verification_calls);
    apk_package = 0;
    assert(!fb_verify_dynamic("base.apk", "dir", &packages) && !verification_calls);
    packages.first = &second;
    crown_manager("base.apk", &packages);
    assert(crowned_uid == UINT32_MAX);
    packages.first = 0;
    crown_manager("base.apk", &packages);
    assert(!fb_crown_by_pkg(KSU_PACKAGE_NAME, &packages));
    assert(crowned_uid == UINT32_MAX);
    return 0;
}
'''
    with tempfile.TemporaryDirectory() as tmp:
        c = Path(tmp) / "crown.c"
        binary = Path(tmp) / "crown"
        c.write_text(prefix + function(source, "crown_manager(") + function(fallback, "fb_crown_by_pkg(") + function(fallback, "fb_verify_dynamic(") + suffix)
        subprocess.run([args.cc, "-std=gnu11", "-Wall", "-Werror", "-Wno-unused-parameter", str(c), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print("Manager package/UID selection and signature gates: passed")


if __name__ == "__main__":
    main()
