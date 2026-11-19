# -*- coding: utf-8 -*-
"""生成 README 用的软件界面截图（原生 Windows 平台渲染，保证中文字体可用）。

用法：
    python scripts/make_screenshot.py
输出：
    assets/screenshot_main.png
"""
from __future__ import annotations

import os
import sys
import time

# 不要用 offscreen：该平台下 QFontDatabase 无字体，中文会渲染成方块。
os.environ.pop("QT_QPA_PLATFORM", None)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402
import app as gui  # noqa: E402


def main():
    qapp = QApplication.instance() or QApplication([])
    qapp.setApplicationName(gui.APP_NAME)
    qapp.setStyle("Fusion")
    qapp.setStyleSheet(gui.QSS)

    w = gui.MainWindow()
    w.resize(1460, 900)

    # 填入示例图片，使截图不是空列表
    sample_dir = os.path.join(ROOT, "tests", "_test_images")
    samples = [os.path.join(sample_dir, f) for f in sorted(os.listdir(sample_dir))
               if f.lower().endswith((".jpg", ".jpeg", ".png"))][:3]
    if samples:
        w.add_paths(samples)

    w.show()
    for _ in range(12):
        qapp.processEvents()
        time.sleep(0.1)   # 等缩略图线程完成，避免截图里出现空白格子

    out = os.path.join(ROOT, "assets", "screenshot_main.png")
    ok = w.grab().save(out)
    if not ok:
        raise SystemExit("截图保存失败")
    print(f"截图已生成: {out}")


if __name__ == "__main__":
    main()
