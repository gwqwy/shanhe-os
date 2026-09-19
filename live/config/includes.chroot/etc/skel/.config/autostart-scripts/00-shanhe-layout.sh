#!/bin/sh
# 山河Linux 首次进入桌面：应用 Win11 布局 + 山河蓝配色（只跑一次）。
MARKER="$HOME/.config/山河布局已应用"
[ -f "$MARKER" ] && exit 0

(
    sleep 8   # 等 plasmashell 就绪

    # 配色：山河蓝
    plasma-apply-colorscheme 山河蓝 >/dev/null 2>&1 \
        || kwriteconfig5 --file kdeglobals --group General --key ColorScheme 山河蓝 2>/dev/null \
        || kwriteconfig6 --file kdeglobals --group General --key ColorScheme 山河蓝 2>/dev/null

    # 布局：Windows 11 风格任务栏
    LAYOUT=/usr/share/plasma/shanhe/win11-layout.js
    if [ -f "$LAYOUT" ]; then
        if command -v qdbus >/dev/null 2>&1; then
            qdbus org.kde.plasmashell /PlasmaShell evaluateScript "$(cat "$LAYOUT")" \
                && touch "$MARKER"
        elif command -v gdbus >/dev/null 2>&1; then
            gdbus call --session \
                --dest org.kde.plasmashell \
                --object-path /PlasmaShell \
                --method org.kde.PlasmaShell.evaluateScript \
                "$(cat "$LAYOUT")" >/dev/null \
                && touch "$MARKER"
        fi
    fi
) &
exit 0
