#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卅语工作室 —— 山河Linux 自带的卅语（sahou）原生集成开发环境。

功能：多标签编辑、卅语语法高亮、一键运行（F5）、交互环境（REPL）、
格式化、查找替换、内置示例库、关键字自动补全、智能缩进（自动补「完毕」）、
网页预览（转译 + 本地服务）、tokens/ast 诊断、stones 库包管理。
全部使用中文界面。
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

from gi.repository import Gdk, GLib, Gio, GObject, Gtk, GtkSource, Pango, Vte  # noqa: E402

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

# 卅语源码快照位置：`sahou 打包` 需要在此仓库内运行（打包时会把解释器源码一并编译）
SAHOU_SRC = "/usr/local/src/sahou"

# ── 卅语速查数据（与上游 lexer.go 的 KeyWords / sahou.lang 对齐） ──
# 关键字：20 个语句关键字 + 3 个常量（中/英双语可混用）
KEYWORDS = [
    ("如果", "if", "条件分支开始"),
    ("又如", "elif", "分支的另一种情况"),
    ("否则", "else", "以上都不成立时"),
    ("当", "while", "条件为真时反复执行"),
    ("遍历", "for", "依次取出每个元素"),
    ("于", "in", "遍历 … 于 集合"),
    ("完毕", "end", "结束一个块（如果 / 遍历 / 函数 …）"),
    ("函数", "fn", "定义函数"),
    ("返回", "return", "函数返回一个值"),
    ("设", "let", "声明变量（可省略）"),
    ("并且", "and", "逻辑与"),
    ("或者", "or", "逻辑或"),
    ("非", "not", "逻辑非"),
    ("尝试", "try", "捕获运行期错误"),
    ("接住", "catch", "接住错误并处理"),
    ("格子", "cell", "响应式变量（依赖变化自动重算）"),
    ("跳出", "break", "跳出当前循环"),
    ("继续", "continue", "跳过本轮剩余部分"),
    ("用", "use", "引入模块或标准库包"),
    ("引入", "import", "用 “包名” 引入"),
    ("真", "true", "布尔真"),
    ("假", "false", "布尔假"),
    ("空值", "null", "空值"),
]

# 内置函数（30 个，中/英双语）
BUILTINS = [
    ("打印", "print", "输出到屏幕（可加参数 结尾:）"),
    ("输入", "input", "从键盘读一行"),
    ("数", "num", "转成数 / 取数"),
    ("文本", "str", "转成文本"),
    ("列表", "list", "构造列表"),
    ("字典", "dict", "构造字典"),
    ("从a到b", "range_to", "生成整数序列（含 a 不含 b）"),
    ("长度", "len", "元素个数"),
    ("取", "slice", "取子串 / 子列表"),
    ("抛出", "throw", "抛出错误"),
    ("类型", "type_of", "取值的类型名"),
    ("包含", "contains", "是否包含某元素"),
    ("求和", "sum", "求和"),
    ("最大值", "max", "最大值"),
    ("最小值", "min", "最小值"),
    ("排序", "sorted", "排序（返回新列表）"),
    ("反转", "reversed", "反转"),
    ("连接", "join", "用分隔符连接列表"),
    ("分割", "split", "按分隔符切分文本"),
    ("替换", "replace", "替换子串"),
    ("修剪", "trim", "去掉首尾空白"),
    ("转大写", "upper", "转大写"),
    ("转小写", "lower", "转小写"),
    ("绝对值", "abs", "绝对值"),
    ("平方根", "sqrt", "平方根"),
    ("四舍五入", "round", "四舍五入"),
    ("读取文件", "read_file", "读文件内容"),
    ("写入文件", "write_file", "写文件"),
    ("文件存在", "file_exists", "文件是否存在"),
    ("位置", "find", "查找元素位置"),
]

# 标准库模块（预置，不写 用…引入 也能用）
STD_MODULES = [
    ("网络", "服务 / 路由 / 监听，HTTP 客户端与 JSON"),
    ("页面", "浏览器 DOM 操作（转译或 wasm 运行）"),
    ("网页", "服务端模板渲染（[[键]] 自动转义）"),
    ("数据库", "嵌入式 SQL + 单文件持久化"),
    ("应用", "桌面窗口 / 手机端 / 写页面"),
    ("测试", "相等 / 为真 / 汇总断言"),
    ("随机", "随机数与随机选择"),
    ("时间", "时间戳与格式化"),
    ("数学", "三角函数、幂、对数等"),
    ("编码", "Base64 / 十六进制等"),
    ("系统", "环境变量、命令行参数、退出"),
]

# exe 自带的标准库包（stones，`用 “包名” 引入` 免安装）
STONES = [
    ("算术库", "加减乘除与常用算术函数"),
    ("文本库", "文本处理函数"),
    ("游戏库", "小游戏相关函数"),
    ("中文数字", "阿拉伯数字 ⇆ 中文数字"),
    ("集合运算", "并集 / 交集 / 差集"),
    ("统计库", "均值 / 方差等统计量"),
    ("单位换算", "长度 / 重量 / 温度换算"),
    ("进制库", "二 / 八 / 十六进制转换"),
    ("几何库", "面积 / 周长 / 体积"),
    ("算法库", "常用算法（排序 / 查找等）"),
]

# 常见报错 → 处理提示（取自上游 tests/cases 的真实报错文案）
ERROR_HINTS = [
    ("还没有定义", "名字拼错了，或者在使用前还没赋值。卅语会顺带给出「你是不是想写 …」的候选。"),
    ("你是不是想写", "字典键名 / 变量名 / 函数名拼写有误，按提示改成候选名即可。"),
    ("缺少 完毕", "块（如果 / 又如 / 否则 / 遍历 / 当 / 函数 / 尝试 / 接住）没有用 完毕 收尾。"),
    ("程序在这里就结束了", "某个块没写完就结束了，检查是否漏了 完毕 或表达式不完整。"),
    ("比较不能连写", "不能写 a < b < c；用 并且 连接：a < b 并且 b < c。"),
    ("不能把", "两个值类型不同（如 文本 与 数）；用 文本(...) / 数(...) 转换后再运算。"),
    ("下标不能是负数", "列表与文本的下标从 0 开始，不能为负。"),
    ("内置函数", "不能给内置函数名重新赋值（如 打印 = 1），换一个变量名。"),
    ("全角", "标点用了全角（如 ＝ 、 ｛ ）；改用半角 = { } ( ) 等。"),
    ("引号", "字符串引号没成对，检查是否漏了右引号。"),
]


