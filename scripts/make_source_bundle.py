# -*- coding: utf-8 -*-
"""生成源码交付物：整合版单文件 + 完整工程 zip。

版本号唯一来源 = src/app.py 中的 APP_VER。
每次运行会：
  1. 把仓库内文档/依赖清单里的版本号、页脚日期同步到当前版本；
  2. 把 core + archive + app 三个模块内联成可直接运行的整合版单文件；
  3. 打包为 ImageToPDF_源码_v<版本>.zip（保持 GitHub 仓库目录结构）；
  4. 若版本演进表缺少当前版本，打印补写提醒。

build.bat 在 PyInstaller 打包 EXE 成功后会自动调用本脚本，
保证「版本更新 → EXE 与源码交付物同步」不遗漏。
"""
import datetime
import os
import re
import shutil
import zipfile
import py_compile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELIV = os.path.join(REPO, "源码交付")
os.makedirs(DELIV, exist_ok=True)

MERGED_NAME = "ImageToPDF_整合版源码.py"
VERSION_RE = r"ImageToPDF Studio v\d+(?:\.\d+)+"

FILES = [
    # 仓库根
    ".gitignore", "LICENSE", "README.md", "CHANGELOG.md", "CONTRIBUTING.md",
    "requirements.txt", "build.bat", "ImageToPDF_Studio.spec",
    ".github/workflows/build.yml",
    # 源码
    "src/app.py", "src/core.py", "src/archive.py",
    # 测试
    "tests/test_core.py", "tests/test_gui.py", "tests/test_archive.py",
    # 文档
    "docs/使用说明.html", "docs/源码说明.html",
    # 资源
    "assets/app.ico", "assets/app.png",
    # 工具脚本
    "scripts/make_icon.py", "scripts/make_source_bundle.py",
    "scripts/diagnose_compression.py", "scripts/diagnose_speed.py",
    "scripts/diagnose_webp.py", "scripts/diagnose_casual.py",
    "scripts/analyze_exe_size.py",
    # 生成物（整合版单文件，放在 zip 根便于直接运行）
    MERGED_NAME,
]


def read(rel):
    with open(os.path.join(REPO, rel), "r", encoding="utf-8") as f:
        return f.read()


def current_version():
    m = re.search(r'^APP_VER\s*=\s*"([^"]+)"', read("src/app.py"), flags=re.M)
    if not m:
        raise RuntimeError('src/app.py 中未找到 APP_VER = "x.y"')
    return m.group(1)


def sync_text_files(ver):
    """同步版本号与页脚日期；CHANGELOG / build.bat 不参与（前者是历史，后者正在执行）。"""
    today = datetime.date.today().isoformat()
    targets = [
        "requirements.txt", "README.md",
        "docs/源码说明.html", "docs/使用说明.html", "dist/使用说明.html",
    ]
    changed = []
    for rel in targets:
        p = os.path.join(REPO, rel)
        if not os.path.exists(p):
            continue
        with open(p, "r", encoding="utf-8") as f:
            old = f.read()
        new = re.sub(VERSION_RE, f"ImageToPDF Studio v{ver}", old)
        version_changed = (new != old)
        if version_changed:
            new = re.sub(r"(<footer>[^<]*?)\d{4}-\d{2}-\d{2}", rf"\g<1>{today}", new)
        if new != old:
            with open(p, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            changed.append(rel)
    # dist 内的使用者说明始终与 docs 同源
    src = os.path.join(REPO, "docs", "使用说明.html")
    dst = os.path.join(REPO, "dist", "使用说明.html")
    if os.path.isdir(os.path.dirname(dst)):
        shutil.copyfile(src, dst)
    return changed


def strip_header(s):
    s = re.sub(r"^# -\*- coding:.*?\n", "", s, count=1, flags=re.M)
    s = s.lstrip("\n")
    if s.startswith('"""'):
        end = s.find('"""', 3)
        s = s[end + 3:].lstrip("\n")
    s = re.sub(r"^from __future__ import annotations\s*\n", "", s, flags=re.M)
    return s


def build_merged(ver):
    sections = [
        ("转换引擎（原 src/core.py）", strip_header(read("src/core.py"))),
        ("压缩包导入（原 src/archive.py）", strip_header(read("src/archive.py"))),
        ("图形界面与入口（原 src/app.py）", strip_header(read("src/app.py"))),
    ]
    body = sections[2][1]
    body = re.sub(r"^import core\s*$", "# core 模块已内联到本文件上方",
                  body, flags=re.M)
    body = re.sub(r"^import archive\s*$", "# archive 模块已内联到本文件上方",
                  body, flags=re.M)
    body = re.sub(r"\bcore\.", "", body)
    body = re.sub(r"\barchive\.", "", body)
    sections[2] = (sections[2][0], body)

    header = (
        '# -*- coding: utf-8 -*-\n'
        f'"""ImageToPDF Studio v{ver} · 整合版单文件源码\n\n'
        '把 src/core.py、src/archive.py、src/app.py 合并为一个可直接运行的脚本。\n'
        '运行：python ImageToPDF_整合版源码.py\n'
        '自检：python ImageToPDF_整合版源码.py --selftest\n'
        '依赖：见 requirements.txt（PySide6 / Pillow / PyMuPDF / py7zr / pyzipper）。\n'
        '"""\n'
        'from __future__ import annotations\n\n'
    )
    chunks = [header]
    for i, (title, text) in enumerate(sections, 1):
        chunks.append("# " + "=" * 66 + "\n")
        chunks.append(f"# 第 {i} 部分：{title}\n")
        chunks.append("# " + "=" * 66 + "\n\n")
        chunks.append(text.rstrip() + "\n\n\n")
    merged = "".join(chunks).rstrip() + "\n"

    path = os.path.join(DELIV, MERGED_NAME)
    with open(path, "w", encoding="utf-8") as f:
        f.write(merged)
    py_compile.compile(path, doraise=True)
    print(f"整合版: {MERGED_NAME} ({os.path.getsize(path):,} B) | 3 模块内联 | 语法检查通过")
    return path


def build_zip(ver, merged_path):
    zip_name = f"ImageToPDF_源码_v{ver}.zip"
    path = os.path.join(DELIV, zip_name)
    missing = [n for n in FILES
               if n != MERGED_NAME and not os.path.exists(os.path.join(REPO, n))]
    if missing:
        raise RuntimeError("以下文件缺失，无法打包源码：" + ", ".join(missing))
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in FILES:
            src = merged_path if rel == MERGED_NAME else os.path.join(REPO, rel)
            z.write(src, arcname=rel)
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        assert bad is None, f"zip 损坏: {bad}"
    print(f"源码包: {zip_name} ({os.path.getsize(path):,} B) | {len(FILES)} 个文件 | 完整性校验通过")
    return path


def main():
    ver = current_version()
    print(f"当前版本: v{ver}（来自 src/app.py 的 APP_VER）")
    changed = sync_text_files(ver)
    print("已同步版本号/日期:", ", ".join(changed) if changed else "无（已是最新）")
    merged = build_merged(ver)
    build_zip(ver, merged)
    shutil.copyfile(os.path.join(REPO, "docs", "源码说明.html"),
                    os.path.join(DELIV, "源码说明.html"))
    if f"<td>{ver}</td>" not in read("docs/源码说明.html"):
        print(f"提醒：docs/源码说明.html 的「版本演进」表尚无 v{ver}，请补一行本次更新内容。")
    print("交付目录:", DELIV)


if __name__ == "__main__":
    main()
