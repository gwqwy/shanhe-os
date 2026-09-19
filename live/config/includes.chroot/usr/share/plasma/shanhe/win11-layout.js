// 山河Linux —— Windows 11 风格 Plasma 布局
// 由首次登录的 autostart 脚本应用一次（见 /etc/skel/.config/autostart-scripts/00-shanhe-layout.sh）

// 1) 壁纸：山河绽放
for (var i = 0; i < desktops().length; i++) {
    var d = desktops()[i];
    d.wallpaperPlugin = 'org.kde.image';
    d.currentConfigGroup = ['Wallpaper', 'org.kde.image', 'General'];
    d.writeConfig('Image', '/usr/share/wallpapers/shanhe/contents/images/1920x1080.png');
}

// 2) 移除发行版默认面板
for (var j in panels()) {
    panelById(panels()[j]).remove();
}

// 3) Windows 11 风格底部任务栏：悬浮、居中
var panel = new Panel;
panel.location = 'bottom';
panel.alignment = 'center';
panel.height = 48;
panel.floating = true;
panel.hiding = 'none';

// 开始按钮：山河徽标
var start = panel.addWidget('org.kde.plasma.private.kickoff');
start.currentConfigGroup = ['General'];
start.writeConfig('icon', 'shanhe-start');

// 居中图标任务栏
var tasks = panel.addWidget('org.kde.plasma.icontasks');
tasks.currentConfigGroup = ['General'];
tasks.writeConfig('launchers', [
    'applications:org.kde.dolphin.desktop',
    'applications:shanhe-studio.desktop',
    'applications:firefox-esr.desktop',
    'applications:org.kde.konsole.desktop'
]);

// 右侧：系统托盘 + 时钟 + 显示桌面
panel.addWidget('org.kde.plasma.private.systemtray');
var clock = panel.addWidget('org.kde.plasma.digitalclock');
clock.currentConfigGroup = ['General'];
clock.writeConfig('showDate', 'true');
panel.addWidget('org.kde.plasma.showdesktop');
