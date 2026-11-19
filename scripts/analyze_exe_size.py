# -*- coding: utf-8 -*-
"""解析 PyInstaller onefile EXE 的 CArchive，列出各组件压缩后体积。

用法：python scripts/analyze_exe_size.py [dist/ImageToPDF_Studio.exe]
不需要安装 PyInstaller，直接从 EXE 尾部 cookie 解析。
"""
import os
import struct
import sys

MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"


def parse(path: str):
    with open(path, "rb") as f:
        data = f.read()
    idx = data.rfind(MAGIC)
    if idx < 0:
        raise RuntimeError("不是 PyInstaller onefile EXE（未找到 CArchive cookie）")
    _magic, pkg_len, toc_off, toc_len, _pyvers, _pylib = struct.unpack(
        "!8sIIII64s", data[idx:idx + 88])
    base = len(data) - pkg_len
    toc = data[base + toc_off: base + toc_off + toc_len]
    rows, pos = [], 0
    while pos + 18 <= len(toc):
        elen, _off, dlen, ulen, _cf, typ = struct.unpack("!iIIIBB", toc[pos:pos + 18])
        if elen < 18:
            break
        name = toc[pos + 18:pos + elen].rstrip(b"\0").decode("utf-8", "replace")
        rows.append((int(dlen), int(ulen), chr(typ) if typ else "?", name))
        pos += elen
    return rows, len(data)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "dist", "ImageToPDF_Studio.exe")
    rows, total = parse(path)
    rows.sort(reverse=True)
    print(f"EXE: {path}")
    print(f"文件大小: {total / 1048576:.1f} MB | 条目: {len(rows)}\n")
    print(f"{'压缩MB':>8} {'原始MB':>8}  条目")
    for dlen, ulen, typ, name in rows[:40]:
        print(f"{dlen / 1048576:8.2f} {ulen / 1048576:8.2f}  {name[:66]:66s} {typ}")
    groups = {}
    for dlen, _ulen, _typ, name in rows:
        prefix = name.split("\\")[0] if "\\" in name else "(root)"
        groups[prefix] = groups.get(prefix, 0) + dlen
    print("\n按目录汇总:")
    for name, size in sorted(groups.items(), key=lambda x: -x[1]):
        print(f"  {size / 1048576:7.2f} MB  {name}")
    print("\n压缩累计:", round(sum(r[0] for r in rows) / 1048576, 1), "MB",
          "| 原始累计:", round(sum(r[1] for r in rows) / 1048576, 1), "MB")


if __name__ == "__main__":
    main()
