#!/usr/bin/env python3
"""Adapt SukiSU Ultra's KPM access_ok calls to the Linux 4.19 API."""

import sys
from pathlib import Path


if len(sys.argv) != 2:
    raise SystemExit("usage: apply_sukisu_4_19_compat.py KERNELSU_DIRECTORY")

ksu_root = Path(sys.argv[1])
kpm_path = ksu_root / "kernel/kpm/kpm.c"
content = kpm_path.read_text()

call_count = content.count("access_ok(")
if call_count != 10:
    raise RuntimeError(
        f"expected 10 upstream KPM access_ok calls, found {call_count}"
    )

content = content.replace("access_ok(", "sukisu_access_ok(")

marker = "#define KPM_NAME_LEN 32\n"
if content.count(marker) != 1:
    raise RuntimeError("KPM compatibility insertion marker is not unique")

compat = """#if LINUX_VERSION_CODE < KERNEL_VERSION(5, 0, 0)
#define sukisu_access_ok(addr, size) \\
    access_ok(VERIFY_READ, (addr), (size))
#else
#define sukisu_access_ok(addr, size) access_ok((addr), (size))
#endif

"""
content = content.replace(marker, compat + marker, 1)

if content.count("sukisu_access_ok(") != 12:
    raise RuntimeError("unexpected KPM compatibility wrapper result")

kpm_path.write_text(content)
print("Applied verified SukiSU KPM access_ok compatibility for Linux 4.19.")
