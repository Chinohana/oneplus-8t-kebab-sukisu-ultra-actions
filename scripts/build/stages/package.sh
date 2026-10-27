#!/usr/bin/env bash
set -euo pipefail

git init AnyKernel3
git -C AnyKernel3 remote add origin "$ANYKERNEL_REPOSITORY"
git -C AnyKernel3 fetch --no-tags --depth=1 \
  "${ANYKERNEL_SEED:-$ANYKERNEL_REPOSITORY}" "$ANYKERNEL_COMMIT"
git -C AnyKernel3 checkout --detach "$ANYKERNEL_COMMIT"
test "$(git -C AnyKernel3 rev-parse HEAD)" = "$ANYKERNEL_COMMIT"
git -C AnyKernel3 apply --check --whitespace=error-all \
  "$BUILD_ROOT/patches/anykernel3-split-status.patch"
git -C AnyKernel3 apply --whitespace=error-all \
  "$BUILD_ROOT/patches/anykernel3-split-status.patch"
python3 "$BUILD_ROOT/scripts/test-anykernel-split.py" AnyKernel3/tools/ak3-core.sh
rm -rf AnyKernel3/.git
cp \
  "kernel_experiment/$SELECTED_OUT/arch/arm64/boot/Image" \
  AnyKernel3/Image

feature_tags=""
string_feature=""
if test "$ENABLE_SUSFS" = "true"; then
  feature_tags="${PROFILE}"
  string_feature="SUSFS v2.3 ${PROFILE}"
else
  feature_tags="nosusfs"
  string_feature="no SUSFS"
fi
if test "$ENABLE_SELINUX_HIDE" = "true"; then
  feature_tags="${feature_tags}-hide"
  string_feature="${string_feature} SELinux hide"
fi
sed -i \
  "s/^kernel.string=.*/kernel.string=${BUILD_CHANNEL^^} SukiSU Ultra kebab LOS${ROM_VERSION} ${string_feature} KSU${SUKISU_DRIVER_VERSION}/" \
  AnyKernel3/anykernel.sh
sed -i 's/^do.devicecheck=.*/do.devicecheck=1/' \
  AnyKernel3/anykernel.sh
sed -i 's/^device.name1=.*/device.name1=OnePlus8T/' \
  AnyKernel3/anykernel.sh
sed -i 's/^device.name2=.*/device.name2=KB2000/' \
  AnyKernel3/anykernel.sh
sed -i 's/^device.name3=.*/device.name3=kebab/' \
  AnyKernel3/anykernel.sh
sed -i 's/^device.name4=.*/device.name4=/' \
  AnyKernel3/anykernel.sh
sed -i 's/^device.name5=.*/device.name5=/' \
  AnyKernel3/anykernel.sh
sed -i 's|^BLOCK=.*|BLOCK=/dev/block/by-name/boot;|' \
  AnyKernel3/anykernel.sh
sed -i 's/^IS_SLOT_DEVICE=.*/IS_SLOT_DEVICE=1;/' \
  AnyKernel3/anykernel.sh
sed -i 's/^do.modules=.*/do.modules=0/' \
  AnyKernel3/anykernel.sh
sed -i \
  '/^# init\.rc$/,/^append_file fstab\.tuna "usbdisk" fstab;$/d' \
  AnyKernel3/anykernel.sh
sed -i 's/^dump_boot;.*/split_boot;/' AnyKernel3/anykernel.sh
sed -i 's/^write_boot;.*/flash_boot;/' AnyKernel3/anykernel.sh

grep -Fqx \
  "kernel.string=${BUILD_CHANNEL^^} SukiSU Ultra kebab LOS${ROM_VERSION} ${string_feature} KSU${SUKISU_DRIVER_VERSION}" \
  AnyKernel3/anykernel.sh
grep -q '^device.name1=OnePlus8T$' AnyKernel3/anykernel.sh
grep -q '^device.name2=KB2000$' AnyKernel3/anykernel.sh
grep -q '^device.name3=kebab$' AnyKernel3/anykernel.sh
grep -q '^device.name4=$' AnyKernel3/anykernel.sh
grep -q '^device.name5=$' AnyKernel3/anykernel.sh
grep -q '^BLOCK=/dev/block/by-name/boot;$' \
  AnyKernel3/anykernel.sh
grep -q '^IS_SLOT_DEVICE=1;$' AnyKernel3/anykernel.sh
test "$(grep -c '^split_boot;' AnyKernel3/anykernel.sh)" = 1
test "$(grep -c '^flash_boot;' AnyKernel3/anykernel.sh)" = 1
if grep -Eq \
  '^(dump_boot|write_boot|backup_file|replace_string|insert_line|append_file|patch_fstab);?' \
  AnyKernel3/anykernel.sh; then
  echo "::error::An unauthorized ramdisk modification command remains."
  exit 1
fi
if grep -Eq \
  '(^|[./])tuna([./;]|$)|device.name[45]=.+' \
  AnyKernel3/anykernel.sh; then
  echo "::error::Example-device content remains in AnyKernel3."
  exit 1
fi

rm -f AnyKernel3/README.md
package_name="${BUILD_CHANNEL^^}_SukiSU_kebab_LOS${ROM_VERSION}_${feature_tags}_K${KERNEL_COMMIT:0:7}_SU${SUKISU_COMMIT:0:7}_KSU${SUKISU_DRIVER_VERSION}"
(
  cd AnyKernel3
  zip -r9 "../${package_name}.zip" . \
    -x '.git/*' '*placeholder'
)
sha256sum "${package_name}.zip" |
  tee "${package_name}.zip.sha256"
echo "PACKAGE_NAME=$package_name" >> "$BUILD_ENV"
echo "KERNEL_ARTIFACT_NAME=$package_name" >> "$BUILD_ENV"
