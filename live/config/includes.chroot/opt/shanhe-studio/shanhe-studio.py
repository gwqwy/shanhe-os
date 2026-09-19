#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卅语工作室 —— 山河Linux 自带的卅语（sahou）原生集成开发环境。

功能：多标签编辑、卅语语法高亮、一键运行（F5）、交互环境（REPL）、
格式化、查找、内置示例库。全部使用中文界面。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkSource", "4")
gi.require_version("Vte", "2.91")

from gi.repository import Gdk, GLib, Gio, Gtk, GtkSource, Pango, Vte  # noqa: E402

APP_TITLE = "卅语工作室"
EXAMPLE_DIR = "/usr/local/share/sahou/示例"
DOC_TUTORIAL = "/usr/local/share/sahou/文档/03-入门教程.md"
SAHOU_BIN = shutil.which("sahou") or shutil.which("卅") or "sahou"

NEW_TEMPLATE = '''# 新建卅语程序
# 运行：按 F5（或点工具栏 ▶）

函数 打招呼(名字)
    返回 "你好，{名字}！"
完毕

姓名 = 输入("你叫什么名字？")
打印(打招呼(姓名))

遍历 n 于 从a到b(1, 4)
    打印("第 {n} 次问好：你好，山河！")
完毕
'''

UNTITLED = "未命名.saho"


def find_language():
    """定位 GtkSourceView 的卅语语法高亮定义。"""
    mgr = GtkSource.LanguageManager.get_default()
    for path in (
        "/usr/share/gtksourceview-4/language-specs",
        os.path.expanduser("~/.local/share/gtksourceview-4/language-specs"),
    ):
        if os.path.isdir(path) and path not in mgr.get_search_path():
            mgr.append_search_path(path)
    return mgr.get_language("saho")


class EditorTab:
    """一个标签页 = 一个打开的文件。"""

    def __init__(self, app, path=None):
        self.app = app
        self.path = None
        self.buffer = GtkSource.Buffer()
        if app.lang is not None:
            self.buffer.set_language(app.lang)
        self.buffer.set_highlight_matching_brackets(True)
        self.buffer.connect("changed", app.on_buffer_changed)

        self.view = GtkSource.View(buffer=self.buffer)
        self.view.set_show_line_numbers(True)
        self.view.set_highlight_current_line(True)
        self.view.set_auto_indent(True)
        self.view.set_indent_width(4)
        self.view.set_insert_spaces_instead_of_tabs(True)
        self.view.set_tab_width(4)
        self.view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.view.set_monospace(True)
        self.view.modify_font(Pango.FontDescription("Noto Sans Mono CJK SC 12"))
        self.view.connect("key-press-event", self.on_key_press)

        self.search_context = GtkSource.SearchContext.new(self.buffer, None)
        self.search_context.set_highlight(True)

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroller.add(self.view)
        self.scroller.show_all()

        if path:
            self.load(path)
        else:
            self.buffer.set_text(NEW_TEMPLATE)
            self.buffer.set_modified(False)

    # ── 文件 ──

    def load(self, path):
        if "\x00" in path:
            raise OSError("路径包含非法字符。")
        target = Path(os.path.normpath(os.path.abspath(path)))
        if not target.is_file():
            raise OSError("文件不存在或不是普通文件：" + str(target))
        text = target.read_text(encoding="utf-8")
        self.path = str(target)
        self.buffer.begin_not_undoable_action()
        self.buffer.set_text(text)
        self.buffer.end_not_undoable_action()
        self.buffer.set_modified(False)
        self.app.refresh_tab_title(self)
        self.app.update_window_title()

    def save(self, as_needed=False):
        if as_needed or not self.path:
            chosen = self.app.save_dialog(os.path.basename(self.path or UNTITLED))
            if not chosen:
                return False
            if not chosen.endswith(".saho"):
                chosen += ".saho"
            self.path = chosen
        if "\x00" in self.path:
            self.app.error_dialog("保存失败", "路径包含非法字符。")
            return False
        target = Path(os.path.normpath(os.path.abspath(self.path)))
        if target.is_dir():
            self.app.error_dialog("保存失败", "目标路径是一个目录，不是文件。")
            return False
        self.path = str(target)
        try:
            text = self.buffer.get_text(
                self.buffer.get_start_iter(), self.buffer.get_end_iter(), True)
            target.write_text(text, encoding="utf-8")
        except OSError as exc:
            self.app.error_dialog("保存失败", str(exc))
            return False
        self.buffer.set_modified(False)
        self.app.refresh_tab_title(self)
        self.app.update_window_title()
        return True

    # ── 事件 ──

    def on_key_press(self, view, event):
        # F5 = 运行；Ctrl+F = 查找
        if event.keyval == Gdk.KEY_F5:
            self.app.run_current()
            return True
        if (event.keyval in (Gdk.KEY_f, Gdk.KEY_F)
                and event.state & Gdk.ModifierType.CONTROL_MASK):
            self.app.show_search()
            return True
        return False

    def display_name(self):
        name = os.path.basename(self.path) if self.path else UNTITLED
        if self.buffer.get_modified():
            name += " ●"
        return name


