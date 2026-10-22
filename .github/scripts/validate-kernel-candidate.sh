#!/usr/bin/env bash
set -euo pipefail

root="${1:-$PWD}"
base_ref="${2:?base Git ref is required}"
output_file="${GITHUB_OUTPUT:-/dev/null}"

source "$root/.github/scripts/load-build-pins.sh" "$root"

base_pins="$(git -C "$root" show "$base_ref:config/build-pins.env")"
old_path="$(sed -n 's/^KERNEL_PIN_PATH=//p' <<< "$base_pins")"
old_branch="$(sed -n 's/^KERNEL_BRANCH=//p' <<< "$base_pins")"
case "$old_branch:$old_path" in
  lineage-23.2:pins/kernel-lineage-23.2|lineage-24.0:pins/kernel-lineage-24.0) ;;
  *) echo "::error::Unsupported previous platform bookmark."; exit 1 ;;
esac

gitlink_at() {
  local ref="$1"
  local pin_path="$2"
  local entry
  entry="$(git -C "$root" ls-tree "$ref" -- "$pin_path")"
  test "$(awk '{print $1}' <<< "$entry")" = 160000
  awk '{print $3}' <<< "$entry"
}

old_kernel="$(gitlink_at "$base_ref" "$old_path")"
new_kernel="$(gitlink_at HEAD "$KERNEL_PIN_PATH")"
[[ "$old_kernel" =~ ^[0-9a-f]{40}$ ]]
[[ "$new_kernel" =~ ^[0-9a-f]{40}$ ]]
test "$old_kernel" != 0000000000000000000000000000000000000000
test "$new_kernel" != 0000000000000000000000000000000000000000
platform_changed=false
if test "$old_branch:$old_path" != "$KERNEL_BRANCH:$KERNEL_PIN_PATH"; then
  platform_changed=true
fi

changed_files="$(git -C "$root" diff --name-only "$base_ref"...HEAD)"
needs_build=false
while IFS= read -r file; do
  case "$file" in
    .gitattributes|.gitmodules|config/*|pins/kernel-lineage-*|\
    .github/workflows/build-sukisu-ultra.yml|.github/scripts/*|patches/*.patch|scripts/build/*)
      needs_build=true
      ;;
  esac
done <<< "$changed_files"

kernel_changed=false
if test "$old_kernel" != "$new_kernel"; then
  kernel_changed=true
fi

# Also validate a platform transition when both upstream refs share one SHA.
if test "$kernel_changed" = true || test "$platform_changed" = true; then
  branch_tip="$(git ls-remote "$KERNEL_REPOSITORY" "refs/heads/$KERNEL_BRANCH" | awk 'NR == 1 {print $1}')"
  if test "$branch_tip" != "$new_kernel"; then
    echo "::error::The candidate is no longer the latest $KERNEL_BRANCH commit."
    exit 1
  fi
fi

if test "$kernel_changed" = true; then

  upstream="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/lineage-kernel-history"
  git init --bare "$upstream"
  git -C "$upstream" remote add origin "$KERNEL_REPOSITORY"
  git -C "$upstream" fetch --no-tags --filter=blob:none origin \
    "+refs/heads/$KERNEL_BRANCH:refs/remotes/origin/$KERNEL_BRANCH"

  branch_tip="$(
    git -C "$upstream" rev-parse "refs/remotes/origin/$KERNEL_BRANCH"
  )"
  if test "$branch_tip" != "$new_kernel"; then
    echo "::error::The candidate is no longer the latest $KERNEL_BRANCH commit."
    exit 1
  fi
  if ! git -C "$upstream" merge-base --is-ancestor \
    "$old_kernel" "$new_kernel"; then
    echo "::error::The $KERNEL_BRANCH branch moved backward or rewrote history."
    exit 1
  fi

  git -C "$upstream" log --reverse --date=short \
    --format='%h %ad %s' "$old_kernel..$new_kernel" \
    | tee "$root/kernel-upstream-changes.txt"
  test -s "$root/kernel-upstream-changes.txt"
elif test "$platform_changed" = true; then
  printf 'Platform transition %s -> %s; upstream kernel SHA unchanged: %s\n' \
    "$old_branch" "$KERNEL_BRANCH" "$new_kernel" > "$root/kernel-upstream-changes.txt"
fi

{
  echo "needs_build=$needs_build"
  echo "kernel_changed=$kernel_changed"
  echo "platform_changed=$platform_changed"
  echo "old_kernel=$old_kernel"
  echo "new_kernel=$new_kernel"
} >> "$output_file"

{
  echo '### Kernel candidate inspection'
  echo
  echo "- Build inputs changed: \`$needs_build\`"
  echo "- Kernel bookmark changed: \`$kernel_changed\`"
  echo "- Platform changed: $platform_changed ($old_branch -> $KERNEL_BRANCH)"
  echo "- Previous kernel: \`$old_kernel\`"
  echo "- Candidate kernel: \`$new_kernel\`"
} >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
