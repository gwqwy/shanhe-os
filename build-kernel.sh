#!/bin/bash
# =============================================================================
#  山河Linux · 主线内核构建（可选进阶）
#  从 https://github.com/torvalds/linux 克隆主线内核并打包成 .deb，
#  生成山河Linux 可用的内核包（GPL-2.0，内核本身与上游一致）。
#
#  用法：
#     sudo bash build-kernel.sh              # 克隆 + 编译 + 产出 deb（约 1~2 小时）
#     sudo bash build-kernel.sh --no-clone   # 复用上次克隆的源码续编
#
#  产物：linux-image-*.deb / linux-headers-*.deb（在 build-kernel/ 下）
#  安装：把 deb 拷到山河Linux 里，sudo dpkg -i linux-image-*.deb，重启即可。
# =============================================================================
set -euo pipefail

KERNEL_REPO="https://github.com/torvalds/linux"
BUILD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/build-kernel"
SRC="$BUILD_DIR/linux"

log()  { echo -e "\033[1;34m[内核]\033[0m $*"; }
die()  { echo -e "\033[1;31m[错误]\033[0m $*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "请用 root 运行：sudo bash build-kernel.sh"

echo ">> 安装编译依赖（build-essential / flex / bison / libssl / dwarves …）"
apt-get update -qq
apt-get install -y -qq git build-essential fakeroot libncurses-dev flex bison \
    libssl-dev bc dwarves rsync cpio xz-utils zstd 2>&1 | tail -1

mkdir -p "$BUILD_DIR"

if [ "${1:-}" != "--no-clone" ]; then
    if [ -d "$SRC/.git" ]; then
        log "更新已有源码树（git pull）"
        git -C "$SRC" pull --ff-only || git -C "$SRC" fetch --depth 1 origin master
    else
        log "浅克隆 torvalds/linux 主线（仅最新版本，约 300MB 下载）"
        git clone --depth 1 "$KERNEL_REPO" "$SRC"
    fi
fi
cd "$SRC"

log "以当前系统内核配置为基底（熟悉配置可作为底线），生成 .config"
if [ -f /boot/config-"$(uname -r)" ]; then
    cp /boot/config-"$(uname -r)" .config
    ./scripts/config --set-str SYSTEM_TRUSTED_KEYS "" \
                     --set-str SYSTEM_REVOCATION_KEYS ""
    make olddefconfig
else
    log "找不到系统内核配置，改用 defconfig（x86_64 默认）"
    make defconfig
fi

log "关闭调试信息以加速编译（镜像小、编得快；需要调试可改回）"
./scripts/config --disable DEBUG_INFO

log "开始编译 deb 包（-j$(nproc)，主线内核通常 1~2 小时）"
make -j"$(nproc)" bindeb-pkg LOCALVERSION=-shanhe

log "完成！产物在 $BUILD_DIR/ 下："
ls -lh "$BUILD_DIR"/*.deb
echo
echo ">> 安装到山河Linux："
echo "     把 linux-image-*.deb 拷入系统，执行：sudo dpkg -i linux-image-*.deb"
echo "     然后 sudo update-grub 并重启（GRUB 高级选项里选新内核）。"
