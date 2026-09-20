# 山河 Linux（ShanHe Linux）

**以 Linux 内核为基础的中文原生编程操作系统** —— 内置「卅语（sahou）」解释器与原生 IDE，
Windows 11 风格桌面，Wine 兼容层可运行 Windows 软件与游戏，支持 NVIDIA 显卡，产出一张
可在 VMware 中直接引导的 ISO 镜像。

```
一个命令构建：  sudo bash build.sh
产物：         山河Linux-0.1.1-amd64.iso  →  挂进 VMware 开机即用
```

---

## 它是什么

| 层 | 实现 |
|---|---|
| 内核 | Linux（Debian 13 打包内核；另附 `build-kernel.sh` 从 [torvalds/linux](https://github.com/torvalds/linux) 编译主线内核） |
| 基础系统 | Debian 13 (trixie) + live-build 定制，ISO 引导（BIOS/UEFI 双支持） |
| 中文编程 | 内置 **卅语** [gwqwy/sahou](https://github.com/gwqwy/sahou)：解释器、REPL、LSP、格式化、JS 转译全部预装，终端敲 `sahou` 或 `卅` 即用 |
| 原生 IDE | 预装 **卅语工作室**（语法高亮 / 一键运行 / 内置终端 / 示例库），无需安装任何编程软件 |
| 桌面 | KDE Plasma 定制成 Windows 11 风格：底部居中任务栏、开始徽标、系统托盘、Win11 蓝配色、山花壁纸 |
| Windows 软件 | Wine + Winetricks 预装，`.exe` 双击即运行；附「Wine 助手」与中文环境配置 |
| 显卡 | VMware 虚拟显卡 3D 加速开箱即用；物理机 NVIDIA 显卡提供一键安装脚本（非自由固件源已启用） |
| 输入法 | Fcitx5 + 拼音预装，开箱打中文 |

## 目录结构

```
shanhe-os/
├── build.sh                  # 一键构建 ISO（在 Debian 13 / Ubuntu 24.04+ 上以 root 运行）
├── build-kernel.sh           # 可选：从 torvalds/linux 编译主线内核并回填 ISO
├── validate.py               # 本地静态验证（语法/关键字对齐），改动后建议跑一遍
├── vendor/sahou/             # 卅语源码快照（构建时原样编译进系统）
├── live/
│   ├── auto/config           # live-build 配置
│   ├── config/
│   │   ├── package-lists/    # 装进系统的软件包清单
│   │   ├── hooks/            # 构建钩子：编译卅语 / 装编辑器 / 布主题 / 配 Wine / 中文化GRUB
│   │   └── includes.chroot/  # 原样进入系统的文件（编辑器、语法、壁纸、布局脚本…）
├── vmware/                   # VMware 虚拟机模板（.vmx）与安装指南
└── docs/                     # 架构设计 / 构建指南 / 使用手册 / Windows 兼容性 / NVIDIA 指南
                               # 附：文件传输速查（Windows ⇆ 构建机的推送/拉取命令）
```

## 快速开始

1. **构建 ISO**（需要一台 Debian 13 或 Ubuntu 24.04+ 的 Linux 环境，约 20~40 分钟）：
   ```bash
   sudo bash build.sh
   ```
2. **VMware 运行**：新建虚拟机（2 核 / 4GB+ / 30GB 磁盘，勾选 3D 加速）→ CD/DVD 挂载生成的
   ISO → 开机 → GRUB 中文菜单选「启动 山河Linux」。详见 [vmware/VMware安装指南.md](vmware/VMware安装指南.md)。
3. **写第一行中文代码**：桌面双击「卅语工作室」→ 新建 → F5 运行。
   ```saho
   # 我的第一个山河程序
   姓名 = 输入("你叫什么名字？")
   打印("你好，{姓名}！欢迎来到山河Linux。")
   ```

## 能力对照（诚实版）

| 需求 | 状态 | 说明 |
|---|---|---|
| 以 Linux 为基础 | ✅ | Linux 内核 + Debian 用户态，主线内核脚本附赠 |
| 原生中文编程 | ✅ | 卅语为系统第一语言：内置解释器、REPL（`卅` 命令）、示例、文件关联 |
| 原生编辑 sahou，不装编程软件 | ✅ | 预装「卅语工作室」IDE，含语法高亮、一键运行、格式化 |
| Windows 风格界面 | ✅ | Plasma 深度定制成 Win11 布局与配色 |
| 运行 Windows 软件 | ✅ 大多数 | Wine 兼容层；**无法 100%**：依赖 Windows 内核驱动的软件（部分杀软、反作弊网游）跑不了，详见兼容性文档 |
| 运行 Windows 游戏 | ⚠️ 部分 | 轻量/老游戏在 VMware 里即可跑；大型 3D 游戏需要真实 NVIDIA 显卡（物理机装驱动，或 VMware GPU 直通），并配 DXVK |
| NVIDIA 显卡 | ✅ | VMware 用虚拟显卡 3D 加速；物理机一键装 NVIDIA 驱动；VMware 里用真卡需 GPU 直通（文档说明） |

> 详细矩阵与原因见 [docs/Windows软件兼容说明.md](docs/Windows软件兼容说明.md) 与
> [docs/NVIDIA显卡指南.md](docs/NVIDIA显卡指南.md)。

## 许可

本项目脚本与文档以 MIT 许可发布。卅语（sahou）上游为 MIT 许可；
Linux 内核为 GPL-2.0；Debian/Wine/KDE 等各依其上游许可。
