# 山河 Linux 更新日志

## v0.2.0（2026-09-20）

主题：**卅语课堂** —— 面向零基础的中文编程闯关学习中心，本系统最具差异化的功能。

### 卅语课堂（新功能）

- 全新「卅语课堂」应用（开始菜单 / 桌面入口），10 节互动课程：
  你好山河 → 变量与插值 → 数学 → 如果/否则 → 遍历循环 → 当与跳出 → 函数 →
  列表 → 字典 → 毕业项目（九九乘法表）
- 每课 = 讲解 + 可自由修改的代码 + **一键运行**（卅语 WASM 引擎在浏览器本地执行，
  全程离线）+ **闯关任务自动检查**，通过即点亮 ✓
- 学习进度与每课代码自动保存在本地（localStorage），随时继续上次进度
- 拓扑：本地静态页 + 127.0.0.1 端口服务，启动器自动拉起并打开浏览器，可重复点击
- 课程代码语法已逐条对照上游 tests/cases 校准，保证开箱即可运行

### 其他

- 系统帮助页加入课堂入口
- CI 产物文件名改为自动探测，未来版本号升级不再影响发布流水线

## v0.1.1（2026-09-20）

主题：**点击启动软件的体验优化** + CI 全自动发布。

### 启动体验优化

- **zram 内存压缩交换**（zstd，75% RAM）+ `vm.swappiness=100` / `vm.vfs_cache_pressure=50`：
  4GB 内存虚拟机开软件不再因换页卡顿，目录/索引缓存保留更充分，应用冷启动更快
- **默认关闭 Baloo 文件索引**：首次进入桌面后最大的后台 I/O 来源被移除（Dolphin 搜索可在
  系统设置手动重新开启）
- **关闭 KWallet 首用弹窗**：首次联网、首次点击不再被"创建密码钱包"对话框打断
- **界面动画时长减半**（AnimationDurationFactor=0.5）：点击响应更跟手，Win11 观感不变
- **Wine 容器初始化推迟 45 秒**并以最低优先级运行：首屏点击不再与 wineboot 抢 CPU/磁盘

### 修复

- 卅语工作室启动崩溃（`Gtk.accelerator_parse` API 拼写错误）；启动器崩溃时改为
  弹窗显示原因 + 写日志自诊断，不再无声转圈
- 用户会话与 SDDM 全部锁定 X11（修复 VMware 宿主机⇆虚拟机复制粘贴/拖放双向不通）
- 主题钩子防御式创建目标目录（修复 CI 全新环境下 Konsole 配置写入失败）
- CI：卅语 wasm 构建失败时自动回退上游预编译运行时（三级兜底）；构建日志始终上传
  Artifacts；失败时自动输出日志尾部

### CI/CD

- 新增 GitHub Actions 工作流：推送 `v*` 标签 → 自动构建 ISO → 1900MB 分卷（绕开
  GitHub 2GB 附件限制）→ 自动创建 Release 并附 SHA256
- 镜像源支持 `SHANHE_MIRROR` / `SHANHE_MIRROR_SECURITY` 环境变量覆盖（CI 用 Debian
  官方源，本地默认清华 TUNA）
- 软件包缓存走 actions/cache，二次构建显著提速

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
