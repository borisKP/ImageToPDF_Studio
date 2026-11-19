# -*- coding: utf-8 -*-
"""
图片转 PDF 核心引擎
- 页面尺寸按每张图片自身尺寸生成（读取图片 DPI 元数据，映射为物理英寸 -> pt）
- 无损模式直接嵌入原始 JPEG/PNG 字节流（等同 img2pdf / Acrobat 默认行为）
- 压缩模式仿 Adobe Acrobat DC「PDF 优化器」：双立方重采样下采样 + JPEG 质量
  + 灰度检测 + 仅在体积变小时替换 + 图形类图片的调色板 PNG 备选
"""
from __future__ import annotations

import io
import os
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from PIL import Image, ImageChops, ImageOps
try:
    import pymupdf as fitz  # PyMuPDF >= 1.24 官方包名
except ImportError:  # 兼容旧版
    import fitz

IMAGE_EXTS = (
    ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff",
    ".webp", ".gif", ".ppm", ".pgm", ".pbm", ".jfif",
)
RAW_EMBED_EXTS = {".jpg", ".jpeg", ".jfif", ".png"}
MAX_PAGE_PT = 14400.0  # PDF 规范建议的页面上限（200 英寸）
MM_TO_PT = 72.0 / 25.4

PAPERS = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A5": (148.0, 210.0),
    "B5": (176.0, 250.0),
    "Letter": (215.9, 279.4),
    "Legal": (215.9, 355.6),
}


def natural_key(text: str):
    """自然排序：2.jpg 排在 10.jpg 之前。"""
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", text)]


