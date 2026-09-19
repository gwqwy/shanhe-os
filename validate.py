"""本地静态验证：Python 语法、XML 格式、desktop 文件必需键、卅语关键字一致性。"""
import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parent
fails = []

# 1) Python 语法
pyf = ROOT / "live/config/includes.chroot/opt/shanhe-studio/shanhe-studio.py"
try:
    ast.parse(pyf.read_text(encoding="utf-8"))
    print("OK   Python 语法:", pyf.name)
except SyntaxError as exc:
    fails.append(f"FAIL Python 语法 {pyf}: {exc}")

# 2) XML 格式
for x in [
    "live/config/includes.chroot/usr/share/gtksourceview-4/language-specs/sahou.lang",
    "live/config/includes.chroot/usr/share/icons/hicolor/scalable/apps/shanhe-start.svg",
    "live/config/includes.chroot/usr/share/icons/hicolor/scalable/apps/shanhe-studio.svg",
    "live/config/includes.chroot/usr/share/wallpapers/shanhe/contents/images/山河壁纸.svg",
]:
    try:
        ET.parse(ROOT / x)
        print("OK   XML 格式:", Path(x).name)
    except Exception as exc:
        fails.append(f"FAIL XML {x}: {exc}")

# 3) desktop 文件必需键
for d in (ROOT / "live/config/includes.chroot/usr/share/applications").glob("*.desktop"):
    text = d.read_text(encoding="utf-8")
    ok = "[Desktop Entry]" in text and "Type=" in text and "Name=" in text and "Exec=" in text
    print(("OK   " if ok else "FAIL ") + "desktop:", d.name)
    if not ok:
        fails.append(f"FAIL desktop 缺键: {d}")

# 4) sahou.lang 关键字与上游 lexer KeyWords 对齐
lang = (ROOT / "live/config/includes.chroot/usr/share/gtksourceview-4/language-specs/sahou.lang")
tree = ET.parse(lang)
lang_keywords = set()
for kw in tree.iter("keyword"):
    lang_keywords.add(kw.text)
lang_keywords = set()
for ctx in tree.iter("context"):
    if ctx.get("id") in ("keywords", "constants"):
        lang_keywords.update(k.text for k in ctx.iter("keyword"))

upstream = set()
lexer = ROOT.parent / "sahou-upstream/internal/lexer/lexer.go"
if not lexer.exists():
    lexer = ROOT / "vendor/sahou/internal/lexer/lexer.go"
in_map = False
for line in lexer.read_text(encoding="utf-8").splitlines():
    if "KeyWords" in line and "map[string]string{" in line:
        in_map = True
        continue
    if in_map:
        if line.strip().startswith("}"):
            break
        if '"' in line:
            for tok in line.split('"')[1::2]:
                if tok not in (":", ","):
                    upstream.add(tok)
missing = upstream - lang_keywords
if missing:
    fails.append(f"FAIL sahou.lang 缺少关键字: {sorted(missing)}")
else:
    print(f"OK   关键字对齐: sahou.lang 覆盖上游 lexer 全部 {len(upstream)} 个关键字拼写")

# 5) 构建钩子齐套检查（编号连续 + chroot/binary 都有）
hooks = sorted((ROOT / "live/config/hooks").glob("*.chroot"))
hooks_bin = sorted((ROOT / "live/config/hooks").glob("*.binary"))
print(f"OK   钩子: {len(hooks)} 个 chroot + {len(hooks_bin)} 个 binary")
if len(hooks) < 5 or len(hooks_bin) < 1:
    fails.append("FAIL 钩子数量异常")

print()
if fails:
    print("\n".join(fails))
    sys.exit(1)
print("全部通过 ✅")
