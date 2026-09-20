#!/bin/bash
# =============================================================================
#  山河Linux 一键构建
#  产出：山河Linux-<版本>-amd64.iso（可在 VMware / 物理机引导）
#
#  用法：
#     sudo bash build.sh              # 标准构建
#     sudo bash build.sh --no-di      # 不带"安装到硬盘"引导项（纯体验模式）
#
#  环境要求：Debian 13 或 Ubuntu 24.04+（需能联网安装 live-build 等工具）
# =============================================================================
set -euo pipefail

VERSION="0.1.1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIVE_DIR="$ROOT/live"
VENDOR="$ROOT/vendor/sahou"
INC="$LIVE_DIR/config/includes.chroot"

log()  { echo -e "\033[1;34m[山河]\033[0m $*"; }
warn() { echo -e "\033[1;33m[注意]\033[0m $*"; }
die()  { echo -e "\033[1;31m[错误]\033[0m $*" >&2; exit 1; }

# ── 0. 环境检查 ──────────────────────────────────────────────
[ "$(id -u)" = "0" ] || die "请用 root 运行：sudo bash build.sh"
command -v apt-get >/dev/null || die "只支持 Debian/Ubuntu 系宿主机"
if grep -qi vmware /sys/class/dmi/id/sys_vendor 2>/dev/null; then
    warn "你在 VMware 里的 Linux 中构建——可以，但建议在单独的 Linux 虚拟机/物理机上进行，构建耗时较长。"
fi

log "安装构建依赖（live-build / rsync / 等）"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq live-build rsync binutils xorriso squashfs-tools \
    debootstrap dosfstools e2fsprogs curl 2>&1 | grep -v "^Selecting\|^Preparing\|^Unpacking\|^Setting up" || true

# ── Debian 归档密钥（Ubuntu 宿主机必需） ─────────────────────
# 在 Ubuntu 上构建 Debian 系统时，debootstrap 要校验 Debian Release 签名，
# Ubuntu 默认不含 debian-archive-keyring，缺失会报
# "Cannot check Release signature; keyring file not available"。
if ! dpkg -s debian-archive-keyring >/dev/null 2>&1; then
    log "安装 Debian 归档签名密钥（Ubuntu 宿主机构建 Debian 系统必需）"
    apt-get install -y debian-archive-keyring \
        || die "debian-archive-keyring 安装失败：请确认已启用 universe 软件源后重试"
fi

# ── live-build 版本校正 ──────────────────────────────────────
# Ubuntu 自带的 live-build 是 3.0~a57 老分支，不认 --image-name/--updates 等选项。
# Debian 官方版版本号形如 20230502 / 20250505+deb13u1（纯脚本包，无编译依赖），
# 检测到版本号不是 20xxxxxx 格式就自动从 Debian 源换装。
LB_VER="$(dpkg-query -W -f='${Version}' live-build 2>/dev/null || echo none)"
if ! echo "$LB_VER" | grep -qE '^2[0-9]{7}'; then
    warn "宿主机 live-build（$LB_VER）是老分支/不兼容，自动换装 Debian 官方版"
    rm -f "$LIVE_DIR/config/bootstrap" "$LIVE_DIR/config/chroot" \
          "$LIVE_DIR/config/binary" "$LIVE_DIR/config/common" \
          "$LIVE_DIR/config/source" 2>/dev/null || true
    rm -rf "$LIVE_DIR/config/archives" 2>/dev/null || true
    POOL="https://deb.debian.org/debian/pool/main/l/live-build"
    DEB=$(curl -fsSL --retry 3 "$POOL/" \
          | grep -oE 'live-build_[0-9][^"]*_all\.deb' | sort -uV | tail -1)
    [ -n "$DEB" ] || die "无法从 Debian 源获取 live-build 版本列表（检查网络）"
    log "下载并安装 $DEB"
    curl -fsSL --retry 3 -o "/tmp/$DEB" "$POOL/$DEB"
    apt-get install -y "/tmp/$DEB" || dpkg -i "/tmp/$DEB"
    rm -f "/tmp/$DEB"
    log "live-build 已切换为 $(dpkg-query -W -f='${Version}' live-build)"
