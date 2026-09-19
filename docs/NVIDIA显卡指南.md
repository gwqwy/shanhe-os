# NVIDIA 显卡指南

山河Linux 对英伟达显卡的支持分三种场景，请对号入座。

## 场景一：VMware 虚拟机（默认场景）✅ 开箱即用

虚拟机里"用显卡"用的是 **VMware 虚拟 GPU**（宿主机显卡通过 VMware 的 3D
加速能力模拟提供 OpenGL），不是 NVIDIA 原生驱动 —— 这是虚拟化图形的正确形态：

- 虚拟机设置 → 显示器 → 勾选 **加速 3D 图形**，图形内存设 4GB；
- 系统已内置 Mesa 3D 与 open-vm-tools，开机即用；
- 桌面合成、视频、绝大多数 Wine 程序够用；
- 重度 3D 游戏受虚拟 GPU 性能限制 —— 想畅玩请看场景二/三。

**本场景不需要也不应运行「安装 NVIDIA 驱动」**（脚本检测到 VMware 会主动提示）。

## 场景二：物理机安装山河Linux + NVIDIA 显卡 ✅ 一键安装

1. 开始菜单 → **安装 NVIDIA 驱动**（或终端手动）：
   ```bash
   sudo /usr/local/lib/shanhe/nvidia-install.sh
   ```
   脚本自动：检测型号（nvidia-detect）→ 安装 non-free 官方驱动 + 内核头 →
   更新 initramfs。
2. 重启，终端验证：
   ```bash
   nvidia-smi          # 应显示显卡型号、驱动版本
   glxinfo | grep renderer
   ```
3. 注意：BIOS 开了 **Secure Boot** 时需在重启时给驱动模块签名确认（提示框选
   Enroll/继续即可）。

## 场景三：VMware 里直通真实 NVIDIA 显卡（GPU Passthrough）⚠️ 进阶

要让虚拟机"摸到"物理 NVIDIA 卡，需要 GPU 直通（VT-d/AMD-Vi + IOMMU）：

1. 宿主机 BIOS 开启 VT-d / IOMMU；
2. Linux 宿主内核参数加 `intel_iommu=on iommu=pt`（或 amd_iommu）；
3. VMware Workstation（15+）→ 虚拟机设置 → 添加 PCI 设备 → 选 NVIDIA GPU；
   勾选「保留全部内存映射 I/O」（虚拟机 → 高级）；
4. 虚拟机内即可像物理机一样执行场景二的驱动安装；
5. 限制：直通后宿主机不再占用该卡（显示输出归虚拟机），且需要两张卡或
   接受宿主无显示。

> Workstation 级别的直通对笔记本 Optimus 双显卡支持有限；重度需求建议
> 用 KVM/QEMU（Looking Glass）或 ESXi。

## Vulkan 与游戏（DXVK）

Windows 3D 游戏的主流方案是 **DXVK**（D3D9/10/11 → Vulkan，Steam Proton 同款），
它要求可用 Vulkan 驱动：

| 环境 | Vulkan 提供 | DXVK 游戏表现 |
|---|---|---|
| VMware（3D 加速） | lavapipe 软渲染（CPU 模拟） | 能跑但慢，适合 2D/老 3D |
| 物理 NVIDIA（驱动装好后） | nvidia 原生 Vulkan | 接近 Windows 原生 |

验证：`vulkaninfo --summary`；安装 DXVK：把 release 包内 `x64/*.dll` 放进游戏
目录并 `winecfg` 每程序启用。

## 常见问题

| 现象 | 处理 |
|---|---|
| `nvidia-smi: command not found` | 驱动没装上：重跑安装脚本看报错 |
| 装驱动后黑屏 | GRUB 加 `nouveau.modeset=0`（已由驱动包自动处理）；或恢复模式下 `apt remove --purge '~nnvidia'` |
| 双显卡笔记本 | 用 `prime-run 程序` 指定跑 N 卡（驱动包自带） |
| Wine 游戏提示缺 d3d11 | 换 DXVK；或 `winetricks dxvk`（需联网） |
