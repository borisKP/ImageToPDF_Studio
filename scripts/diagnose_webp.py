# -*- coding: utf-8 -*-
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
"""验证：WebP 能否直接嵌入 PDF；「先转 WebP 再做 PDF」的体积与画质代价"""
import io
import os

import pymupdf as fitz
from PIL import Image, ImageChops, ImageStat
import core

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "_speed_out", "big_screenshot.png")
OUT = os.path.join(BASE, "_webp_out")


def enc(im, fmt, **kw):
    b = io.BytesIO()
    im.save(b, format=fmt, **kw)
    return b.getvalue()


def mae(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def make_pdf(stream, name, w=4000, h=2250, dpi=150):
    doc = fitz.open()
    pw, ph = w / dpi * 72, h / dpi * 72
    pg = doc.new_page(width=pw, height=ph)
    pg.insert_image(fitz.Rect(0, 0, pw, ph), stream=stream)
    p = os.path.join(OUT, name + ".pdf")
    doc.save(p, garbage=4, deflate=True, clean=True)
    doc.close()
    return p


def main():
    os.makedirs(OUT, exist_ok=True)
    with Image.open(SRC) as im0:
        im = im0.convert("RGB")
        im.load()

    png = enc(im, "PNG", optimize=True)
    webp80 = enc(im, "WEBP", quality=80, method=6)
    webp40 = enc(im, "WEBP", quality=40, method=6)
    jpg80 = enc(im, "JPEG", quality=80, optimize=True, progressive=False, subsampling=1)

    print("=== 源图 4000×2250，各格式自身体积 ===")
    for n, b in (("PNG", png), ("WebP q80", webp80), ("WebP q40", webp40),
                 ("baseline JPEG q80", jpg80)):
        print(f"  {n:22s} {len(b):>9,} B")

    # ---- 硬证据：直接把 WebP 字节塞进 PDF
    print("\n=== 直接嵌入 WebP 字节流 ===")
    doc = fitz.open()
    pg = doc.new_page(width=400, height=225)
    try:
        pg.insert_image(fitz.Rect(0, 0, 400, 225), stream=webp80)
        doc.save(os.path.join(OUT, "RAW_WEBP.pdf"))
        print("  结果：竟然成功（需检查产物）")
    except Exception as e:
        print(f"  结果：失败 -> {type(e).__name__}: {e}")
    doc.close()

    # ---- 二次有损
    w80 = Image.open(io.BytesIO(webp80)).convert("RGB")
    w40 = Image.open(io.BytesIO(webp40)).convert("RGB")
    jpg_from_webp80 = enc(w80, "JPEG", quality=80, optimize=True,
                          progressive=False, subsampling=1)
    jpg_from_webp40 = enc(w40, "JPEG", quality=80, optimize=True,
                          progressive=False, subsampling=1)

    print("\n=== 转成 PDF 时实际可用的编码（PDF 只认 DCT/Flate） ===")
    print(f"  {'路径':38s} {'最终字节':>10s} {'相对原图 MAE':>12s}")
    for label, stream, decoded in (
        ("原图 → PNG(Flate)", png, im),
        ("原图 → JPEG q80(DCT)", jpg80, Image.open(io.BytesIO(jpg80)).convert("RGB")),
        ("原图 → WebP80 → JPEG q80", jpg_from_webp80, w80),
        ("原图 → WebP40 → JPEG q80", jpg_from_webp40, w40),
    ):
        print(f"  {label:38s} {len(stream):>10,} {mae(im, decoded):>12.3f}")

    print("\n=== 生成 PDF 后的文件体积（同一页面尺寸） ===")
    paths = [
        ("A_PNG_Flate", png),
        ("B_JPEG_q80", jpg80),
        ("C_WebP80_then_JPEG", jpg_from_webp80),
        ("D_WebP40_then_JPEG", jpg_from_webp40),
    ]
    for name, stream in paths:
        p = make_pdf(stream, name)
        d = fitz.open(p)
        filt = "/FlateDecode" if "/FlateDecode" in d.xref_object(
            d[0].get_images(full=True)[0][0]) else "/DCTDecode"
        print(f"  {name:24s} {os.path.getsize(p):>9,} B   {filt}")
        d.close()

    # v1.4 阅读优先作参考
    st = core.ConvertSettings()
    st.compress.reading_mode = True
    st.compress.max_megapixels = 4.0
    st.compress.target_dpi = 120
    st.compress.trigger_dpi = 180
    st.compress.quality = 70
    st.max_long_edge_mm = 297
    r = core.convert([SRC], os.path.join(OUT, "E_v14_阅读优先.pdf"), st)
    print(f"  {'E_v14_阅读优先':24s} {r['pdf_bytes']:>9,} B   /DCTDecode")


if __name__ == "__main__":
    main()