def hint_for(message):
    """把解释器的报错映射成一条更易读的中文提示（速查面板「常见报错」同源）。"""
    for key, tip in ERROR_HINTS:
        if key in message:
            return "提示：" + tip
    return ("提示：对照《工具 → 卅语速查 → 常见报错》，"
            "或打开 /usr/local/share/sahou/文档 查阅中文教程。")


# 代码片段库（名称 → 可直接插入的代码）
SNIPPETS = [
    ("入门：问好", '''名字 = 输入("你叫什么名字？")
打印("你好，{名字}！欢迎来到山河Linux。")
'''),
    ("函数定义", '''函数 打招呼(名字)
    返回 "你好，{名字}！"
完毕
'''),
    ("如果 / 否则", '''如果 条件
    打印("成立")
否则
    打印("不成立")
完毕
'''),
    ("遍历循环", '''遍历 i 于 从a到b(0, 10)
    打印(i)
完毕
'''),
    ("当循环", '''计数 = 0
当 计数 < 10
    打印(计数)
    计数 = 计数 + 1
完毕
'''),
    ("字典（当对象用）", '''小猫 = {"名字": "咪咪", "饥饿": 0}
打印(小猫["名字"])
'''),
    ("列表操作", '''名单 = ["小明", "小红", "小刚"]
打印(长度(名单))
打印(排序(名单))
'''),
    ("尝试 / 接住", '''尝试
    数("不是数字")
接住 错误信息
    打印("出错了：{错误信息}")
完毕
'''),
    ("管道流水线", '''结果 = [3, 1, 2] -> 排序(?) -> 取(?, 0, 2)
打印(结果)
'''),
    ("响应式格子", '''数量 = 格子(2)
单价 = 格子(3.5)
合计 = 格子(单价 * 数量)
打印(合计)
'''),
    ("引入标准库", '''用 "算术库" 引入
用 "文本库" 引入
'''),
    ("数据库入门", '''库 = 数据库.打开("数据.db")
库.执行("建 表 如无 订单 (编号 自增, 客户, 金额)")
库.执行("插入 订单 (客户, 金额) 值 (?, ?)", "小明", 10)
'''),
    ("写页面（控件）", '''页 = 应用.写页面("我的应用", 460, 360)
页.标签("3 × 4 = ?")
'''),
    ("九九乘法表", '''函数 乘法表()
    遍历 i 于 从a到b(1, 10)
        遍历 j 于 从a到b(1, i + 1)
            打印("{j}×{i}={i * j}", 结尾: "  ")
        完毕
        打印("")
    完毕
完毕

乘法表()
'''),
]


# ── 智能编辑常量（v0.3.0 续：编辑器增强） ──
# 需要 完毕 收尾的块起始关键字（回车时自动补 完毕 并缩进）
BLOCK_OPENERS = ("函数", "如果", "又如", "否则", "遍历", "当", "尝试", "接住")
# 自动配对的括号与引号（左 → 右）
BRACKET_PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"'}
# 光标左侧是这些字符时，按右括号/引号不重复插入
CLOSING_CHARS = set(BRACKET_PAIRS.values()) | {")", "]", "}"}
# 行注释前缀（卅语用 #）
COMMENT_PREFIX = "# "
# 缩进宽度（与视图 set_indent_width 一致）
INDENT = 4
# 字号档位（编辑器增强：Ctrl+= / Ctrl+- / Ctrl+0）
FONT_FAMILY = "Noto Sans Mono CJK SC"
FONT_SIZES = (10, 11, 12, 13, 14, 16, 18, 20, 24)
DEFAULT_FONT_INDEX = 2  # 对应 12
# 最近打开文件（自管，不依赖 GtkRecent）
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "shanhe-studio")
RECENT_FILE = os.path.join(CONFIG_DIR, "recent.json")
RECENT_MAX = 12
# 网页预览用（sahou serve 默认地址）
SERVE_HOST = "127.0.0.1"
SERVE_PORT = 8000


def load_recent():
    """读取最近打开文件列表（失败时返回空表，不打扰用户）。"""
    try:
        import json
        with open(RECENT_FILE, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, list):
            return [p for p in data if isinstance(p, str)]
    except (OSError, ValueError):
        pass
    return []


def save_recent(paths):
    """写回最近打开文件列表；写不进去也不报错。"""
    try:
        import json
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(RECENT_FILE, "w", encoding="utf-8") as fh:
            json.dump(list(paths)[:RECENT_MAX], fh, ensure_ascii=False, indent=1)
    except OSError:
        pass


def completion_candidates():
    """自动补全候选：(插入文本, 显示名, 说明)。复用速查表的数据。"""
    items = []
    for zh, en, desc in KEYWORDS:
        items.append((zh, zh, en + " · " + desc))
    for zh, en, desc in BUILTINS:
        items.append((zh + "(", zh, en + " · " + desc))
    for name, desc in STD_MODULES:
        items.append((name + ".", name, "标准库 · " + desc))
    for name, desc in STONES:
        items.append(('用 "%s" 引入' % name, name, "自带库包 · " + desc))
    return items


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


class SahoProposal(GObject.Object, GtkSource.CompletionItem):
    """一条补全候选：label 即插入文本（保证插入正确），markup 负责好看。"""

    def __init__(self, insert, show, info):
        GObject.Object.__init__(self)
        self.insert_text = insert
        self.show_name = show
        self.info_text = info

    def do_get_label(self):
        return self.insert_text

    def do_get_text(self):
        return self.insert_text

    def do_get_markup(self):
        return "<b>%s</b>  <small>%s</small>" % (
            GLib.markup_escape_text(self.show_name),
            GLib.markup_escape_text(self.info_text))

    def do_get_info(self):
        return self.info_text


