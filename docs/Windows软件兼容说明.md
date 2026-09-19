# Windows 软件兼容说明（诚实版）

山河Linux 通过 **Wine** 运行 Windows 软件。Wine 是用户态 API 转译层：
它把 Windows 程序对 Win32 API 的调用翻译成 Linux 的 POSIX/OpenGL 调用，
**不运行 Windows 内核**。这决定了能力边界 —— 下面照实说。

## 能力矩阵

| 类别 | 兼容性 | 说明 |
|---|---|---|
| 办公：Office 2010/2013、WPS、LibreOffice 文档 | ✅ 好 | Office 2016+ 部分功能欠缺；WPS Linux 原生版更佳 |
| 开发工具：VS Code、Notepad++、Sublime | ✅ 好 | 注意：本系统自带卅语工作室，无需另装 |
| 老游戏（DirectX 7~9 时代、2D） | ✅ 好 | 配合 DXVK 更佳 |
| 单机 3D 游戏（D3D9/10/11） | ⚠️ 视显卡 | 需要 Vulkan：物理 NVIDIA + DXVK 流畅；VMware 虚拟显卡只能软渲染 |
| .NET Framework 程序 | ✅ 中上 | Wine Mono 已含大部分；个别需 winetricks dotnet48 |
| 国产软件：微信/QQ/钉钉 | ⚠️ 部分 | 旧版可跑；新版多依赖驱动/反作弊 —— 建议用官方 Linux 版或网页版 |
| 反作弊网游（LOL、DNF、Valorant 等） | ❌ 不行 | 反作弊驱动要求 Windows 内核，Wine 无解（这是全 Linux 生态的边界，非本系统问题） |
| Windows 杀毒软件 / 系统优化工具 | ❌ 不行 | 依赖内核驱动 |
| UWP / Microsoft Store 应用 | ❌ 不行 | 需要 Windows 应用模型 |
| 16 位 DOS/Win9x 程序 | ❌ 不行 | 64 位系统不支持 16 位代码 |

## 提高成功率的实操建议

1. **Windows 版本**：`winecfg` → 应用程序 → Windows 版本默认 Win10。
2. **中文字体**：Wine 助手 → 中文字体修复（`winetricks cjkfonts`）。
3. **运行库**：缺 VC++/字体/组件时用 `winetricks`（如 `winetricks vcrun2019`）。
4. **独立前缀**：互相打架的程序分开容器：
   ```bash
   WINEPREFIX=~/.wine-游戏A wine setup.exe
   WINEPREFIX=~/.wine-游戏A wine 游戏A.exe
   ```
5. **3D 游戏**：确认 `vulkaninfo | grep device` 有设备；无则游戏会掉到软渲染。

## 游戏路径对比

| 环境 | 方案 | 预期 |
|---|---|---|
| VMware 虚拟机 | Wine + 虚拟显卡（OpenGL/软渲染） | 2D / 老游戏可玩 |
| VMware 虚拟机 + GPU 直通 | Wine + DXVK + 真 NVIDIA | 接近物理机（配置复杂，见 NVIDIA 指南） |
| 物理机 NVIDIA | Wine + DXVK（同 Steam Proton 技术） | 主流 3D 单机可玩 |

> Steam 平台：建议直接装 Steam Linux 版，其内置 Proton 兼容层比裸 Wine 开箱即用率高得多
> （`sudo apt install steam`）。Proton 与本系统内置的 Wine 可并存不冲突。
