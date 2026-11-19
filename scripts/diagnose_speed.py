# -*- coding: utf-8 -*-
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
"""诊断：PDF 打开/翻页卡顿的可量化原因（解码内存、渲染耗时、线性化）"""
import io
import os
import time

import pymupdf as fitz
from PIL import Image, ImageDraw
import core

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "_speed_out")


def make_big_screenshot(path, w=4000, h=2250):
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w, 160), fill=(37, 99, 235))
    for i in range(28):
        d.rectangle((120, 260 + i * 68, w - 120, 305 + i * 68),
                    fill=(228, 234, 244) if i % 2 else (248, 250, 252))
        d.line((120, 305 + i * 68, w - 120, 305 + i * 68), fill=(120, 130, 145))
    im.save(path, format="PNG", dpi=(150, 150))


def bench(path, label):
    doc = fitz.open(path)
    linear = getattr(doc, "is_linear", None)
    try:
        linear = doc.is_linear
    except Exception:
        pass
    print(f"\n=== {label} | {os.path.getsize(path):,} B | linear={linear} ===")
    for pno, page in enumerate(doc):
        for img in page.get_images(full=True):
            d = doc.extract_image(img[0])
            raw_mb = d["width"] * d["height"] * 3 / 1024 / 1024
            obj = doc.xref_object(img[0])
            filt = "/FlateDecode" if "/FlateDecode" in obj else (
                "/DCTDecode" if "/DCTDecode" in obj else "?")
            # 渲染 3 次取平均，模拟连续翻页
            t0 = time.perf_counter()
            for _ in range(3):
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
                _ = pix.samples[:64]
            ms = (time.perf_counter() - t0) / 3 * 1000
            print(f"  p{pno+1} 页面 {page.rect.width:.0f}×{page.rect.height:.0f} pt | "
                  f"图 {d['width']}×{d['height']} ({d['ext']}) | "
                  f"流 {len(d['image']):,} B | 解压后 {raw_mb:.1f} MB | {filt} | "
                  f"渲染 {ms:.1f} ms")
    doc.close()


def build_pdf(img_path, out_path, mode, linear=False, encrypt=False):
    with Image.open(img_path) as im:
        w, h = im.size
        if mode == "jpeg":
            buf = io.BytesIO()
            im.convert("RGB").save(buf, format="JPEG", quality=85,
                                   optimize=True, progressive=False, subsampling=0)
            stream = buf.getvalue()
        else:
            buf = io.BytesIO()
            im.save(buf, format="PNG", optimize=True)
            stream = buf.getvalue()
    doc = fitz.open()
    pw, ph = w / 150 * 72, h / 150 * 72
    page = doc.new_page(width=pw, height=ph)
    page.insert_image(fitz.Rect(0, 0, pw, ph), stream=stream)
    kw = dict(garbage=4, deflate=True, clean=True)
    if linear:
        kw["linear"] = True
    if encrypt:
        kw.update(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="abc",
                  owner_pw="owner", permissions=-1)
    doc.save(out_path, **kw)
    doc.close()
    return out_path


def main():
    os.makedirs(OUT, exist_ok=True)
    src = os.path.join(OUT, "big_screenshot.png")
    make_big_screenshot(src)
    print("源图 4000×2250 PNG:", os.path.getsize(src), "B")

    a = build_pdf(src, os.path.join(OUT, "A_PNG_Flate.pdf"), "png")
    bench(a, "A · PNG / FlateDecode（体积可能更小，但解码成原始像素）")
    b = build_pdf(src, os.path.join(OUT, "B_JPEG_baseline.pdf"), "jpeg")
    bench(b, "B · baseline JPEG / DCTDecode")

    # 线性化兼容性
    for lin, enc in ((True, False), (True, True)):
        p = os.path.join(OUT, f"C_linear{lin}_enc{enc}.pdf")
        try:
            build_pdf(src, p, "jpeg", linear=lin, encrypt=enc)
            d = fitz.open(p)
            print(f"\n[兼容性] linear={lin} encrypt={enc} -> OK, is_linear={d.is_linear}")
            d.close()
        except Exception as e:
            print(f"\n[兼容性] linear={lin} encrypt={enc} -> FAIL: {e}")

    # core 现有各档
    ps = [os.path.join(BASE, "_test_images", n)
          for n in sorted(os.listdir(os.path.join(BASE, "_test_images")))
          if core.is_image(os.path.join(BASE, "_test_images", n))]
    for label, fn in (("core 无损", lambda o: setattr(o, "enabled", False)),
                      ("core 屏幕150", lambda o: core.apply_preset(o, "screen"))):
        st = core.ConvertSettings()
        fn(st.compress)
        p = os.path.join(OUT, label + ".pdf")
        core.convert(ps, p, st)
        bench(p, label)


if __name__ == "__main__":
    main()
