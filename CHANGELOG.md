# 山河 Linux 更新日志

## v0.1.0（2026-09-18）

首个公开版本。基于 Linux 内核（Debian 13 trixie + live-build）的中文原生编程操作系统。

### 核心

- 内置「卅语（sahou）」v0.1：源码随镜像编译，单文件解释器含 REPL / LSP / 格式化 /
  WASM 运行时，中文命令 `卅` 与 `sahou` 等价
- 预装自研「卅语工作室」IDE（GTK3 + GtkSourceView4 + VTE）：双语关键字语法高亮
  （sahou.lang 与上游 lexer 逐项对齐）、F5 一键运行、REPL 面板、格式化、示例库、
  崩溃弹窗与日志自诊断
- `.saho` 文件类型注册与双击即开，桌面预置编辑器/示例/帮助快捷方式

### 桌面与体验

- KDE Plasma 定制 Windows 11 风格：底部悬浮居中任务栏、四格开始徽标、山河蓝配色、
  「山河绽放」矢量壁纸，首次登录自动应用
- SDDM 与用户会话锁定 X11（保障 VMware 剪贴板/拖放），Fcitx5 拼音、Noto CJK 全中文环境
- 内置《帮助》手册与全套卅语文档（/usr/local/share/sahou/文档）

### 兼容与硬件

- Wine 10 + Winetricks + 中文字体映射表，.exe 双击即跑；「Wine 助手」图形工具
- VMware：open-vm-tools 客户机集成、3D 加速模板（.vmx 含复制粘贴/拖放开关）
- NVIDIA：物理机一键安装脚本（nvidia-detect 自动选型），GPU 直通文档
- GRUB 中文引导菜单，体验/安装双模式（live-installer 整盘复制安装）

### 构建系统

- `sudo bash build.sh` 一键产出 ISO（20~40 分钟）；Ubuntu 宿主机自动适配
  （自动换装 Debian 版 live-build、补 Debian 签名密钥）
- 清华 TUNA 镜像默认（可改回官方源）；构建缓存增量复用
- 构建钩子：卅语编译、IDE 部署、主题落地、Wine 中文化、镜像瘦身、GRUB 中文化
- `build-kernel.sh`：可选从 torvalds/linux 编译主线内核
- 关闭 live-build 固件自动扫描（规避联网下载型固件包构建失败），显式声明纯净固件

### 已知边界（如实说明）

- 反作弊网游、依赖 Windows 内核驱动的软件无法经 Wine 运行
- VMware 虚拟显卡下大型 3D 游戏性能有限，重度游戏需物理机 NVIDIA 或 GPU 直通
- 卅语上游 v0.1 语言能力以 https://github.com/gwqwy/sahou 为准
