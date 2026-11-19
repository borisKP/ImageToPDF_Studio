# -*- coding: utf-8 -*-
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
"""诊断：十几 MB 原图 vs 网站展示副本 vs 各档 PDF「随便看看」成本"""
import io
import os
import time

import pymupdf as fitz
from PIL import Image
import core

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "_casual_out")
SRC = os.path.join(OUT, "原图_十几MB.jpg")


def make_source():
    os.makedirs(OUT, exist_ok=True)
    im = Image.effect_noise((4000, 3000), 45).convert("RGB")
    im.save(SRC, format="JPEG", quality=95, subsampling=0)
    return im


def website_copy(im):
    """模拟图片网站实际下发给浏览器的展示副本"""
    t = im.copy()
    t.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    b = io.BytesIO()
    t.save(b, format="WEBP", quality=75, method=6)
    return t.size, len(b.getvalue())


def bench(path, label):
    doc = fitz.open(path)
    pg = doc[0]
    d = doc.extract_image(pg.get_images(full=True)[0][0])
    w, h = d["width"], d["height"]
    mem = w * h * 3 / 1024 / 1024
    obj = doc.xref_object(pg.get_images(full=True)[0][0])
    filt = "/FlateDecode" if "/FlateDecode" in obj else "/DCTDecode"
    t0 = time.perf_counter()
    for _ in range(3):
        pix = pg.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
        _ = pix.samples[:64]
    ms = (time.perf_counter() - t0) / 3 * 1000
    print(f"  {label:26s} {os.path.getsize(path):>10,} B | 图 {w}×{h} | "
          f"内存 {mem:5.1f} MB | {filt:14s} | 渲染 {ms:6.1f} ms")
    doc.close()


def settings(label, ppi, trig, q, edge_mm, mp, reading):
    st = core.ConvertSettings()
    st.compress.enabled = True
    st.compress.target_dpi = ppi
    st.compress.trigger_dpi = trig
    st.compress.quality = q
    st.compress.reading_mode = reading
    st.compress.max_megapixels = mp
    st.max_long_edge_mm = edge_mm
    return st


def main():
    im = make_source()
    print("=== 源图（模拟图片网站下载的『原图』）===")
    print(f"  {os.path.getsize(SRC):,} B  4000×3000 JPEG q95")
    size, n = website_copy(im)
    print(f"  网站实际下发的展示副本：{size[0]}×{size[1]} WebP q75 = {n:,} B"
          f"  → 是原图的 {n / os.path.getsize(SRC) * 100:.1f}%")

    print("\n=== 同一张原图做成 PDF ===")
    cases = [
        ("A 无损（原始嵌入）", None),
        ("B 屏幕150（默认）", settings("b", 150, 225, 75, 0, 0, False)),
        ("C 极限96（现有预设）", settings("c", 96, 144, 58, 0, 0, False)),
        ("D 移动端一键优化", settings("d", 120, 180, 70, 297, 4.0, True)),
        ("E 随便看看（本轮新增）", settings("e", 96, 150, 55, 210, 1.0, True)),
    ]
    for label, st in cases:
        p = os.path.join(OUT, label.split()[0] + ".pdf")
        if st is None:
            st = core.ConvertSettings()
        core.convert([SRC], p, st)
        bench(p, label)


if __name__ == "__main__":
    main()