def is_image(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in IMAGE_EXTS


# ---------------------------------------------------------------- 配置对象

@dataclass
class CompressOptions:
    enabled: bool = False
    target_dpi: float = 150.0        # 下采样目标（图像在页面上的 ppi）
    trigger_dpi: float = 225.0       # 仅当有效 ppi 高于此值时下采样（Acrobat: for images above）
    quality: int = 78                # JPEG 质量 1-100
    resample: str = "bicubic"        # bicubic | average | subsample
    only_if_smaller: bool = True     # 压缩后更大则保留原始（Acrobat 同名选项）
    auto_grayscale: bool = True      # 灰度图自动转 L
    strip_metadata: bool = True      # 剥离 EXIF / ICC
    flatten_alpha: bool = True       # 透明背景转白底
    graphics_mode: bool = True       # 同时尝试调色板 PNG，取更小者（对截图/线稿更优）
    reading_mode: bool = False       # 阅读流畅优先：所有图片预处理为 baseline JPEG，杜绝 FlateDecode
    max_megapixels: float = 0.0      # 0=不限；>0 限制单页图像像素（百万），控制解码内存峰值


@dataclass
class SecurityOptions:
    """PDF 口令保护与权限（对齐 Acrobat「使用口令保护 PDF」）。"""
    enabled: bool = False
    user_pw: str = ""                # 打开口令；空则不加密
    owner_pw: str = ""               # 所有者口令；空则与打开口令相同
    method: str = "aes256"           # aes256 | aes128 | rc4_128
    allow_print: bool = True
    allow_copy: bool = True
    allow_modify: bool = True
    allow_annotate: bool = True
    allow_print_hq: bool = True


ENCRYPTION_LABELS = {
    "aes256": "AES-256（推荐，Acrobat X+）",
    "aes128": "AES-128（兼容旧版 Acrobat）",
    "rc4_128": "RC4-128（兼容性最好，安全性较低）",
}


def security_kwargs(st: "ConvertSettings") -> dict:
    """生成 doc.save() 的加密参数；未启用口令时返回空字典。"""
    sec = st.security
    if not (sec.enabled and sec.user_pw):
        return {}
    enc = getattr(fitz, {
        "aes256": "PDF_ENCRYPT_AES_256",
        "aes128": "PDF_ENCRYPT_AES_128",
        "rc4_128": "PDF_ENCRYPT_RC4_128",
    }.get(sec.method, "PDF_ENCRYPT_AES_256"), fitz.PDF_ENCRYPT_AES_256)
    p = lambda name: getattr(fitz, name, 0)
    perm = p("PDF_PERM_ACCESSIBILITY")  # 无障碍读取始终允许
    if sec.allow_print:
        perm |= p("PDF_PERM_PRINT")
    if sec.allow_copy:
        perm |= p("PDF_PERM_COPY")
    if sec.allow_modify:
        perm |= p("PDF_PERM_MODIFY") | p("PDF_PERM_ASSEMBLE")
    if sec.allow_annotate:
        perm |= p("PDF_PERM_ANNOTATE") | p("PDF_PERM_FORM")
    if sec.allow_print_hq:
        perm |= p("PDF_PERM_PRINT_HQ")
    return {
        "encryption": enc,
        "user_pw": sec.user_pw,
        "owner_pw": sec.owner_pw or sec.user_pw,
        "permissions": perm,
    }


@dataclass
class ConvertSettings:
    page_mode: str = "image"         # image=按图片尺寸 | paper=统一纸张
    dpi_source: str = "auto"         # auto=读图片DPI元数据 | fixed=固定DPI
    default_dpi: float = 96.0        # 元数据缺失时的兜底 DPI
    fixed_dpi: float = 150.0
    max_long_edge_mm: float = 0.0    # 0=不限；>0 时限制页面最长边（避免手机照片生成超大页面）
    paper_name: str = "A4"
    paper_w_mm: float = 210.0
    paper_h_mm: float = 297.0
    auto_rotate_paper: bool = True   # 横图自动用横向纸张
    margin_mm: float = 0.0
    compress: CompressOptions = field(default_factory=CompressOptions)
    security: SecurityOptions = field(default_factory=SecurityOptions)
    bookmarks: bool = True           # 按文件名生成书签
    title: str = "图片合集"


# 压缩预设：名称 / 参数（对齐 Acrobat PDF 优化器的常见档位）
PRESETS = {
    "lossless": ("无损 · 原始嵌入（不重编码）", dict(enabled=False)),
    "screen": ("屏幕阅读 · 150 ppi / 中等质量", dict(
        enabled=True, target_dpi=150.0, trigger_dpi=225.0, quality=75)),
    "balanced": ("均衡 · 200 ppi / 高质量", dict(
        enabled=True, target_dpi=200.0, trigger_dpi=300.0, quality=82)),
    "print": ("印刷 · 300 ppi / 最高质量", dict(
        enabled=True, target_dpi=300.0, trigger_dpi=450.0, quality=90)),
    "small": ("极限压缩 · 96 ppi / 低质量", dict(
        enabled=True, target_dpi=96.0, trigger_dpi=144.0, quality=58)),
}


def apply_preset(opts: CompressOptions, preset_key: str):
    if preset_key in PRESETS:
        for k, v in PRESETS[preset_key][1].items():
            setattr(opts, k, v)
    return opts


# ---------------------------------------------------------------- 图像工具

def get_dpi(im: Image.Image):
    """读取图片 DPI 元数据；无有效值返回 None。"""
    dpi = im.info.get("dpi")
    if isinstance(dpi, (tuple, list)) and len(dpi) >= 2:
        try:
            x, y = float(dpi[0]), float(dpi[1])
            if 1.0 <= x <= 10000.0 and 1.0 <= y <= 10000.0:
                return x, y
        except (TypeError, ValueError):
            pass
    dens = im.info.get("jfif_density")
    if dens:
        try:
            x, y = float(dens[0]), float(dens[1])
            if im.info.get("jfif_unit") == 2:  # 点/厘米
                x *= 2.54
                y *= 2.54
            if 1.0 <= x <= 10000.0 and 1.0 <= y <= 10000.0:
                return x, y
        except (TypeError, ValueError):
            pass
    return None


def has_exif_rotation(im: Image.Image) -> bool:
    try:
        ex = im.getexif()
        return bool(ex and int(ex.get(274, 1)) not in (0, 1))
    except Exception:
        return False


def load_image(path: str):
    """返回 (raw_bytes, PIL.Image, (dpi_x,dpi_y)|None)"""
    with open(path, "rb") as f:
        raw = f.read()
    with Image.open(io.BytesIO(raw)) as src:
        dpi = get_dpi(src)
        rotated = has_exif_rotation(src)
        # GIF / 多帧 TIFF 只取第一帧
        try:
            src.seek(0)
        except Exception:
            pass
        im = ImageOps.exif_transpose(src)
        im.load()
        return raw, im.copy(), dpi, rotated


def to_png_bytes(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    out = im
    if out.mode not in ("RGB", "L", "RGBA", "LA", "P", "1"):
        out = out.convert("RGB")
    out.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def looks_gray(im: Image.Image) -> bool:
    if im.mode != "RGB":
        return False
    try:
        r, g, b = im.split()
        return (ImageChops.difference(r, g).getextrema()[1] <= 6
                and ImageChops.difference(g, b).getextrema()[1] <= 6)
    except Exception:
        return False


RESAMPLE_MAP = {
    "bicubic": Image.Resampling.LANCZOS,   # 近似 Acrobat「双立方缩减像素采样」，平滑渐变最好
    "average": Image.Resampling.BOX,       # 近似「平均缩减像素取样」
    "subsample": Image.Resampling.NEAREST, # 近似「次取样」，最快，适合线稿
}

# 低于此分辨率，图片被拉伸到原页面尺寸后基本不可读，且移动端渲染器易降级/白页。
MIN_SAFE_DPI = 72.0


def jpeg_sof(data: bytes):
    """返回 JPEG 的 SOF marker：0xC0=baseline，0xC2=progressive。"""
    if data[:2] != b"\xff\xd8":
        return None
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
            return None
        seg = int.from_bytes(data[i + 2:i + 4], "big")
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7):
            return m
        i += 2 + seg
    return None


def looks_graphic(im: Image.Image, sample: int = 160,
                  top_n: int = 16, coverage: float = 0.45) -> bool:
    """判断截图 / 线稿 / 图表：大面积纯色块。照片类渐变返回 False，禁止 256 色量化。

    用「前 top_n 高频色的像素覆盖率」而非颜色总数 —— 渐变照片缩略后颜色也很多，
    但没有任何一种颜色占据大面积；截图/线稿则相反。
    """
    try:
        small = im.convert("RGB").resize((sample, sample), Image.Resampling.BOX)
        colors = small.getcolors(maxcolors=sample * sample)
        if colors is None:
            return False
        colors.sort(key=lambda x: x[0], reverse=True)
        return sum(c for c, _ in colors[:top_n]) / float(sample * sample) >= coverage
    except Exception:
        return False


def _prepare_rgb(im: Image.Image, opts: CompressOptions):
    """返回 (可用 JPEG 编码的图, 是否含 alpha)。"""
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    if has_alpha and not opts.flatten_alpha:
        return im.convert("RGBA"), True
    if has_alpha:
        rgba = im.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        return bg, False
    if im.mode not in ("RGB", "L"):
        return im.convert("RGB"), False
    return im.copy(), False


def compress_stream(im: Image.Image, page_w_pt: float, page_h_pt: float,
                    opts: CompressOptions, raw_size: int) -> bytes:
    """按页面物理尺寸计算有效 ppi，进行 Acrobat 式下采样 + 编码。"""
    w, h = im.size
    inch_w, inch_h = page_w_pt / 72.0, page_h_pt / 72.0
    eff_x = w / inch_w if inch_w > 0 else w
    eff_y = h / inch_h if inch_h > 0 else h

    out = im
    if opts.enabled and (eff_x > opts.trigger_dpi or eff_y > opts.trigger_dpi):
        target = max(MIN_SAFE_DPI, opts.target_dpi)
        scale = min(target / eff_x, target / eff_y, 1.0)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        if (nw, nh) != (w, h):
            out = out.resize((nw, nh), RESAMPLE_MAP.get(opts.resample, Image.Resampling.LANCZOS))

    rgb, still_alpha = _prepare_rgb(out, opts)
    if opts.auto_grayscale and looks_gray(rgb):
        rgb = rgb.convert("L")

    candidates = []

    # 1) RGBA 保留透明时只能用 PNG
    if still_alpha:
        buf = io.BytesIO()
        rgb.save(buf, format="PNG", optimize=True)
        candidates.append(buf.getvalue())
    else:
        # 2) 主路径：JPEG（照片/扫描件）
        q = max(1, min(100, int(opts.quality)))
        subsampling = 0 if q >= 88 else (1 if q >= 72 else 2)  # 高质量用 4:4:4 保留细节
        buf = io.BytesIO()
        # 必须 baseline：ISO 32000 明确指出渐进式 JPEG 嵌入 PDF 无收益，
        # 解码更慢、更耗内存；PWG PDF/is 直接禁止。移动端阅读器常出现花屏/半幅/白页。
        save_kw = dict(format="JPEG", quality=q, optimize=True, progressive=False,
                       subsampling=subsampling)
        if not opts.strip_metadata:
            icc = im.info.get("icc_profile")
            if icc:
                save_kw["icc_profile"] = icc
        rgb.save(buf, **save_kw)
        candidates.append(buf.getvalue())

        # 3) 备选：调色板 PNG —— 仅对图形类图片启用。
        # 照片走 256 色量化会产生色带/色块（常被误认为「显示异常」），
        # 且 PyMuPDF 会把 P 模式 PNG 展开成 Flate RGB 原始像素流，解码内存峰值更高。
        if opts.graphics_mode and looks_graphic(rgb):
            try:
                pal = rgb.convert("RGB").quantize(colors=256, method=Image.Quantize.FASTOCTREE)
                buf2 = io.BytesIO()
                pal.save(buf2, format="PNG", optimize=True)
                candidates.append(buf2.getvalue())
            except Exception:
                pass

    best = min(candidates, key=len)
    if opts.only_if_smaller and len(best) >= raw_size:
        # 由调用方决定是否回退到无损流
        return b""  # 空字节 = 信号：本次压缩无收益
    return best


def _cap_pixels(im: Image.Image, max_mp: float):
    """限制单页图像像素总数，控制阅读器解码时的位图内存峰值。"""
    if max_mp <= 0:
        return im
    w, h = im.size
    limit = max_mp * 1_000_000
    if w * h <= limit:
        return im
    k = (limit / (w * h)) ** 0.5
    return im.resize((max(1, round(w * k)), max(1, round(h * k))),
                     RESAMPLE_MAP["bicubic"])


def prepare_readable_stream(im: Image.Image, page_w_pt: float, page_h_pt: float,
                            opts: CompressOptions, raw_size: int) -> bytes:
    """先把图片预处理成「最适合阅读」的格式，再交给 PDF 封装。

    目标不是最小体积，而是让阅读器走最快的解码路径：
      - 一律 baseline JPEG / DCTDecode（杜绝 PNG 的 FlateDecode 原始像素流）
      - 4:4:4 采样，文字/线条不糊；质量下限 70
      - 按页面实际 ppi 下采样 + 单页像素上限，控制解码内存
    实测：同为 4000×2250，Flate 渲染 97 ms，DCT 76 ms；程序内 Flate 单位成本约为 DCT 的 8 倍。
    """
    w, h = im.size
    inch_w, inch_h = page_w_pt / 72.0, page_h_pt / 72.0
    eff_x, eff_y = w / inch_w if inch_w > 0 else w, h / inch_h if inch_h > 0 else h

    out = im
    if eff_x > opts.trigger_dpi or eff_y > opts.trigger_dpi:
        target = max(MIN_SAFE_DPI, opts.target_dpi)
        scale = min(target / eff_x, target / eff_y, 1.0)
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        if (nw, nh) != (w, h):
            out = out.resize((nw, nh),
                             RESAMPLE_MAP.get(opts.resample, Image.Resampling.LANCZOS))
    out = _cap_pixels(out, opts.max_megapixels)

    rgb, still_alpha = _prepare_rgb(out, opts)
    if still_alpha:  # JPEG 无 alpha 通道，强制白底
        rgba = rgb.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[-1])
        rgb = bg
    if opts.auto_grayscale and looks_gray(rgb):
        rgb = rgb.convert("L")

    q = max(70, min(100, int(opts.quality)))
    buf = io.BytesIO()
    save_kw = dict(format="JPEG", quality=q, optimize=True,
                   progressive=False, subsampling=0)
    if not opts.strip_metadata:
        icc = im.info.get("icc_profile")
        if icc:
            save_kw["icc_profile"] = icc
    rgb.save(buf, **save_kw)
    best = buf.getvalue()
    # 阅读优先是硬目标：即便比原 PNG 大也不回退到 FlateDecode
    if opts.only_if_smaller and not opts.reading_mode and len(best) >= raw_size:
        return b""
    return best


