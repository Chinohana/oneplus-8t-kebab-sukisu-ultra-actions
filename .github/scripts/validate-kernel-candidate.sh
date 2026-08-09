#!/usr/bin/env bash
set -euo pipefail

root="${1:-$PWD}"
base_ref="${2:?base Git ref is required}"
output_file="${GITHUB_OUTPUT:-/dev/null}"

source "$root/.github/scripts/load-build-pins.sh" "$root"

gitlink_at() {
  local ref="$1"
  local allow_migration_fallback="${2:-false}"
  local entry
  entry="$(git -C "$root" ls-tree "$ref" -- "$KERNEL_PIN_PATH")"
  if test -z "$entry" && test "$allow_migration_fallback" = true; then
    printf '%s\n' "$SM8250_REFERENCE_BASE_COMMIT"
    return
  fi
  test "$(awk '{print $1}' <<< "$entry")" = 160000
  awk '{print $3}' <<< "$entry"
}

old_kernel="$(gitlink_at "$base_ref" true)"
new_kernel="$(gitlink_at HEAD)"
test "$old_kernel" != 0000000000000000000000000000000000000000
test "$new_kernel" != 0000000000000000000000000000000000000000

changed_files="$(git -C "$root" diff --name-only "$base_ref"...HEAD)"
needs_build=false
while IFS= read -r file; do
  case "$file" in
    .gitmodules|config/*|pins/kernel-lineage-23.2|\
    .github/workflows/build-sukisu-ultra.yml|.github/scripts/*.sh|patches/*.patch)
      needs_build=true
      ;;
  esac
done <<< "$changed_files"

kernel_changed=false
if test "$old_kernel" != "$new_kernel"; then
  kernel_changed=true
  test "$KERNEL_BRANCH" = lineage-23.2

  upstream="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/lineage-kernel-history"
  git init --bare "$upstream"
  git -C "$upstream" remote add origin "$KERNEL_REPOSITORY"
  git -C "$upstream" fetch --no-tags --filter=blob:none origin \
    "+refs/heads/$KERNEL_BRANCH:refs/remotes/origin/$KERNEL_BRANCH"

  branch_tip="$(
    git -C "$upstream" rev-parse "refs/remotes/origin/$KERNEL_BRANCH"
  )"
  if test "$branch_tip" != "$new_kernel"; then
    echo "::error::The candidate is no longer the latest lineage-23.2 commit."
    exit 1
  fi
  if ! git -C "$upstream" merge-base --is-ancestor \
    "$old_kernel" "$new_kernel"; then
    echo "::error::The lineage-23.2 branch moved backward or rewrote history."
    exit 1
  fi

  git -C "$upstream" log --reverse --date=short \
    --format='%h %ad %s' "$old_kernel..$new_kernel" \
    | tee "$root/kernel-upstream-changes.txt"
  test -s "$root/kernel-upstream-changes.txt"
fi

{
  echo "needs_build=$needs_build"
  echo "kernel_changed=$kernel_changed"
  echo "old_kernel=$old_kernel"
  echo "new_kernel=$new_kernel"
} >> "$output_file"

{
  echo '### Kernel candidate inspection'
  echo
  echo "- Build inputs changed: \`$needs_build\`"
  echo "- Kernel bookmark changed: \`$kernel_changed\`"
  echo "- Previous kernel: \`$old_kernel\`"
  echo "- Candidate kernel: \`$new_kernel\`"
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
