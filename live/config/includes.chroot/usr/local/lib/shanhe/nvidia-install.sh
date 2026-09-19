#!/bin/sh
# NVIDIA 驱动安装 —— 山河Linux（物理机用；VMware 虚拟机请用虚拟显卡，无需本脚本）
# 由桌面「安装 NVIDIA 驱动」经 pkexec 调起，也可在终端手动 sudo 运行。
set -e
export LANG=zh_CN.UTF-8

echo "=============================================="
echo "  山河Linux —— NVIDIA 驱动安装"
echo "=============================================="

if [ "$(id -u)" != "0" ]; then
    echo "请以 root 运行（桌面图标会自动提权，或 sudo 执行本脚本）。"
    exit 1
fi

if grep -qi vmware /sys/class/dmi/id/sys_vendor 2>/dev/null; then
    echo
    echo ">> 检测到你正在 VMware 中运行。"
    echo ">> VMware 虚拟机使用 VMware 虚拟显卡（已启用 3D 加速），"
    echo ">> 不需要也不能安装 NVIDIA 原生驱动。"
    echo ">> 想在虚拟机里使用真实 NVIDIA 显卡，请查阅："
    echo ">>   docs/NVIDIA显卡指南.md（GPU 直通章节）"
    exit 0
fi

if ! command -v nvidia-detect >/dev/null 2>&1 && ! lspci 2>/dev/null | grep -qi nvidia; then
    echo ">> 未检测到 NVIDIA 显卡，无需安装。"
    exit 0
fi

echo ">> 检测显卡型号（nvidia-detect）..."
CARD=$(nvidia-detect 2>/dev/null | tail -1)
echo ">> 推荐驱动：${CARD:-nvidia-driver}"

echo ">> 刷新软件源..."
apt-get update

echo ">> 安装驱动与内核模块（约几分钟，视网速而定）..."
if [ "$CARD" = "nvidia-legacy-390xx-driver" ] || [ "$CARD" = "nvidia-tesla-driver" ]; then
    apt-get install -y "$CARD" linux-headers-amd64
else
    apt-get install -y nvidia-driver linux-headers-amd64
fi

echo ">> 更新初始化内存盘..."
update-initramfs -u

echo
echo "=============================================="
echo "  安装完成！请重启系统以启用 NVIDIA 驱动。"
echo "  验证：重启后运行  nvidia-smi"
echo "=============================================="