# ---------------------------------------------------------------- 页面计算

def compute_page_size(w: int, h: int, dpi, st: ConvertSettings):
    """返回 (page_w_pt, page_h_pt)。每页尺寸可不同 —— 这是与「固定 A4」的本质区别。"""
    if st.page_mode == "paper":
        pw, ph = PAPERS.get(st.paper_name, (st.paper_w_mm, st.paper_h_mm))
        if st.paper_name == "自定义":
            pw, ph = st.paper_w_mm, st.paper_h_mm
        pw_pt, ph_pt = pw * MM_TO_PT, ph * MM_TO_PT
        if st.auto_rotate_paper and (w > h) != (pw_pt > ph_pt):
            pw_pt, ph_pt = ph_pt, pw_pt
    else:
        if st.dpi_source == "fixed":
            dx = dy = max(1.0, st.fixed_dpi)
        else:
            base = max(1.0, st.default_dpi)
            dx, dy = (dpi if dpi else (base, base))
        pw_pt, ph_pt = w / dx * 72.0, h / dy * 72.0
        # 最长边限制：避免手机照片（DPI 元数据为 72/96）生成几十英寸的巨页
        if st.max_long_edge_mm > 0:
            limit_pt = st.max_long_edge_mm * MM_TO_PT
            longest = max(pw_pt, ph_pt)
            if longest > limit_pt:
                k = limit_pt / longest
                pw_pt *= k
                ph_pt *= k

    # PDF 规范上限保护
    longest = max(pw_pt, ph_pt)
    if longest > MAX_PAGE_PT:
        k = MAX_PAGE_PT / longest
        pw_pt *= k
        ph_pt *= k
    return max(1.0, pw_pt), max(1.0, ph_pt)


