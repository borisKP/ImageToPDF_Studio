# -*- coding: utf-8 -*-
"""压缩包导入自测：普通 ZIP / AES 密码 ZIP / 密码 7z / 密码错误分支"""
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))

import os
import shutil
import tempfile
import zipfile

import py7zr
import pyzipper
from PIL import Image
import archive

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "_archive_test_out")
PW = "pw123"


def make_images(folder):
    os.makedirs(folder, exist_ok=True)
    for i, (name, color) in enumerate([
        ("01_横图.png", (30, 90, 180)),
        ("02_竖图.png", (220, 60, 60)),
        ("10_截图.png", (240, 240, 240)),
    ]):
        Image.new("RGB", (200 + i * 40, 120 + i * 30), color).save(
            os.path.join(folder, name))
    return [os.path.join(folder, n) for n in sorted(os.listdir(folder))]


def build_archives(folder, images):
    paths = {}
    plain = os.path.join(OUT, "plain.zip")
    with zipfile.ZipFile(plain, "w", zipfile.ZIP_DEFLATED) as z:
        for p in images:
            z.write(p, os.path.basename(p))
    paths["plain"] = plain

    aes = os.path.join(OUT, "aes.zip")
    with pyzipper.AESZipFile(aes, "w", compression=pyzipper.ZIP_DEFLATED,
                             encryption=pyzipper.WZ_AES) as z:
        z.setpassword(PW.encode())
        for p in images:
            z.write(p, os.path.basename(p))
    paths["aes"] = aes

    seven = os.path.join(OUT, "enc.7z")
    with py7zr.SevenZipFile(seven, "w", password=PW) as z:
        for p in images:
            z.write(p, os.path.basename(p))
    paths["7z"] = seven
    return paths


def run():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    imgs = make_images(os.path.join(OUT, "src"))
    paths = build_archives(os.path.join(OUT, "src"), imgs)
    print("测试压缩包:", {k: os.path.getsize(v) for k, v in paths.items()})

    for kind, pw in (("plain", None), ("aes", PW), ("7z", PW)):
        dest = tempfile.mkdtemp(prefix="i2p_arch_")
        got = archive.extract_archive(paths[kind], dest, pw)
        print(f"  {kind:6s} -> {len(got)} 张:", [os.path.basename(p) for p in got])
        assert len(got) == 3, f"{kind} 解压数量错误"
        assert [os.path.basename(p) for p in got] == [
            "01_横图.png", "02_竖图.png", "10_截图.png"], "文件名自然排序错误"
        for p in got:
            with Image.open(p) as im:
                im.verify()
        shutil.rmtree(dest, ignore_errors=True)

    # 需要密码
    dest = tempfile.mkdtemp(prefix="i2p_arch_")
    try:
        archive.extract_archive(paths["aes"], dest, None)
        raise AssertionError("AES zip 未提供密码却没报错")
    except archive.PasswordRequired:
        print("  AES zip 无密码 -> PasswordRequired OK")
    shutil.rmtree(dest, ignore_errors=True)

    # 错误密码
    for kind in ("aes", "7z"):
        dest = tempfile.mkdtemp(prefix="i2p_arch_")
        try:
            archive.extract_archive(paths[kind], dest, "wrong")
            raise AssertionError(f"{kind} 错误密码却没报错")
        except archive.BadPassword:
            print(f"  {kind} 错误密码 -> BadPassword OK")
        shutil.rmtree(dest, ignore_errors=True)

    # ---- 解压体积上限：可配置 / 可继续 / 可关闭 ----
    dest = tempfile.mkdtemp(prefix="i2p_lim_")
    try:
        archive.extract_archive(paths["plain"], dest, None, limit_bytes=100)
        raise AssertionError("超低上限却没抛 LimitExceeded")
    except archive.LimitExceeded:
        print("  上限 100 B 且不允许继续 -> LimitExceeded OK")
    shutil.rmtree(dest, ignore_errors=True)

    dest = tempfile.mkdtemp(prefix="i2p_lim_ok_")
    got = archive.extract_archive(paths["plain"], dest, None, limit_bytes=100,
                                  on_limit=lambda *_: True)
    assert len(got) == 3, "选择继续后未完整解压"
    print("  上限 100 B 选择继续 -> 3 张 OK")
    shutil.rmtree(dest, ignore_errors=True)

    dest = tempfile.mkdtemp(prefix="i2p_lim_none_")
    got = archive.extract_archive(paths["plain"], dest, None, limit_bytes=0)
    assert len(got) == 3, "不限制模式解压失败"
    print("  设为不限制 -> 3 张 OK")
    shutil.rmtree(dest, ignore_errors=True)

    # 端到端：加密压缩包 -> 图片列表 -> PDF
    import core
    import pymupdf as fitz
    dest = tempfile.mkdtemp(prefix="i2p_e2e_")
    got = archive.extract_archive(paths["aes"], dest, PW)
    st = core.ConvertSettings()
    st.compress.reading_mode = True
    st.compress.max_megapixels = 1.0
    pdf = os.path.join(OUT, "从压缩包生成.pdf")
    r = core.convert(got, pdf, st)
    doc = fitz.open(pdf)
    print("  端到端: 加密 ZIP ->", r["pages"], "页 PDF,", r["pdf_bytes"], "B")
    assert doc.page_count == 3 and r["encrypted"] is False
    doc.close()
    shutil.rmtree(dest, ignore_errors=True)

    print("\n>>> 压缩包自测全部通过")


if __name__ == "__main__":
    run()
