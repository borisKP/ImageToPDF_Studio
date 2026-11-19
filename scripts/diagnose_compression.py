# -*- coding: utf-8 -*-
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
"""诊断：不同压缩强度下 PDF 内部图像对象的真实编码 / 色彩空间 / 有效分辨率"""
import os

import pymupdf as fitz
import core

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTDIR = os.path.join(BASE, "_test_images")
OUT = os.path.join(BASE, "_diag_out")

SOF = {0xC0: "BASELINE", 0xC1: "extended-seq", 0xC2: "PROGRESSIVE",
       0xC3: "lossless", 0xC5: "diff-seq", 0xC6: "diff-prog", 0xC7: "diff-lossless"}


def jpeg_kind(data):
    if data[:2] != b"\xff\xd8":
        return ""
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        m = data[i + 1]
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        if m == 0xDA:
            break
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        if m in SOF:
            return SOF[m]
        i += 2 + seg
    return "unknown"


def png_kind(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return ""
    return {0: "Gray", 2: "RGB", 3: "INDEXED/PALETTE", 4: "Gray+Alpha",
            6: "RGBA"}.get(data[25], "?") + f"/{data[24]}bit"


def analyze(path, label):
    doc = fitz.open(path)
    print(f"\n=== {label} | {os.path.getsize(path):,} bytes | {doc.page_count} 页 ===")
    for pno, page in enumerate(doc):
        for img in page.get_images(full=True):
            xref = img[0]
            d = doc.extract_image(xref)
            data, ext = d["image"], d["ext"]
            kind = jpeg_kind(data) if ext in ("jpeg", "jpg") else png_kind(data)
            obj = doc.xref_object(xref)
            fields = [ln.strip() for ln in obj.splitlines()
                      if any(k in ln for k in ("/Filter", "/ColorSpace", "/SMask",
                                               "/BitsPerComponent", "/DecodeParms"))]
            eff = d["width"] / (page.rect.width / 72) if page.rect.width else 0
            print(f"  p{pno+1} 页面 {page.rect.width:.0f}×{page.rect.height:.0f} pt "
                  f"({page.rect.width/72*25.4:.0f}×{page.rect.height/72*25.4:.0f} mm) | "
                  f"图像 {d['width']}×{d['height']} | 有效 {eff:.0f} ppi | "
                  f"{ext} {kind} | {len(data):,} B")
            print("       " + " ".join(fields)[:200])
    doc.close()


def build(label, fn):
    ps = [os.path.join(TESTDIR, n) for n in sorted(os.listdir(TESTDIR))
          if core.is_image(os.path.join(TESTDIR, n))]
    st = core.ConvertSettings()
    fn(st.compress)
    out = os.path.join(OUT, label + ".pdf")
    core.convert(ps, out, st)
    analyze(out, label)


def main():
    os.makedirs(OUT, exist_ok=True)
    build("01_无损", lambda o: setattr(o, "enabled", False))
    build("02_屏幕150", lambda o: core.apply_preset(o, "screen"))
    build("03_极限96", lambda o: core.apply_preset(o, "small"))

    def brutal(o):
        core.apply_preset(o, "small")
        o.target_dpi, o.trigger_dpi, o.quality = 72, 100, 35
    build("04_暴力72_q35", brutal)

    def brutal2(o):
        core.apply_preset(o, "small")
        o.target_dpi, o.trigger_dpi, o.quality = 48, 72, 20
    build("05_暴力48_q20", brutal2)

    print("\n结论指向：PROGRESSIVE / INDEXED 出现即移动端高风险编码")


if __name__ == "__main__":
    main()