# ---------------------------------------------------------------- 主流程

def convert(paths, out_path: str, st: ConvertSettings,
            progress: Callable[[int, int, str], None] | None = None,
            should_cancel: Callable[[], bool] | None = None):
    """
    生成 PDF。返回统计字典。
    progress(done, total, message)；should_cancel() 返回 True 时中止（抛出 RuntimeError）。
    """
    total = len(paths)
    if not total:
        raise ValueError("没有可转换的图片")

    folder = os.path.dirname(os.path.abspath(out_path))
    if folder:
        os.makedirs(folder, exist_ok=True)

    doc = fitz.open()
    toc = []
    src_bytes = 0
    out_bytes = 0
    errors = []

    try:
        for idx, path in enumerate(paths):
            if should_cancel and should_cancel():
                raise RuntimeError("已取消")
            name = os.path.basename(path)
            if progress:
                progress(idx, total, f"处理 {idx + 1}/{total}：{name}")
            try:
                raw, im, dpi, rotated = load_image(path)
                w, h = im.size
                src_bytes += len(raw)

                page_w, page_h = compute_page_size(w, h, dpi, st)
                ext = os.path.splitext(path)[1].lower()

                # 无损基准流：JPEG/PNG 直接嵌入原始字节，零重编码
                if ext in RAW_EMBED_EXTS and not rotated:
                    lossless = raw
                else:
                    lossless = to_png_bytes(im)

                stream = lossless
                if st.compress.reading_mode:
                    # 先把图片统一转成最适合阅读的 baseline JPEG，再做 PDF
                    packed = prepare_readable_stream(im, page_w, page_h,
                                                     st.compress, len(lossless))
                    stream = packed if packed else lossless
                elif st.compress.enabled:
                    packed = compress_stream(im, page_w, page_h, st.compress, len(lossless))
                    # 空 = 压缩无收益（Acrobat「仅在减小时优化」）；回退到无损流
                    stream = packed if packed else lossless

                out_bytes += len(stream)
                page = doc.new_page(width=page_w, height=page_h)
                margin = max(0.0, st.margin_mm) * MM_TO_PT
                rect = fitz.Rect(margin, margin, page_w - margin, page_h - margin)
                if rect.width <= 0 or rect.height <= 0:
                    rect = fitz.Rect(0, 0, page_w, page_h)
                page.insert_image(rect, stream=stream, keep_proportion=True, overlay=True)

                if st.bookmarks:
                    toc.append([1, os.path.splitext(name)[0], idx + 1])
                im.close()
            except Exception as e:  # 单张失败不阻断整批
                errors.append(f"{name}: {e}")
                continue

        if st.bookmarks and toc:
            try:
                doc.set_toc(toc)
            except Exception:
                pass
        doc.set_metadata({
            "title": st.title or os.path.splitext(os.path.basename(out_path))[0],
            "producer": "ImageToPDF Studio (PyMuPDF)",
            "creator": "ImageToPDF Studio",
            "creationDate": time.strftime("D:%Y%m%d%H%M%S"),
        })
        if progress:
            progress(total, total, "正在写入 PDF …")
        enc_kw = security_kwargs(st)
        doc.save(out_path, garbage=4, deflate=True, clean=True, **enc_kw)
    finally:
        doc.close()

    if not os.path.exists(out_path):
        raise RuntimeError("PDF 未生成，所有图片均失败：" + " | ".join(errors[:3]))

    final_size = os.path.getsize(out_path)
    return {
        "pages": len(paths) - len(errors),
        "source_bytes": src_bytes,
        "pdf_bytes": final_size,
        "ratio": (final_size / src_bytes) if src_bytes else 0.0,
        "errors": errors,
        "output": out_path,
        "preprocessed": bool(st.compress.reading_mode),
        "encrypted": bool(security_kwargs(st)),
        "encryption": ENCRYPTION_LABELS.get(st.security.method, "").split("（")[0]
                      if security_kwargs(st) else "",
    }