class SahoCompletionProvider(GObject.Object, GtkSource.CompletionProvider):
    """卅语关键词 / 内置函数 / 标准库 / 自带库包 的自动补全。"""

    def __init__(self):
        GObject.Object.__init__(self)
        self.items = completion_candidates()

    def do_get_name(self):
        return "卅语补全"

    def do_get_priority(self):
        return 200

    def do_get_activation(self):
        return GtkSource.CompletionActivation.INTERACTIVE

    def _current_word(self, context):
        """尽力取出光标处的当前词（旧版接口没有 get_word 时手工回溯）。"""
        try:
            word = context.get_word()
            if word is not None:
                return word
        except Exception:
            pass
        try:
            import re
            it = context.get_iter()
            buf = it.get_buffer()
            line_start = buf.get_iter_at_line(it.get_line())
            text = buf.get_text(line_start, it, True)
            found = re.search(r"[0-9A-Za-z_\u4e00-\u9fa5]+$", text)
            return found.group(0) if found else ""
        except Exception:
            return ""

    def do_populate(self, context):
        word = self._current_word(context)
        proposals = []
        for insert, show, info in self.items:
            if word and word not in show and word not in info:
                continue
            proposals.append(SahoProposal(insert, show, info))
        return proposals


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
        self.apply_font()
        self.view.connect("key-press-event", self.on_key_press)
        app.attach_completion(self.view)

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
        """编辑器智能键：运行 / 查找 / 跳转 / 注释 / 字号 / 缩进 / 补括号 / 补完毕。"""
        ctrl = bool(event.state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(event.state & Gdk.ModifierType.SHIFT_MASK)
        kv = event.keyval
        if kv == Gdk.KEY_F5:
            self.app.run_current()
            return True
        if ctrl and kv in (Gdk.KEY_f, Gdk.KEY_F):
            self.app.show_search()
            return True
        if ctrl and kv in (Gdk.KEY_g, Gdk.KEY_G):
            self.app.goto_line()
            return True
        if ctrl and kv in (Gdk.KEY_slash, Gdk.KEY_question):
            self.toggle_comment()
            return True
        if ctrl and kv in (Gdk.KEY_plus, Gdk.KEY_equal, Gdk.KEY_KP_Add):
            self.app.zoom_font(1)
            return True
        if ctrl and kv in (Gdk.KEY_minus, Gdk.KEY_KP_Subtract):
            self.app.zoom_font(-1)
            return True
        if ctrl and kv in (Gdk.KEY_0, Gdk.KEY_KP_0):
            self.app.zoom_font(0)
            return True
        if ctrl:
            return False
        if kv == Gdk.KEY_ISO_Left_Tab or (kv == Gdk.KEY_Tab and shift):
            self.indent_lines(dedent=True)
            return True
        if kv == Gdk.KEY_Tab:
            if self.buffer.get_selection_bounds():
                self.indent_lines()
                return True
            return False
        if kv in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            return self.auto_indent_return(view, event)
        if self.auto_pair(view, event):
            return True
        return False

    def apply_font(self):
        """按当前字号刷新编辑器字体（Ctrl+= / Ctrl+- / Ctrl+0 共用）。"""
        desc = Pango.FontDescription("%s %d" % (FONT_FAMILY, self.app.font_size))
        self.view.modify_font(desc)

    def _selected_lines(self):
        """选区覆盖的行号区间 [起, 止]（无选区则当前行）。"""
        buf = self.buffer
        if buf.get_selection_bounds():
            start, end = buf.get_selection_bounds()
        else:
            start = end = buf.get_iter_at_mark(buf.get_insert())
        return start.get_line(), end.get_line()

    def _line_end(self, n):
        it = self.buffer.get_iter_at_line(n)
        it.forward_to_line_end()
        return it

    def toggle_comment(self):
        """整行注释 / 取消注释（Ctrl+/）。"""
        buf = self.buffer
        first, last = self._selected_lines()
        texts = []
        for n in range(first, last + 1):
            it = buf.get_iter_at_line(n)
            texts.append(buf.get_text(it, self._line_end(n), True))
        commented = all(text.lstrip().startswith("#") for text in texts)
        buf.begin_user_action()
        for n in range(first, last + 1):
            it = buf.get_iter_at_line(n)      # 逐行重取，上一行的改动会让旧迭代器失效
            if commented:
                text = texts[n - first]
                pos = len(text) - len(text.lstrip())
                remove = 2 if text[pos:pos + 2] == "# " else 1
                head = it.copy()
                head.forward_chars(pos)
                tail = head.copy()
                tail.forward_chars(remove)
                buf.delete(head, tail)
            else:
                buf.insert(it, COMMENT_PREFIX)
        buf.end_user_action()
        self.app.flash_status("已取消注释" if commented else "已注释本行")

    def indent_lines(self, dedent=False):
        """整块缩进 / 反缩进（Tab / Shift+Tab）。"""
        buf = self.buffer
        first, last = self._selected_lines()
        buf.begin_user_action()
        for n in range(first, last + 1):
            it = buf.get_iter_at_line(n)
            if dedent:
                if not buf.get_text(it, self._line_end(n), True).strip():
                    continue
                stop = it.copy()
                stop.forward_chars(INDENT)
                chunk = buf.get_text(it, stop, True)
                if chunk.startswith("\t"):
                    one = it.copy()
                    one.forward_chars(1)
                    buf.delete(it, one)
                else:
                    spaces = min(len(chunk) - len(chunk.lstrip(" ")), INDENT)
                    if spaces:
                        cut = it.copy()
                        cut.forward_chars(spaces)
                        buf.delete(it, cut)
            else:
                if buf.get_text(it, self._line_end(n), True).strip():
                    buf.insert(it, " " * INDENT)
        buf.end_user_action()

    def auto_pair(self, view, event):
        """输入左括号 / 引号时自动补右半；有选区则用括号包住。"""
        ch = chr(event.keyval)
        if ch not in BRACKET_PAIRS:
            return False
        close = BRACKET_PAIRS[ch]
        buf = self.buffer
        if buf.get_selection_bounds():
            start, end = buf.get_selection_bounds()
            selected = buf.get_text(start, end, True)
            buf.begin_user_action()
            buf.delete(start, end)
            buf.insert_at_cursor(ch + selected + close)
            buf.end_user_action()
            return True
        it = buf.get_iter_at_mark(buf.get_insert())
        after = it.copy()
        if after.forward_char() and buf.get_text(it, after, True) == close:
            buf.place_cursor(after)          # 右边已存在，跨过去不重复插入
            return True
        buf.insert_at_cursor(ch + close)
        back = buf.get_iter_at_offset(
            buf.get_iter_at_mark(buf.get_insert()).get_offset() - 1)
        buf.place_cursor(back)
        return True

    def auto_indent_return(self, view, event):
        """回车：块起始行自动补一行空行 + 缩进 + 完毕，光标停在中间。"""
        buf = self.buffer
        it = buf.get_iter_at_mark(buf.get_insert())
        if it.get_offset() != self._line_end(it.get_line()).get_offset():
            return False                      # 只在行尾才自动补
        text = buf.get_text(buf.get_iter_at_line(it.get_line()), it, True)
        stripped = text.strip()
        if not stripped.startswith(BLOCK_OPENERS) or stripped.startswith("#"):
            return False                      # 交给视图默认的自动缩进
        indent = text[:len(text) - len(text.lstrip())]
        buf.begin_user_action()
        buf.insert_at_cursor("\n" + indent + " " * INDENT
                             + "\n" + indent + "完毕")
        buf.end_user_action()
        cursor = (buf.get_iter_at_mark(buf.get_insert()).get_offset()
                  - len(indent) - len("完毕") - 1)
        buf.place_cursor(buf.get_iter_at_offset(cursor))
        return True

    def display_name(self):
        name = os.path.basename(self.path) if self.path else UNTITLED
        if self.buffer.get_modified():
            name += " ●"
        return name


# 速查面板的分类内容：(显示, 说明, 插入文本)；插入文本为 None 表示只作提示不插入
REFERENCE = {
    "关键字": [(zh + " / " + en, desc, zh) for zh, en, desc in KEYWORDS],
    "内置函数": [(zh + " / " + en, desc, zh + "(") for zh, en, desc in BUILTINS],
    "标准库模块": [(name, desc, name + ".") for name, desc in STD_MODULES],
    "自带库包": [("用 \"" + name + "\" 引入", desc, "用 \"" + name + "\" 引入")
                 for name, desc in STONES],
    "常见报错": [(key, tip, None) for key, tip in ERROR_HINTS],
}
REF_CATEGORIES = tuple(REFERENCE.keys())


class ReferenceWindow(Gtk.Window):
    """卅语速查 —— 关键字 / 内置函数 / 标准库 / 常见报错，双击即插入编辑器。"""

    def __init__(self, app):
        Gtk.Window.__init__(self, title="卅语速查")
        self.app = app
        self.set_default_size(600, 640)
        self.set_transient_for(app)
        self.set_destroy_with_parent(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for edge in ("top", "bottom", "start", "end"):
            getattr(box, "set_margin_" + edge)(8)

        hint = Gtk.Label(
            label="写代码时随时查，双击条目插入到光标处", xalign=0)
        hint.get_style_context().add_class("dim-label")
        box.pack_start(hint, False, False, 0)

        self.category = Gtk.ComboBoxText()
        for name in REF_CATEGORIES:
            self.category.append_text(name)
        self.category.set_active(0)
        self.category.connect("changed", lambda *_: self.refresh())
        box.pack_start(self.category, False, False, 0)

        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("搜索…（关键字 / 函数 / 报错）")
        self.search.connect("search-changed", lambda *_: self.refresh())
        box.pack_start(self.search, False, False, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", lambda *_: self.insert_selected())
        self.listbox.connect("row-selected", self.on_selected)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(self.listbox)
        box.pack_start(scroller, True, True, 0)

        self.detail = Gtk.Label(label="", xalign=0)
        self.detail.set_line_wrap(True)
        box.pack_start(self.detail, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        insert_btn = Gtk.Button(label="插入到编辑器")
        insert_btn.connect("clicked", lambda *_: self.insert_selected())
        actions.pack_end(insert_btn, False, False, 0)
        box.pack_start(actions, False, False, 0)

        self.add(box)
        self.refresh()
        self.show_all()

    def refresh(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        category = self.category.get_active_text()
        query = self.search.get_text().strip()
        for show, desc, insert in REFERENCE.get(category, []):
            if query and query not in show and query not in desc:
                continue
            row = Gtk.ListBoxRow()
            row.insert_text = insert
            row.detail_text = desc
            label = Gtk.Label(xalign=0)
            label.set_markup("<b>%s</b>  <small>%s</small>" % (
                GLib.markup_escape_text(show),
                GLib.markup_escape_text(desc)))
            for edge in ("top", "bottom", "start", "end"):
                getattr(label, "set_margin_" + edge)(6)
            row.add(label)
            self.listbox.add(row)
        self.listbox.show_all()

    def on_selected(self, _listbox, row):
        self.detail.set_text(row.detail_text if row is not None else "")

    def insert_selected(self):
        if self.category.get_active_text() == "常见报错":
            return
        row = self.listbox.get_selected_row()
        if row is None or not row.insert_text:
            return
        self.app.insert_text(row.insert_text)


class ShanHeStudio(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=APP_TITLE)
        self.set_default_size(1100, 720)
        self.lang = find_language()
        self.tabs = []
        self.ref_win = None
        # v0.3.0 续：字号、最近文件、自动补全
        self.font_size = FONT_SIZES[DEFAULT_FONT_INDEX]
        self.recent = load_recent()
        self.provider = SahoCompletionProvider()

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

    def menu_item(self, label, callback, accel=None):
        """造一个菜单项，可选绑定快捷键。"""
        mi = Gtk.MenuItem(label=label)
        mi.connect("activate", callback)
        if accel:
            key, mods = Gtk.accelerator_parse(accel)
            mi.add_accelerator("activate", self.accel, key, mods,
                               Gtk.AccelFlags.VISIBLE)
        return mi

    def build_menubar(self):
        menu = Gtk.MenuBar()

        file_menu = Gtk.Menu()
        file_menu.append(self.menu_item(
            "新建", lambda *_: self.new_tab(), "<Control>N"))
        file_menu.append(self.menu_item(
            "打开…", lambda *_: self.open_dialog(), "<Control>O"))
        self.recent_item = Gtk.MenuItem(label="最近打开")
        file_menu.append(self.recent_item)
        file_menu.append(self.menu_item(
            "保存", lambda *_: self.save_current(), "<Control>S"))
        file_menu.append(self.menu_item(
            "另存为…", self.save_as_current, "<Control><Shift>S"))
        file_menu.append(self.menu_item("关闭标签", self.close_tab, "<Control>W"))
        file_menu.append(self.menu_item(
            "打包为独立程序…", lambda *_: self.pack_current()))
        file_menu.append(self.menu_item("退出", lambda *_: self.close() and None))
        file_item = Gtk.MenuItem(label="文件")
        file_item.set_submenu(file_menu)
        menu.append(file_item)

        edit_menu = Gtk.Menu()
        edit_menu.append(self.menu_item(
            "撤销", lambda *_: self.edit_action("undo"), "<Control>Z"))
        edit_menu.append(self.menu_item(
            "重做", lambda *_: self.edit_action("redo"), "<Control><Shift>Z"))
        edit_menu.append(Gtk.SeparatorMenuItem())
        for label, action in (("剪切", "cut"), ("复制", "copy"), ("粘贴", "paste")):
            edit_menu.append(self.menu_item(label, lambda _mi, a=action: self.clipboard_action(a)))
        edit_menu.append(self.menu_item("全选", lambda *_: self.select_all(),
                                        "<Control>a"))
        edit_menu.append(Gtk.SeparatorMenuItem())
        edit_menu.append(self.menu_item("查找替换", lambda *_: self.show_search(),
                                        "<Control>f"))
        edit_menu.append(self.menu_item("跳转到行…", lambda *_: self.goto_line(),
                                        "<Control>g"))
        edit_menu.append(self.menu_item("切换注释", lambda *_: self.current_action(
            lambda t: t.toggle_comment()), "<Control>slash"))
        edit_menu.append(self.menu_item("增加缩进", lambda *_: self.current_action(
            lambda t: t.indent_lines())))
        edit_menu.append(self.menu_item("减少缩进", lambda *_: self.current_action(
            lambda t: t.indent_lines(dedent=True))))
        edit_menu.append(Gtk.SeparatorMenuItem())
        edit_menu.append(self.menu_item("放大字号", lambda *_: self.zoom_font(1),
                                        "<Control>plus"))
        edit_menu.append(self.menu_item("缩小字号", lambda *_: self.zoom_font(-1),
                                        "<Control>minus"))
        edit_menu.append(self.menu_item("重置字号", lambda *_: self.zoom_font(0),
                                        "<Control>0"))
        edit_item = Gtk.MenuItem(label="编辑")
        edit_item.set_submenu(edit_menu)
        menu.append(edit_item)

        examples_menu = Gtk.Menu()
        self.append_examples(examples_menu, EXAMPLE_DIR)
        examples_item = Gtk.MenuItem(label="示例")
        examples_item.set_submenu(examples_menu)
        menu.append(examples_item)

        snippet_menu = Gtk.Menu()
        for name, code in SNIPPETS:
            mi = Gtk.MenuItem(label=name)
            mi.connect("activate", lambda _mi, c=code: self.insert_text(c))
            snippet_menu.append(mi)
        snippet_item = Gtk.MenuItem(label="片段")
        snippet_item.set_submenu(snippet_menu)
        menu.append(snippet_item)

        tools_menu = Gtk.Menu()
        for label, cb in (
            ("卅语速查…", lambda *_: self.show_reference()),
            ("代码片段…", lambda *_: self.show_snippets()),
            ("语法检查", lambda *_: self.check_syntax()),
            ("在浏览器中预览（网页）…", lambda *_: self.preview_web()),
            ("打包为独立程序…", lambda *_: self.pack_current()),
        ):
            tools_menu.append(self.menu_item(label, cb))
        tools_menu.append(Gtk.SeparatorMenuItem())
        for label, cb in (
            ("记号流 tokens…", lambda *_: self.show_diagnostics("tokens")),
            ("语法树 ast…", lambda *_: self.show_diagnostics("ast")),
            ("库包列表…", lambda *_: self.show_stones()),
            ("卅语版本…", lambda *_: self.show_diagnostics("版本")),
        ):
            tools_menu.append(self.menu_item(label, cb))
        tools_item = Gtk.MenuItem(label="工具")
        tools_item.set_submenu(tools_menu)
        menu.append(tools_item)

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
        self.refresh_recent_menu()
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
        bar.insert(self.toolbar_button(
            "help-browser", "卅语速查",
            lambda *_: self.show_reference()), -1)
        bar.insert(self.toolbar_button(
            "view-list-symbolic", "代码片段",
            lambda *_: self.show_snippets()), -1)
        bar.insert(self.toolbar_button(
            "package-x-generic", "打包为独立程序",
            lambda *_: self.pack_current()), -1)
        bar.insert(self.toolbar_button(
            "applications-internet", "在浏览器中预览（网页）",
            lambda *_: self.preview_web()), -1)
        bar.insert(self.toolbar_button(
            "system-search-symbolic", "记号流 tokens",
            lambda *_: self.show_diagnostics("tokens")), -1)
        bar.insert(self.toolbar_button(
            "view-grid-symbolic", "库包列表",
            lambda *_: self.show_stones()), -1)
        return bar

    def build_search_bar(self):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", lambda *_: self.search_next())
        top.pack_start(self.search_entry, True, True, 6)
        next_btn = Gtk.Button(label="下一个")
        next_btn.connect("clicked", lambda *_: self.search_next())
        top.pack_start(next_btn, False, False, 0)
        close_btn = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                  Gtk.IconSize.MENU)
        close_btn.connect("clicked", lambda *_: self.search_bar.hide())
        top.pack_start(close_btn, False, False, 4)
        outer.pack_start(top, False, False, 0)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("替换为…")
        self.replace_entry.connect("activate", lambda *_: self.replace_next())
        bottom.pack_start(self.replace_entry, True, True, 6)
        rep_btn = Gtk.Button(label="替换")
        rep_btn.connect("clicked", lambda *_: self.replace_next())
        bottom.pack_start(rep_btn, False, False, 0)
        rep_all_btn = Gtk.Button(label="全部替换")
        rep_all_btn.connect("clicked", lambda *_: self.replace_all())
        bottom.pack_start(rep_all_btn, False, False, 0)
        outer.pack_start(bottom, False, False, 0)

        outer.set_margin_top(2)
        outer.set_margin_bottom(2)
        return outer

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
                self.add_recent(path)
                return
        if self.new_tab(path):
            self.add_recent(path)

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
        if tab and tab.save():
            self.add_recent(tab.path)
            self.flash_status("已保存：" + os.path.basename(tab.path))

    def save_as_current(self, *_):
        tab = self.current()
        if tab and tab.save(as_needed=True):
            self.add_recent(tab.path)

    def open_tutorial(self):
        if os.path.exists(DOC_TUTORIAL):
            Gio.AppInfo.launch_default_for_uri("file://" + DOC_TUTORIAL, None)
        else:
            self.error_dialog("找不到教程", DOC_TUTORIAL)

    def show_about(self, *_):
        dlg = Gtk.AboutDialog()
        dlg.set_transient_for(self)
        dlg.set_program_name(APP_TITLE)
        dlg.set_version("2.1")
        dlg.set_comments("山河Linux 自带的卅语（sahou）集成开发环境。\n"
                         "v2：卅语速查、代码片段库、语法检查、一键打包。\n"
                         "v2.1：自动补全、智能缩进与自动补「完毕」、查找替换、\n"
                         "      网页预览、tokens/ast 诊断、stones 库包管理。\n"
                         "卅语：https://github.com/gwqwy/sahou")
        dlg.set_logo_icon_name("utilities-terminal")
        dlg.run()
        dlg.destroy()

    # ── 运行 / REPL / 格式化 ──

    def run_current(self):
        tab = self.current()
        if not tab or not tab.save():
            return
        # 先做纯解析检查：语法有误时给出中文提示，避免只看到一串报错
        ok, message = self.syntax_check(tab.path)
        if not ok:
            dlg = Gtk.MessageDialog(self, Gtk.DialogFlags.MODAL,
                                    Gtk.MessageType.WARNING, Gtk.ButtonsType.NONE,
                                    "语法有误，是否仍然运行？")
            dlg.format_secondary_text(message + "\n\n" + hint_for(message))
            dlg.add_buttons("取消", Gtk.ResponseType.REJECT,
                            "仍然运行", Gtk.ResponseType.OK)
            resp = dlg.run()
            dlg.destroy()
            if resp != Gtk.ResponseType.OK:
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

    # ── 速查 / 片段 / 打包 / 语法检查（v0.3.0 IDE 增强） ──

    def insert_text(self, text):
        """把一段文本插入当前标签的光标处。"""
        tab = self.current()
        if not tab or not text:
            return
        buf = tab.buffer
        if buf.get_selection_bounds():
            buf.delete_selection(True, True)
        buf.insert_at_cursor(text)
        tab.view.grab_focus()
        self.flash_status("已插入到光标处")

    def show_reference(self):
        """打开「卅语速查」窗口（可常驻，双击条目插入）。"""
        if self.ref_win is None:
            self.ref_win = ReferenceWindow(self)
            self.ref_win.connect("destroy", self.on_ref_destroy)
        self.ref_win.present()

    def on_ref_destroy(self, *_):
        self.ref_win = None

    def show_snippets(self):
        """代码片段选择框：列出内置片段，双击插入。"""
        dlg = Gtk.Dialog(title="代码片段", transient_for=self, modal=True)
        dlg.set_default_size(560, 620)
        dlg.add_button("关闭", Gtk.ResponseType.CLOSE)
        area = dlg.get_content_area()
        area.set_spacing(6)
        for edge in ("top", "bottom", "start", "end"):
            getattr(area, "set_margin_" + edge)(8)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("搜索片段…")
        area.pack_start(search, False, False, 0)

        listbox = Gtk.ListBox()
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(listbox)
        area.pack_start(scroller, True, True, 0)

        def fill():
            for child in listbox.get_children():
                listbox.remove(child)
            query = search.get_text().strip()
            for name, code in SNIPPETS:
                if query and query not in name:
                    continue
                row = Gtk.ListBoxRow()
                row.code = code
                label = Gtk.Label(label=name, xalign=0)
                for edge in ("top", "bottom", "start", "end"):
                    getattr(label, "set_margin_" + edge)(6)
                row.add(label)
                listbox.add(row)
            listbox.show_all()

        def activated(_listbox, row):
            self.insert_text(row.code)
            dlg.response(Gtk.ResponseType.CLOSE)

        search.connect("search-changed", lambda *_: fill())
        listbox.connect("row-activated", activated)
        fill()
        area.show_all()
        dlg.run()
        dlg.destroy()

    def syntax_check(self, path):
        """用 `sahou ast` 做纯解析检查（只分析语法、不执行代码）。

        返回 (是否通过, 报错文本)。解释器不可用时不阻断用户。
        """
        try:
            proc = subprocess.run([SAHOU_BIN, "ast", path],
                                  capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.SubprocessError) as exc:
            return True, str(exc)
        if proc.returncode == 0:
            return True, ""
        return False, (proc.stdout + proc.stderr).strip()

    def check_syntax(self):
        tab = self.current()
        if not tab or not tab.save():
            return
        ok, message = self.syntax_check(tab.path)
        if ok:
            self.flash_status("语法检查通过：" + os.path.basename(tab.path))
            return
        self.error_dialog("语法检查未通过", message + "\n\n" + hint_for(message))

    def pack_current(self):
        """把当前程序打包成独立可执行文件（调用 `sahou 打包`，输出显示在运行区）。"""
        tab = self.current()
        if not tab or not tab.save():
            return
        base = os.path.splitext(os.path.basename(tab.path))[0] + ".exe"
        chosen = self.pack_dialog(base)
        if not chosen:
            return
        if not chosen.endswith(".exe"):
            chosen += ".exe"
        # `sahou 打包` 要在卅语源码仓库内运行（打包时复用解释器源码与 go.mod）
        work = SAHOU_SRC if os.path.isdir(SAHOU_SRC) else os.path.dirname(tab.path)
        self.term_pane.show_all()
        self.paned.set_position(max(240, self.get_allocation().height - 280))
        self.flash_status("正在打包：" + os.path.basename(chosen))
        self.spawn_terminal([SAHOU_BIN, "打包", tab.path, "-o", chosen], work)

    def pack_dialog(self, suggested):
        dlg = Gtk.FileChooserDialog("打包为独立程序", self,
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
        flt.set_name("独立程序 (*.exe)")
        flt.add_pattern("*.exe")
        dlg.add_filter(flt)
        name = dlg.get_filename() if dlg.run() == Gtk.ResponseType.OK else None
        dlg.destroy()
        return name

    # ── v0.3.0 续：自动补全 / 最近文件 / 编辑动作 / 跳转字号 / 查找替换 ──

    def attach_completion(self, view):
        """给编辑器装上卅语自动补全（旧版 GtkSource 不支持时静默跳过）。"""
        try:
            completion = view.get_completion()
            if completion is None:
                return
            completion.add_provider(self.provider)
            completion.set_show_headers(False)
        except Exception:
            pass

    def add_recent(self, path):
        if not path:
            return
        path = os.path.abspath(path)
        self.recent = [p for p in self.recent if p != path]
        self.recent.insert(0, path)
        self.recent = self.recent[:RECENT_MAX]
        save_recent(self.recent)
        self.refresh_recent_menu()

    def open_recent(self, path):
        if os.path.isfile(path):
            self.open_path(path)
        else:
            self.error_dialog("文件已不存在", path)

    def refresh_recent_menu(self):
        """重建「文件 → 最近打开」子菜单。"""
        submenu = Gtk.Menu()
        if not self.recent:
            item = Gtk.MenuItem(label="（暂无）")
            item.set_sensitive(False)
            submenu.append(item)
        else:
            for path in self.recent:
                label = "%s    %s" % (os.path.basename(path),
                                      os.path.dirname(path))
                submenu.append(self.menu_item(
                    label, lambda _mi, p=path: self.open_recent(p)))
            submenu.append(Gtk.SeparatorMenuItem())
            submenu.append(self.menu_item(
                "清除列表", lambda *_: self.clear_recent()))
        submenu.show_all()
        self.recent_item.set_submenu(submenu)
        self.recent_item.set_sensitive(bool(self.recent))

    def clear_recent(self, *_):
        self.recent = []
        save_recent(self.recent)
        self.refresh_recent_menu()
        self.flash_status("已清除最近打开记录")

    def current_action(self, fn):
        """把 fn 作用到当前标签（有标签才执行）。"""
        tab = self.current()
        if tab:
            fn(tab)
            tab.view.grab_focus()

    def edit_action(self, kind):
        def run(tab):
            buf = tab.buffer
            if kind == "undo":
                if buf.can_undo():
                    buf.undo()
            elif buf.can_redo():
                buf.redo()
        self.current_action(run)

    def clipboard_action(self, kind):
        def run(tab):
            cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            if kind == "cut":
                tab.view.cut_clipboard(cb, True)
            elif kind == "copy":
                tab.view.copy_clipboard(cb)
            else:
                tab.view.paste_clipboard(cb, None, True)
        self.current_action(run)

    def select_all(self):
        def run(tab):
            tab.buffer.select_range(tab.buffer.get_start_iter(),
                                    tab.buffer.get_end_iter())
        self.current_action(run)

    def goto_line(self):
        """Ctrl+G：跳转到指定行。"""
        tab = self.current()
        if not tab:
            return
        total = tab.buffer.get_line_count()
        current = tab.buffer.get_iter_at_mark(
            tab.buffer.get_insert()).get_line() + 1
        dlg = Gtk.Dialog(title="跳转到行", transient_for=self, modal=True)
        dlg.add_buttons("取消", Gtk.ResponseType.CANCEL,
                        "跳转", Gtk.ResponseType.OK)
        area = dlg.get_content_area()
        area.set_spacing(6)
        for edge in ("top", "bottom", "start", "end"):
            getattr(area, "set_margin_" + edge)(8)
        area.pack_start(Gtk.Label(label="行号（1 – %d）：" % total, xalign=0),
                        False, False, 0)
        adj = Gtk.Adjustment(value=current, lower=1, upper=max(1, total),
                             step_increment=1)
        spin = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
        area.pack_start(spin, False, False, 0)
        area.show_all()
        if dlg.run() == Gtk.ResponseType.OK:
            line = max(1, min(total, int(spin.get_value())))
            it = tab.buffer.get_iter_at_line(line - 1)
            tab.buffer.place_cursor(it)
            tab.view.scroll_to_iter(it, 0.1, True, 0.0, 0.5)
            tab.view.grab_focus()
        dlg.destroy()

    def zoom_font(self, delta):
        """字号缩放：delta 为 +1 放大、-1 缩小、0 复位。"""
        idx = (FONT_SIZES.index(self.font_size)
               if self.font_size in FONT_SIZES else DEFAULT_FONT_INDEX)
        if delta == 0:
            idx = DEFAULT_FONT_INDEX
        else:
            idx = max(0, min(len(FONT_SIZES) - 1, idx + delta))
        self.font_size = FONT_SIZES[idx]
        for tab in self.tabs:
            tab.apply_font()
        self.flash_status("编辑器字号：%d" % self.font_size)

    def replace_next(self):
        """替换当前命中，并跳到下一个。"""
        tab = self.current()
        if not tab or not self.search_entry.get_text():
            return
        it = tab.buffer.get_iter_at_mark(tab.buffer.get_insert())
        hit = tab.search_context.forward(it)
        if hit:
            start, end, _wrapped = hit
            tab.search_context.replace(start, end, self.replace_entry.get_text(), -1)
        self.search_next()

    def replace_all(self):
        tab = self.current()
        if not tab or not self.search_entry.get_text():
            return
        count = tab.search_context.replace_all(self.replace_entry.get_text(), -1)
        self.flash_status("已替换 %d 处" % count)

    # ── v0.3.0 续：网页预览 / 调试诊断 / 库包管理 ──

    def preview_web(self):
        """一键把当前程序转译成网页 JS（sahou build），并起本地服务在浏览器打开。"""
        tab = self.current()
        if not tab or not tab.save():
            return
        js_path = os.path.splitext(tab.path)[0] + ".js"
        folder = os.path.dirname(tab.path) or os.path.expanduser("~")
        try:
            proc = subprocess.run([SAHOU_BIN, "build", tab.path, "-o", js_path],
                                  capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            self.error_dialog("转译失败", str(exc))
            return
        if proc.returncode != 0:
            msg = (proc.stdout + proc.stderr).strip()
            self.error_dialog("转译失败", msg + "\n\n" + hint_for(msg))
            return
        self.flash_status("已转译为网页：" + os.path.basename(js_path))
        self.term_pane.show_all()
        self.paned.set_position(max(240, self.get_allocation().height - 280))
        self.spawn_terminal([SAHOU_BIN, "serve", folder,
                             "%s:%d" % (SERVE_HOST, SERVE_PORT)], folder)
        url = "http://%s:%d/%s" % (SERVE_HOST, SERVE_PORT,
                                   os.path.basename(tab.path))
        GLib.timeout_add(1200, self.open_url, url)

    def open_url(self, url):
        """在默认浏览器打开地址（失败时提示手动访问）。"""
        try:
            Gio.AppInfo.launch_default_for_uri(url, None)
            self.flash_status("已在浏览器打开：" + url)
        except Exception as exc:
            self.error_dialog("打不开浏览器",
                              "%s\n\n请手动访问：%s" % (exc, url))
        return False

    def show_diagnostics(self, kind):
        """查看 tokens / ast / 版本（把卅语 CLI 输出显示在只读面板里）。"""
        argv = [SAHOU_BIN]
        if kind in ("tokens", "ast"):
            tab = self.current()
            if not tab or not tab.save():
                return
            argv += [kind, tab.path]
        else:
            argv.append(kind)
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            self.error_dialog("执行失败", str(exc))
            return
        text = (proc.stdout + proc.stderr).strip() or "（没有输出）"
        self.show_text_panel("卅语 · " + kind, " ".join(argv), text)

    def show_text_panel(self, title, subtitle, text):
        """只读等宽文本面板，方便查看与复制诊断结果。"""
        dlg = Gtk.Dialog(title=title, transient_for=self, modal=False)
        dlg.set_default_size(760, 560)
        dlg.add_button("关闭", Gtk.ResponseType.CLOSE)
        area = dlg.get_content_area()
        area.set_spacing(6)
        for edge in ("top", "bottom", "start", "end"):
            getattr(area, "set_margin_" + edge)(8)
        head = Gtk.Label(label=subtitle, xalign=0)
        head.get_style_context().add_class("dim-label")
        area.pack_start(head, False, False, 0)
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        view.set_wrap_mode(Gtk.WrapMode.NONE)
        view.modify_font(Pango.FontDescription("%s %d" % (FONT_FAMILY, 11)))
        view.get_buffer().set_text(text)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(view)
        area.pack_start(scroller, True, True, 0)
        area.show_all()
        dlg.run()
        dlg.destroy()

    def show_stones(self):
        """库包管理：列出 exe 自带的 stones 标准库包，双击安装到当前程序目录。"""
        try:
            proc = subprocess.run([SAHOU_BIN, "stones"],
                                  capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as exc:
            self.error_dialog("执行失败", str(exc))
            return
        names = []
        for line in (proc.stdout + proc.stderr).splitlines():
            line = line.strip()
            if not line or line.startswith("exe 自带") or line.startswith("这个 exe"):
                continue
            name = line.split("——")[0].split("[")[0].strip()
            if name:
                names.append(name)
        dlg = Gtk.Dialog(title="库包（stones）", transient_for=self, modal=True)
        dlg.set_default_size(560, 560)
        dlg.add_buttons("刷新", Gtk.ResponseType.APPLY,
                        "关闭", Gtk.ResponseType.CLOSE)
        area = dlg.get_content_area()
        area.set_spacing(6)
        for edge in ("top", "bottom", "start", "end"):
            getattr(area, "set_margin_" + edge)(8)
        hint = Gtk.Label(xalign=0)
        hint.set_text("双击某包，即安装到当前程序所在目录（sahou 装 <包名>）")
        hint.get_style_context().add_class("dim-label")
        area.pack_start(hint, False, False, 0)
        listbox = Gtk.ListBox()
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.add(listbox)
        area.pack_start(scroller, True, True, 0)
        for name in names:
            row = Gtk.ListBoxRow()
            row.code = name
            label = Gtk.Label(label=name, xalign=0)
            for edge in ("top", "bottom", "start", "end"):
                getattr(label, "set_margin_" + edge)(6)
            row.add(label)
            listbox.add(row)
        area.show_all()

        def install(_lb, row):
            if row is not None and getattr(row, "code", None):
                self.install_stone(row.code)
                dlg.response(Gtk.ResponseType.CLOSE)

        listbox.connect("row-activated", install)
        resp = dlg.run()
        dlg.destroy()
        if resp == Gtk.ResponseType.APPLY:
            self.show_stones()

    def install_stone(self, name):
        """把自带库包安装到当前程序目录（在终端里跑 sahou 装 <包名>）。"""
        tab = self.current()
        work = (os.path.dirname(tab.path)
                if tab and tab.path else os.path.expanduser("~"))
        self.term_pane.show_all()
        self.paned.set_position(max(240, self.get_allocation().height - 280))
        self.flash_status("正在安装库包：" + name)
        self.spawn_terminal([SAHOU_BIN, "装", name], work)

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
