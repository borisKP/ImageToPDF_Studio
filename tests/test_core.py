# -*- coding: utf-8 -*-
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
"""核心引擎自测：页面尺寸 / 页数 / 压缩率 / 纸张模式"""
import os
import io
import sys
import shutil

from PIL import Image, ImageDraw
import pymupdf as fitz
import core

BASE = os.path.dirname(os.path.abspath(__file__))
TESTDIR = os.path.join(BASE, "_test_images")
OUTDIR = os.path.join(BASE, "_test_out")


def make_images():
    if os.path.isdir(TESTDIR):
        shutil.rmtree(TESTDIR)
    os.makedirs(TESTDIR)
    # 1. 横图 3000x2000 @300dpi（渐变照片）
    g = Image.linear_gradient("L").resize((3000, 2000))
    im = Image.merge("RGB", (g, g.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
                             g.transpose(Image.Transpose.FLIP_TOP_BOTTOM)))
    d = ImageDraw.Draw(im)
    for i in range(0, 3000, 150):
        d.line((i, 0, i, 2000), fill=(200, 40, 40), width=2)
    im.save(os.path.join(TESTDIR, "01_横图_3000x2000_300dpi.jpg"),
            quality=92, dpi=(300, 300))
    # 2. 竖图 1200x1800 @150dpi PNG
    im2 = Image.new("RGB", (1200, 1800), (245, 247, 250))
    d2 = ImageDraw.Draw(im2)
    for y in range(0, 1800, 60):
        d2.rectangle((80, y, 1120, y + 30), fill=(30, 90, 180))
    im2.save(os.path.join(TESTDIR, "02_竖图_1200x1800_150dpi.png"), dpi=(150, 150))
    # 3. 截图 1600x900 @96dpi（大色块 + 文字线条）
    im3 = Image.new("RGB", (1600, 900), (255, 255, 255))
    d3 = ImageDraw.Draw(im3)
    d3.rectangle((0, 0, 1600, 80), fill=(37, 99, 235))
    for i in range(12):
        d3.rectangle((60, 130 + i * 58, 1540, 170 + i * 58),
                     fill=(228, 234, 244) if i % 2 else (248, 250, 252))
        d3.line((60, 170 + i * 58, 1540, 170 + i * 58), fill=(120, 130, 145), width=1)
    im3.save(os.path.join(TESTDIR, "10_截图_1600x900_96dpi.png"), dpi=(96, 96))


def paths():
    return [os.path.join(TESTDIR, n) for n in sorted(os.listdir(TESTDIR))]


def inspect(pdf_path):
    doc = fitz.open(pdf_path)
    sizes = [(round(p.rect.width, 1), round(p.rect.height, 1)) for p in doc]
    toc = doc.get_toc()
    n = doc.page_count
    doc.close()
    return n, sizes, toc


