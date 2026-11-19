# -*- coding: utf-8 -*-
"""压缩包导入：ZIP(含 AES 密码) / 7z(含密码) / RAR(外部工具)。

只做一件事：把压缩包里的图片安全地解压到指定目录，返回图片路径列表。
不依赖 core.py，便于整合版单文件源码内联。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import zipfile
from typing import Callable

ARCHIVE_EXTS = {".zip", ".7z", ".rar"}
IMAGE_EXTS = {".jpg", ".jpeg", ".jfif", ".png", ".bmp", ".tif", ".tiff",
              ".webp", ".gif", ".ppm", ".pgm", ".pbm"}
MAX_FILES = 500
MAX_FILE_BYTES = 100 * 1024 * 1024       # 单文件 100 MB
MAX_TOTAL_BYTES = 1024 * 1024 * 1024    # 总计 1 GB，防解压炸弹
NO_WINDOW = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW


class ArchiveError(Exception):
    """压缩包无法解压。"""


class PasswordRequired(ArchiveError):
    """压缩包加密，需要提供密码。"""


class BadPassword(ArchiveError):
    """密码不正确。"""


class LimitExceeded(ArchiveError):
    """解压体积超过设定上限，且调用方选择不继续。"""


def _limit_message(limit: int) -> str:
    return (f"解压内容超过设定上限（{limit / 1024 ** 3:.2f} GB），已中止。"
            "可在「⑤ 压缩包」里调高上限、设为不限制，或在超限提示中选「继续」。")


def is_archive(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in ARCHIVE_EXTS


def natural_key(text: str):
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", text)]


def _is_image_name(name: str) -> bool:
    if "__MACOSX" in name or name.startswith("."):
        return False
    return os.path.splitext(name)[1].lower() in IMAGE_EXTS


def _safe_name(name: str) -> str:
    base = os.path.basename(name.replace("\\", "/")).strip()
    base = re.sub(r'[<>:"|?*\x00-\x1f]', "_", base)
    if not base or base in (".", ".."):
        base = "image.png"
    return base


def find_external_tool():
    """返回 (可执行文件路径, 类型)，用于 RAR。无则返回 None。"""
    candidates = [
        (shutil.which("7z"), "7z"),
        (shutil.which("7za"), "7z"),
        (os.path.join(os.environ.get("ProgramFiles", ""), "7-Zip", "7z.exe"), "7z"),
        (os.path.join(os.environ.get("ProgramFiles(x86)", ""), "7-Zip", "7z.exe"), "7z"),
        (shutil.which("unrar"), "unrar"),
        (os.path.join(os.environ.get("ProgramFiles", ""), "WinRAR", "UnRAR.exe"), "unrar"),
    ]
    for p, kind in candidates:
        if p and os.path.isfile(p):
            return p, kind
    return None


class _Sink:
    """把解压出的字节写入目标目录，统一做数量/体积限制与重名处理。"""

    def __init__(self, dest: str, limit_bytes: int = 0,
                 on_limit: Callable | None = None):
        self.dest = dest
        self.total = 0
        self.count = 0
        self.limit = limit_bytes        # 0 = 不限制
        self.on_limit = on_limit
        os.makedirs(dest, exist_ok=True)

    def write(self, data: bytes, original_name: str) -> str | None:
        if self.count >= MAX_FILES:
            return None
        if len(data) > MAX_FILE_BYTES:
            return None
        new_total = self.total + len(data)
        if self.limit and new_total > self.limit:
            if self.on_limit and self.on_limit(new_total, self.limit):
                self.limit = 0          # 用户选择继续：本次导入不再检查
            else:
                raise LimitExceeded(_limit_message(self.limit))
        self.total = new_total
        base = _safe_name(original_name)
        stem, ext = os.path.splitext(base)
        target = os.path.join(self.dest, base)
        n = 2
        while os.path.exists(target):
            target = os.path.join(self.dest, f"{stem}_{n}{ext}")
            n += 1
        with open(target, "wb") as f:
            f.write(data)
        self.count += 1
        return target


def _map_error(e: Exception, password: str | None):
    """把不同库的异常统一成 PasswordRequired / BadPassword / ArchiveError。"""
    msg = str(e).lower()
    tname = type(e).__name__.lower()
    needs = ("password" in msg or "encrypted" in msg or "passwordrequired" in tname)
    if password is None and needs:
        raise PasswordRequired("该压缩包已加密，需要密码") from e
    if password and ("bad password" in msg or "wrong password" in msg
                     or "corrupt" in msg or "lzma" in tname or "decrypt" in msg):
        raise BadPassword("密码不正确") from e
    raise ArchiveError(f"解压失败：{e}") from e


def _extract_zip(path: str, sink: _Sink, password: str | None,
                 progress: Callable | None):
    # AES 加密的 ZIP 必须用 AESZipFile 打开；普通 ZipFile 会在解密阶段报 Bad password。
    # AESZipFile 是 ZipFile 子类，普通 ZIP / ZipCrypto 加密 ZIP 也能读。
    try:
        import pyzipper
        opener = pyzipper.AESZipFile
    except ImportError:
        opener = zipfile.ZipFile
    pwd = password.encode("utf-8") if password else None
    with opener(path, "r") as z:
        # pyzipper 的 AES 解密器读取的是实例上的密码，而不是 read(pwd=...) 参数
        if pwd is not None and hasattr(z, "setpassword"):
            z.setpassword(pwd)
        infos = [i for i in z.infolist() if not i.is_dir() and _is_image_name(i.filename)]
        for idx, info in enumerate(infos[:MAX_FILES]):
            if info.file_size > MAX_FILE_BYTES:
                continue
            try:
                data = z.read(info)
            except RuntimeError as e:
                _map_error(e, password)
            except Exception as e:
                _map_error(e, password)
            sink.write(data, info.filename)
            if progress:
                progress(idx + 1, len(infos), info.filename)


def _extract_7z(path: str, sink: _Sink, password: str | None,
                progress: Callable | None):
    import py7zr
    try:
        with py7zr.SevenZipFile(path, "r", password=password) as z:
            names = [n for n in z.getnames()
                     if _is_image_name(n)
                     and ".." not in n.replace("\\", "/").split("/")]
            names = names[:MAX_FILES]
            # 只解压图片条目；py7zr 会自行处理内部路径安全
            z.extract(path=sink.dest, targets=names)
            if progress:
                for idx, name in enumerate(names):
                    progress(idx + 1, len(names), name)
    except (PasswordRequired, BadPassword, ArchiveError):
        raise
    except Exception as e:
        _map_error(e, password)


def _extract_rar(path: str, dest: str, password: str | None):
    tool = find_external_tool()
    if not tool:
        raise ArchiveError(
            "RAR 需要外部解压工具。请安装 7-Zip 或 WinRAR（安装后重新打开程序），"
            "或把压缩包另存为 ZIP / 7Z 后导入。")
    exe, kind = tool
    if kind == "7z":
        cmd = [exe, "x", "-y", "-o" + dest]
        if password:
            cmd.append("-p" + password)
        cmd.append(path)
    else:  # UnRAR.exe
        cmd = [exe, "x", "-y", ("-p" + password if password else "-p-"),
               path, dest + os.sep]
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, errors="replace", timeout=300,
                              creationflags=NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise ArchiveError("RAR 解压超时（超过 5 分钟）")
    out = (proc.stdout or "").lower()
    if proc.returncode != 0:
        if "password" in out or "encrypted" in out:
            if not password:
                raise PasswordRequired("该 RAR 已加密，需要密码")
            raise BadPassword("密码不正确")
        raise ArchiveError(f"RAR 解压失败（返回码 {proc.returncode}）：{out[-300:]}")


def _collect(dest: str, limit_bytes: int = 0,
             on_limit: Callable | None = None) -> list[str]:
    """收集已落盘的图片（7Z / RAR 路径），并做总量上限检查。"""
    found, total = [], 0
    limit = limit_bytes
    for root, _dirs, files in os.walk(dest):
        for fn in files:
            fp = os.path.join(root, fn)
            if not _is_image_name(fn):
                continue
            try:
                size = os.path.getsize(fp)
            except OSError:
                continue
            if size > MAX_FILE_BYTES:
                continue
            total += size
            if limit and total > limit:
                if on_limit and on_limit(total, limit):
                    limit = 0           # 用户选择继续
                else:
                    raise LimitExceeded(_limit_message(limit))
            found.append(fp)
    found.sort(key=lambda p: natural_key(os.path.basename(p)))
    return found[:MAX_FILES]


def extract_archive(path: str, dest: str, password: str | None = None,
                    progress: Callable | None = None,
                    limit_bytes: int | None = None,
                    on_limit: Callable | None = None) -> list[str]:
    """解压图片到 dest，返回按文件名自然排序的图片路径列表。

    limit_bytes: 解压总体积上限（字节）；None = 默认 1 GB；0 = 不限制。
    on_limit:    超限回调 (total, limit) -> bool；返回 True 表示继续解压，
                 False / None 表示中止并抛出 LimitExceeded。一次导入只询问一次。

    抛出 PasswordRequired / BadPassword / LimitExceeded / ArchiveError。
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in ARCHIVE_EXTS:
        raise ArchiveError(f"不支持的压缩包格式：{ext}")
    limit = MAX_TOTAL_BYTES if limit_bytes is None else int(limit_bytes)
    answered: dict = {}

    def ask(total: int, cap: int) -> bool:
        if "ok" not in answered:
            answered["ok"] = bool(on_limit(total, cap)) if on_limit else False
        return answered["ok"]

    os.makedirs(dest, exist_ok=True)
    sink = _Sink(dest, limit, ask)
    if ext == ".zip":
        _extract_zip(path, sink, password, progress)
    elif ext == ".7z":
        _extract_7z(path, sink, password, progress)
    else:
        _extract_rar(path, dest, password)
    # ZIP 已在 _Sink 中逐文件检查过，避免重复询问
    return _collect(dest, 0 if ext == ".zip" else limit, ask)