fi

# ── 1. 准备 includes：把卅语源码放进系统（chroot 内离线编译） ──
log "布置卅语（sahou）源码到系统内 /usr/local/src/sahou"
if [ ! -d "$VENDOR" ]; then
    warn "vendor/sahou 缺失，尝试从 GitHub 克隆……"
    git clone --depth 1 https://github.com/gwqwy/sahou.git "$VENDOR"
fi
rm -rf "$INC/usr/local/src/sahou"
mkdir -p "$INC/usr/local/src"
rsync -a --exclude '.git' --exclude '*.exe' --exclude 'sahou.wasm' \
      --exclude 'assets' "$VENDOR/" "$INC/usr/local/src/sahou/"

# ── 2. live-build 配置 ───────────────────────────────────────
cd "$LIVE_DIR"
log "lb clean（清理上一次构建，保留软件包缓存以便增量重跑）"
lb clean noauto >/dev/null 2>&1 || true

log "lb config（生成构建配置）"

# ── 2.5 钩子布局适配 ─────────────────────────────────────────
# 新版 live-build（trixie）只扫描 config/hooks/{normal,live}/ 子目录，且要求
# 两个目录各至少有一个 chroot 钩子才会执行；旧版（bookworm）扫描扁平目录。
# 策略：扁平目录是唯一源，构建时复制到 live/，并在 normal/ 放一个无害占位。
HOOKS_SRC="$LIVE_DIR/config/hooks"
HOOKS_LIVE="$HOOKS_SRC/live"
HOOKS_NORMAL="$HOOKS_SRC/normal"
mkdir -p "$HOOKS_LIVE" "$HOOKS_NORMAL"
cp -f "$HOOKS_SRC"/*.chroot "$HOOKS_LIVE"/ 2>/dev/null || true
cp -f "$HOOKS_SRC"/*.binary "$HOOKS_LIVE"/ 2>/dev/null || true
printf '#!/bin/sh\ntrue\n' > "$HOOKS_NORMAL/0000-noop.chroot"
chmod +x "$HOOKS_LIVE"/* "$HOOKS_NORMAL"/* 2>/dev/null || true

if [ "${1:-}" = "--no-di" ]; then
    NO_DI=1
else
    # 自动探测本机 live-build 是否支持 debian-installer
    if lb config --help 2>/dev/null | grep -q "debian-installer"; then
        NO_DI=0
    else
        NO_DI=1
        warn "本机 live-build 不支持 debian-installer，将构建纯 Live 版（仍可安装，见文档）"
    fi
fi

if [ "$NO_DI" = "0" ]; then
    sh auto/config
else
    sh auto/config --debian-installer none
fi

# ── 3. 构建 ─────────────────────────────────────────────────
log "开始构建 ISO（下载软件包 + 编译卅语 + 打包，约 20~40 分钟）……"
lb build

# ── 4. 产物 ─────────────────────────────────────────────────
ISO_SRC="$LIVE_DIR/shanhe-amd64.hybrid.iso"
ISO_OUT="$ROOT/山河Linux-${VERSION}-amd64.iso"
[ -f "$ISO_SRC" ] || ISO_SRC="$LIVE_DIR/shanhe-amd64.iso"
[ -f "$ISO_SRC" ] || die "构建结束但未找到 ISO 文件，请检查上方日志"
mv -f "$ISO_SRC" "$ISO_OUT"

log "构建完成！"
echo
echo "   产物：$ISO_OUT  ($(du -h "$ISO_OUT" | cut -f1))"
echo
echo "   下一步："
echo "     1) 打开 vmware/VMware安装指南.md，新建虚拟机挂载此 ISO"
echo "     2) GRUB 菜单选「启动 山河Linux」体验，或「安装 山河Linux」装盘"
echo "     3) 桌面双击「卅语工作室」开始中文编程"
echo