def run():
    make_images()
    if os.path.isdir(OUTDIR):
        shutil.rmtree(OUTDIR)
    os.makedirs(OUTDIR)
    ps = paths()
    print("测试图片：", [os.path.basename(p) for p in ps])
    print("源大小：", [os.path.getsize(p) for p in ps])

    # ---- 无损
    st = core.ConvertSettings()
    r = core.convert(ps, os.path.join(OUTDIR, "无损.pdf"), st)
    print("\n[无损]", r["pages"], "页", r["pdf_bytes"], "bytes")
    print("  页面尺寸:", inspect(r["output"])[1])
    print("  书签:", inspect(r["output"])[2])

    # ---- 压缩（屏幕 150ppi）
    st2 = core.ConvertSettings()
    core.apply_preset(st2.compress, "screen")
    r2 = core.convert(ps, os.path.join(OUTDIR, "压缩150.pdf"), st2)
    print("\n[压缩 150ppi]", r2["pages"], "页", r2["pdf_bytes"], "bytes",
          f"({r2['ratio']*100:.0f}% of source)")
    print("  页面尺寸:", inspect(r2["output"])[1])
    print("  错误:", r2["errors"])

    # ---- 统一 A4
    st3 = core.ConvertSettings()
    st3.page_mode = "paper"
    st3.paper_name = "A4"
    st3.margin_mm = 10
    r3 = core.convert(ps, os.path.join(OUTDIR, "统一A4.pdf"), st3)
    print("\n[统一A4]", r3["pages"], "页", inspect(r3["output"])[1])

    # ---- 固定 DPI 300 + 最长边限制
    st4 = core.ConvertSettings()
    st4.dpi_source = "fixed"
    st4.fixed_dpi = 300
    st4.max_long_edge_mm = 297
    r4 = core.convert(ps, os.path.join(OUTDIR, "固定300.pdf"), st4)
    print("\n[固定300dpi+最长边297mm]", r4["pages"], "页", inspect(r4["output"])[1])

    # ---- 密码保护
    st5 = core.ConvertSettings()
    st5.security = core.SecurityOptions(enabled=True, user_pw="abc123",
                                        owner_pw="owner", method="aes256",
                                        allow_copy=False, allow_modify=False)
    out5 = os.path.join(OUTDIR, "加密.pdf")
    r5 = core.convert(ps, out5, st5)
    enc = fitz.open(out5)
    print("\n[加密]", "needs_pass=", enc.needs_pass,
          "wrong=", enc.authenticate("bad"),
          "user=", enc.authenticate("abc123"),
          "pages=", enc.page_count, "flag=", r5["encrypted"], r5["encryption"])
    assert enc.needs_pass, "PDF 未加密"
    assert enc.authenticate("bad") == 0, "错误口令竟然通过"
    assert enc.authenticate("abc123") > 0, "正确口令未通过"
    assert enc.page_count == 3
    assert r5["encrypted"] and r5["encryption"] == "AES-256"
    enc.close()
    plain = fitz.open(os.path.join(OUTDIR, "无损.pdf"))
    assert not plain.needs_pass, "未启用密码的 PDF 被误加密"
    plain.close()

    # ---- 移动端兼容回归
    with Image.open(ps[0]) as photo:
        photo.thumbnail((800, 600))
        assert not core.looks_graphic(photo), "照片被误判为图形类"
    assert core.looks_graphic(Image.new("RGB", (800, 600), (255, 255, 255))), \
        "纯色图形未被识别"
    opts = core.CompressOptions(enabled=True, target_dpi=96, trigger_dpi=100,
                                quality=35, graphics_mode=False)
    with Image.open(ps[0]) as photo:
        photo.load()
        packed = core.compress_stream(photo, 720, 480, opts, 10 ** 9)
        assert core.jpeg_sof(packed) == 0xC0, "生成了渐进式 JPEG（移动端高风险）"
    opts2 = core.CompressOptions(enabled=True, target_dpi=48, trigger_dpi=10,
                                 quality=60, graphics_mode=False)
    with Image.open(ps[0]) as photo:
        photo.load()
        packed2 = core.compress_stream(photo, 720, 480, opts2, 10 ** 9)
        w2 = Image.open(io.BytesIO(packed2)).width
        assert 700 <= w2 <= 740, f"ppi 下限未生效: {w2}px"
    print("\n[移动端兼容] baseline JPEG / 照片不量化 / ppi 下限 72 均通过")

    # ---- 阅读流畅优先：先转格式再做 PDF
    st_r = core.ConvertSettings()
    st_r.compress.reading_mode = True
    st_r.compress.max_megapixels = 1.0
    out_r = os.path.join(OUTDIR, "阅读优先.pdf")
    rr = core.convert(ps, out_r, st_r)
    rd = fitz.open(out_r)
    objs, maxpx = [], 0
    for pg in rd:
        for im in pg.get_images(full=True):
            objs.append(rd.xref_object(im[0]))
            d = rd.extract_image(im[0])
            maxpx = max(maxpx, d["width"] * d["height"])
    rd.close()
    joined = " ".join(objs)
    assert "/DCTDecode" in joined and "/FlateDecode" not in joined, \
        "阅读优先仍存在 Flate 图像对象"
    assert maxpx <= 1_050_000, f"单页像素上限未生效: {maxpx}"
    assert rr["preprocessed"]
    print("[阅读优先] 全部图像 DCTDecode / 单页 ≤1 MP 通过")

    # ---- 随便看看一键档参数（96 ppi / q55 / 长边210mm / ≤1MP）
    st_c = core.ConvertSettings()
    st_c.compress.enabled = True
    st_c.compress.target_dpi = 96
    st_c.compress.trigger_dpi = 150
    st_c.compress.quality = 55
    st_c.compress.reading_mode = True
    st_c.compress.max_megapixels = 1.0
    st_c.max_long_edge_mm = 210
    out_c = os.path.join(OUTDIR, "随便看看.pdf")
    rc = core.convert(ps, out_c, st_c)
    dc = fitz.open(out_c)
    objs, px = [], 0
    for pg in dc:
        for im in pg.get_images(full=True):
            objs.append(dc.xref_object(im[0]))
            d = dc.extract_image(im[0])
            px = max(px, d["width"] * d["height"])
    dc.close()
    assert "/FlateDecode" not in " ".join(objs)
    assert px <= 1_050_000
    print("[随便看看] 全部 DCTDecode / 单页 ≤1 MP / 体积", rc["pdf_bytes"], "B")

    # 断言
    n1, s1, _ = inspect(os.path.join(OUTDIR, "无损.pdf"))
    n2, s2, _ = inspect(os.path.join(OUTDIR, "压缩150.pdf"))
    assert n1 == 3 == n2, "页数错误"
    assert s1 == s2, "压缩改变了页面尺寸（不应改变）"
    assert len(set(s1)) == 3, "页面尺寸未跟随每张图片"
    assert r2["pdf_bytes"] < r["pdf_bytes"], "压缩后未变小"
    print("\n>>> 全部断言通过")


if __name__ == "__main__":
    run()
