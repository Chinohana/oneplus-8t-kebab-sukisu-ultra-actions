#!/usr/bin/env bash
set -euo pipefail
workspace="${BUILD_WORKSPACE:-$HOME/oneplus8t-kernel}"
repository="${BUILDER_REPOSITORY:-https://github.com/Chinohana/oneplus-8t-kebab-sukisu-ultra-actions.git}"
ref="${1:-main}"
mkdir -p "$workspace"/{src,toolchains,out,cache,audit,runs}
test "$(findmnt -n -T "$workspace" -o FSTYPE)" = ext4
if ! test -e "$workspace/control"; then
  git clone --no-checkout "$repository" "$workspace/control"
fi
test -z "$(git -C "$workspace/control" status --porcelain)"
git -C "$workspace/control" fetch --no-tags "$repository" "$ref"
git -C "$workspace/control" checkout --detach FETCH_HEAD
printf 'Builder snapshot: %s\n' "$(git -C "$workspace/control" rev-parse HEAD)"
printf 'Workspace ready: %s\nNo patches applied and no compilation started.\n' "$workspace"
