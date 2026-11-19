# -*- coding: utf-8 -*-
"""生成程序图标 app.ico"""
import os
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))


def make(size=256):
    S = size
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = int(S * 0.20)
    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=r, fill=(37, 99, 235, 255))
    # 白色相框（图片）
    x0, y0, x1, y1 = int(S * .14), int(S * .18), int(S * .66), int(S * .64)
    d.rounded_rectangle((x0, y0, x1, y1), radius=int(S * .04),
                        fill=(255, 255, 255, 255))
    d.rectangle((x0 + int(S * .05), y0 + int(S * .05),
                 x1 - int(S * .05), y1 - int(S * .10)), fill=(147, 197, 253, 255))
    d.ellipse((x0 + int(S * .09), y0 + int(S * .09),
               x0 + int(S * .20), y0 + int(S * .20)), fill=(250, 204, 21, 255))
    d.polygon([(x0 + int(S * .05), y1 - int(S * .10)),
               (x0 + int(S * .20), y0 + int(S * .22)),
               (x0 + int(S * .33), y1 - int(S * .10))], fill=(59, 130, 246, 255))
    # 右下 PDF 标记
    px0, py0 = int(S * .56), int(S * .55)
    px1, py1 = int(S * .90), int(S * .86)
    d.rounded_rectangle((px0, py0, px1, py1), radius=int(S * .04),
                        fill=(239, 68, 68, 255), outline=(255, 255, 255, 255),
                        width=max(2, int(S * .012)))
    fs = max(8, int(S * .115))
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", fs)
    except Exception:
        font = None
    d.text((px0 + int(S * .035), py0 + int(S * .11)), "PDF",
           fill=(255, 255, 255, 255), font=font)
    return im


def main():
    base = make(256)
    path = os.path.join(BASE, "app.ico")
    base.save(path, format="ICO",
              sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    base.save(os.path.join(BASE, "app.png"))
    print("icon:", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