class ShanHeStudio(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=APP_TITLE)
        self.set_default_size(1100, 720)
        self.lang = find_language()
        self.tabs = []

        self.accel = Gtk.AccelGroup()
        self.add_accel_group(self.accel)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)

        # 底部运行区（VTE 终端）
        self.terminal = Vte.Terminal()
        self.terminal.set_font(Pango.FontDescription("Noto Sans Mono CJK SC 11"))
        self.terminal_scroller = Gtk.ScrolledWindow()
        self.terminal_scroller.set_policy(Gtk.PolicyType.AUTOMATIC,
                                          Gtk.PolicyType.AUTOMATIC)
        self.terminal_scroller.add(self.terminal)

        self.term_pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.term_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.term_label = Gtk.Label(label="运行输出", xalign=0)
        term_close = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                   Gtk.IconSize.MENU)
        term_close.set_relief(Gtk.ReliefStyle.NONE)
        term_close.connect("clicked", lambda *_: self.term_pane.hide())
        self.term_header.pack_start(self.term_label, False, False, 4)
        self.term_header.pack_end(term_close, False, False, 4)
        self.term_pane.pack_start(self.term_header, False, False, 2)
        self.term_pane.pack_start(self.terminal_scroller, True, True, 0)

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.paned.pack1(self.notebook, resize=True, shrink=False)
        self.paned.pack2(self.term_pane, resize=False, shrink=False)
        self.paned.set_position(480)

        self.search_bar = self.build_search_bar()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(self.build_menubar(), False, False, 0)
        box.pack_start(self.build_toolbar(), False, False, 0)
        box.pack_start(self.search_bar, False, False, 0)
        box.pack_start(self.paned, True, True, 0)
        box.pack_start(self.build_statusbar(), False, False, 0)
        self.add(box)

        self.connect("delete-event", self.on_delete_event)
        self.drag_dest_set(Gtk.DestDefaults.ALL, [], Gdk.DragAction.COPY)
        self.drag_dest_add_uri_targets()
        self.connect("drag-data-received", self.on_drag_data_received)

        self.new_tab()
        self.show_all()
        self.term_pane.hide()
        self.search_bar.hide()
        self.update_window_title()

    # ── 界面构建 ──

    def build_menubar(self):
        menu = Gtk.MenuBar()

        file_menu = Gtk.Menu()
        entries = (
            ("新建", lambda *_: self.new_tab(), "<Control>N"),
            ("打开…", lambda *_: self.open_dialog(), "<Control>O"),
            ("保存", lambda *_: self.save_current(), "<Control>S"),
            ("另存为…", self.save_as_current, "<Control><Shift>S"),
            ("关闭标签", self.close_tab, "<Control>W"),
            ("退出", lambda *_: self.close() and None, None),
        )
        for label, cb, accel in entries:
            mi = Gtk.MenuItem(label=label)
            mi.connect("activate", cb)
            if accel:
                key, mods = Gtk.accelerator_parse(accel)
                mi.add_accelerator("activate", self.accel, key, mods,
                                   Gtk.AccelFlags.VISIBLE)
            file_menu.append(mi)
        file_item = Gtk.MenuItem(label="文件")
        file_item.set_submenu(file_menu)
        menu.append(file_item)

        examples_menu = Gtk.Menu()
        self.append_examples(examples_menu, EXAMPLE_DIR)
        examples_item = Gtk.MenuItem(label="示例")
        examples_item.set_submenu(examples_menu)
        menu.append(examples_item)

        help_menu = Gtk.Menu()
        mi = Gtk.MenuItem(label="卅语入门教程")
        mi.connect("activate", lambda *_: self.open_tutorial())
        help_menu.append(mi)
        mi = Gtk.MenuItem(label="关于卅语工作室")
        mi.connect("activate", self.show_about)
        help_menu.append(mi)
        help_item = Gtk.MenuItem(label="帮助")
        help_item.set_submenu(help_menu)
        menu.append(help_item)
        return menu

    def append_examples(self, menu, directory):
        if not os.path.isdir(directory):
            mi = Gtk.MenuItem(label="（示例目录未找到）")
            mi.set_sensitive(False)
            menu.append(mi)
            return
        for name in sorted(os.listdir(directory)):
            path = os.path.join(directory, name)
            if os.path.isdir(path):
                submenu = Gtk.Menu()
                item = Gtk.MenuItem(label=name)
                item.set_submenu(submenu)
                menu.append(item)
                self.append_examples(submenu, path)
            elif name.endswith(".saho"):
                item = Gtk.MenuItem(label=os.path.splitext(name)[0])
                item.connect("activate", lambda _mi, p=path: self.open_path(p))
                menu.append(item)

    def toolbar_button(self, icon_name, tip, cb):
        btn = Gtk.ToolButton()
        btn.set_icon_widget(Gtk.Image.new_from_icon_name(
            icon_name, Gtk.IconSize.LARGE_TOOLBAR))
        btn.set_label(tip)
        btn.set_tooltip_text(tip)
        btn.set_is_important(True)
        btn.connect("clicked", cb)
        return btn

    def build_toolbar(self):
        bar = Gtk.Toolbar()
        bar.set_style(Gtk.ToolbarStyle.ICONS)
        bar.insert(self.toolbar_button(
            "document-new-symbolic", "新建",
            lambda *_: self.new_tab()), -1)
        bar.insert(self.toolbar_button(
            "document-open-symbolic", "打开",
            lambda *_: self.open_dialog()), -1)
        bar.insert(self.toolbar_button(
            "document-save-symbolic", "保存",
            lambda *_: self.save_current()), -1)
        bar.insert(self.toolbar_button(
            "media-playback-start-symbolic", "运行（F5）",
            lambda *_: self.run_current()), -1)
        bar.insert(self.toolbar_button(
            "utilities-terminal-symbolic", "交互环境",
            lambda *_: self.open_repl()), -1)
        bar.insert(self.toolbar_button(
            "object-select-symbolic", "格式化",
            lambda *_: self.format_current()), -1)
        return bar

    def build_search_bar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", lambda *_: self.search_next())
        box.pack_start(self.search_entry, True, True, 6)
        next_btn = Gtk.Button(label="下一个")
        next_btn.connect("clicked", lambda *_: self.search_next())
        box.pack_start(next_btn, False, False, 0)
        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                  Gtk.IconSize.MENU)
        close_btn.connect("clicked", lambda *_: self.search_bar.hide())
        box.pack_start(close_btn, False, False, 4)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        return box

    def build_statusbar(self):
        self.statusbar = Gtk.Statusbar()
        self.cursor_cid = self.statusbar.get_context_id("cursor")
        self.status_cid = self.statusbar.get_context_id("status")
        self.statusbar.push(self.status_cid, "就绪 —— 山河Linux · 卅语工作室")
        self.statusbar.pack_end(Gtk.Label(label="UTF-8"), False, False, 4)
        return self.statusbar

    # ── 标签页管理 ──

    def new_tab(self, path=None):
        try:
            tab = EditorTab(self, path)
        except OSError as exc:
            self.error_dialog("打开失败", str(exc))
            return None
        label = Gtk.Label(label=tab.display_name())
        idx = self.notebook.append_page(tab.scroller, label)
        self.notebook.set_tab_reorderable(tab.scroller, True)
        self.notebook.set_current_page(idx)
        self.tabs.append(tab)
        tab.view.grab_focus()
        return tab

    def current(self):
        page = self.notebook.get_nth_page(self.notebook.get_current_page())
        for tab in self.tabs:
            if tab.scroller is page:
                return tab
        return self.tabs[-1] if self.tabs else None

    def refresh_tab_title(self, tab):
        idx = self.notebook.page_num(tab.scroller)
        if idx >= 0:
            self.notebook.set_tab_label_text(tab.scroller, tab.display_name())

    def update_window_title(self):
        tab = self.current()
        name = tab.display_name() if tab else ""
        self.set_title("%s%s" % (name + " — " if name else "", APP_TITLE))

    def close_tab(self, *_):
        tab = self.current()
        if not tab:
            return
        if tab.buffer.get_modified():
            dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                                    Gtk.MessageType.QUESTION, Gtk.ButtonsType.NONE,
                                    "%s 有未保存的修改，保存吗？" % tab.display_name())
            dlg.add_buttons("不保存", Gtk.ResponseType.REJECT,
                            "取消", Gtk.ResponseType.CANCEL,
                            "保存", Gtk.ResponseType.OK)
            resp = dlg.run()
            dlg.destroy()
            if resp == Gtk.ResponseType.CANCEL:
                return
            if resp == Gtk.ResponseType.OK and not tab.save():
                return
        self.tabs.remove(tab)
        self.notebook.remove(tab.scroller)
        self.update_window_title()

    # ── 打开 / 保存 ──

    def open_dialog(self, *_):
        dlg = Gtk.FileChooserDialog("打开卅语程序", self,
                                    Gtk.FileChooserAction.OPEN,
                                    ("取消", Gtk.ResponseType.CANCEL,
                                     "打开", Gtk.ResponseType.OK))
        flt = Gtk.FileFilter()
        flt.set_name("卅语程序 (*.saho)")
        flt.add_pattern("*.saho")
        dlg.add_filter(flt)
        if dlg.run() == Gtk.ResponseType.OK:
            self.open_path(dlg.get_filename())
        dlg.destroy()

    def open_path(self, path):
        path = os.path.abspath(path)
        for tab in self.tabs:
            if tab.path == path:
                self.notebook.set_current_page(self.notebook.page_num(tab.scroller))
                return
        self.new_tab(path)

    def save_dialog(self, suggested):
        dlg = Gtk.FileChooserDialog("保存卅语程序", self,
                                    Gtk.FileChooserAction.SAVE,
                                    ("取消", Gtk.ResponseType.CANCEL,
                                     "保存", Gtk.ResponseType.OK))
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name(suggested)
        folder = os.path.join(os.path.expanduser("~"), "我的程序")
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError:
            folder = os.path.expanduser("~")
        dlg.set_current_folder(folder)
        flt = Gtk.FileFilter()
        flt.set_name("卅语程序 (*.saho)")
        flt.add_pattern("*.saho")
        dlg.add_filter(flt)
        name = dlg.get_filename() if dlg.run() == Gtk.ResponseType.OK else None
        dlg.destroy()
        return name

    def save_current(self, *_):
        tab = self.current()
        if tab:
            tab.save()
            self.flash_status("已保存：" + os.path.basename(tab.path))

    def save_as_current(self, *_):
        tab = self.current()
        if tab:
            tab.save(as_needed=True)

    def open_tutorial(self):
        if os.path.exists(DOC_TUTORIAL):
            Gio.AppInfo.launch_default_for_uri("file://" + DOC_TUTORIAL, None)
        else:
            self.error_dialog("找不到教程", DOC_TUTORIAL)

    def show_about(self, *_):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self)
        dlg.set_program_name(APP_TITLE)
        dlg.set_version("1.0")
        dlg.set_comments("山河Linux 自带的卅语（sahou）集成开发环境。\n"
                         "卅语：https://github.com/gwqwy/sahou")
        dlg.set_logo_icon_name("utilities-terminal")
        dlg.run()
        dlg.destroy()

    # ── 运行 / REPL / 格式化 ──

    def run_current(self):
        tab = self.current()
        if not tab or not tab.save():
            return
        self.term_pane.show_all()
        self.paned.set_position(max(240, self.get_allocation().height - 280))
        self.spawn_terminal([SAHOU_BIN, "run", tab.path],
                            os.path.dirname(tab.path) or os.path.expanduser("~"))

    def open_repl(self):
        self.term_pane.show_all()
        self.paned.set_position(max(240, self.get_allocation().height - 280))
        self.spawn_terminal([SAHOU_BIN], os.path.expanduser("~"))

    def format_current(self):
        tab = self.current()
        if not tab or not tab.save():
            return
        try:
            proc = subprocess.run([SAHOU_BIN, "fmt", tab.path],
                                  capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError) as exc:
            self.error_dialog("格式化失败", str(exc))
            return
        if proc.returncode == 0:
            tab.load(tab.path)
            self.flash_status("已格式化：" + os.path.basename(tab.path))
        else:
            self.error_dialog("格式化失败", proc.stderr or "未知错误")

    def spawn_terminal(self, argv, cwd):
        envv = ["%s=%s" % (k, v) for k, v in os.environ.items()]
        self.term_label.set_text("运行输出 —— " + " ".join(argv))
        try:
            self.terminal.spawn_async(
                Vte.PtyFlags.DEFAULT, cwd, argv, envv,
                GLib.SpawnFlags.DEFAULT,
                None, None, None,      # child_setup 及其 data/destroy
                -1,                    # timeout
                None,                  # cancellable
                self.on_spawn_done, None)
        except TypeError:
            # 老版 VTE 的同步接口兜底
            try:
                self.terminal.spawn_sync(
                    Vte.PtyFlags.DEFAULT, cwd, argv, envv,
                    GLib.SpawnFlags.DEFAULT, None, None, None)
            except Exception as exc:
                self.error_dialog("无法启动", str(exc))

    def on_spawn_done(self, terminal, pid, error, user_data=None):
        if error is not None:
            self.error_dialog("无法启动", error.message)

    # ── 查找 ──

    def show_search(self):
        self.search_bar.show_all()
        self.search_entry.grab_focus()

    def on_search_changed(self, entry):
        tab = self.current()
        if not tab:
            return
        tab.search_context.set_search_text(entry.get_text(), True)
        self.search_next(from_start=True)

    def search_next(self, from_start=False):
        tab = self.current()
        if not tab or not self.search_entry.get_text():
            return
        if from_start:
            tab.buffer.place_cursor(tab.buffer.get_start_iter())
        insert = tab.buffer.get_insert()
        start = tab.buffer.get_iter_at_mark(insert)
        found = tab.search_context.forward(start)
        if found:
            match_start, match_end, _has_wrapped = found
            tab.buffer.select_range(match_start, match_end)
            tab.view.scroll_to_iter(match_start, 0.2, True, 0.0, 0.5)

    # ── 状态栏 ──

    def on_buffer_changed(self, buf):
        tab = self.current()
        if tab:
            self.refresh_tab_title(tab)
            self.update_window_title()
            self.update_cursor()

    def update_cursor(self, *_):
        tab = self.current()
        if not tab:
            return False
        mark = tab.buffer.get_insert()
        it = tab.buffer.get_iter_at_mark(mark)
        self.statusbar.pop(self.cursor_cid)
        self.statusbar.push(self.cursor_cid, "行 %d，列 %d" % (
            it.get_line() + 1, it.get_line_offset() + 1))
        return False

    def flash_status(self, text, seconds=4):
        ready = "就绪 —— 山河Linux · 卅语工作室"
        self.statusbar.pop(self.status_cid)
        self.statusbar.push(self.status_cid, text)

        def restore():
            self.statusbar.pop(self.status_cid)
            self.statusbar.push(self.status_cid, ready)
            return False

        GLib.timeout_add(seconds * 1000, restore)

    # ── 对话框 / 拖放 / 关闭 ──

    def error_dialog(self, title, message):
        dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                                Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                                title)
        dlg.format_secondary_text(message)
        dlg.run()
        dlg.destroy()

    def on_drag_data_received(self, widget, ctx, x, y, data, info, time):
        for uri in data.get_uris():
            path = Gio.File.new_for_uri(uri).get_path()
            if path and path.endswith(".saho"):
                self.open_path(path)
        Gtk.drag_finish(ctx, True, False, time)

    def on_delete_event(self, *_):
        for tab in list(self.tabs):
            if tab.buffer.get_modified():
                self.notebook.set_current_page(self.notebook.page_num(tab.scroller))
                before = list(self.tabs)
                self.close_tab()
                if self.tabs == before and tab in self.tabs:
                    return True  # 用户取消了关闭
        return False


def main():
    GLib.set_prgname("shanhe-studio")
    GLib.set_application_name(APP_TITLE)
    win = ShanHeStudio()
    for path in sys.argv[1:]:
        win.open_path(path)
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
