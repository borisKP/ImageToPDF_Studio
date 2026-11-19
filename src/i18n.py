# -*- coding: utf-8 -*-
"""多语言支持。

设计要点（后续加语言只需 3 步）：
  1. LANGS 增加 (code, 显示名)；
  2. TRANSLATIONS[code] 增加字典；
  3. 无需改动 app.py —— 菜单由 LANGS 自动生成，静态控件按原文查表重翻译。

中文原文是 key。未翻译的条目原样显示，不会崩。
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal

LANGS = [("zh", "中文 / Chinese"), ("en", "English")]
DEFAULT_LANG = "zh"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "zh": {},
    "en": {
        # ---- 通用 / 菜单 / 工具栏
        "中": "Medium", "最低": "Lowest", "低": "Low", "高": "High", "最高": "Highest",
        "文件(&F)": "&File", "开始(&S)": "&Start", "视图(&V)": "&View", "帮助(&H)": "&Help",
        "设置(&P)": "&Preferences",
        "添加图片": "Add Images", "选择任意数量的图片": "Select one or more images",
        "添加文件夹": "Add Folder", "导入整个文件夹内的图片": "Import all images in a folder",
        "添加压缩包": "Add Archive", "ZIP / 7Z / RAR，可带密码；直接把图片导入列表": "ZIP / 7Z / RAR, password supported; import images directly",
        "移除选中": "Remove Selected", "从列表移除": "Remove from list", "清空": "Clear",
        "↑ 上移": "↑ Move Up", "↓ 下移": "↓ Move Down", "置顶": "Pin to Top",
        "反转顺序": "Reverse Order", "置底": "Pin to Bottom",
        "添加图片…": "Add Images…", "添加文件夹…": "Add Folder…",
        "添加压缩包…（ZIP / 7Z / RAR）": "Add Archive… (ZIP / 7Z / RAR)",
        "导入压缩包并直接生成 PDF": "Import Archive and Generate PDF",
        "清空列表": "Clear List", "退出": "Exit",
        "生成 PDF": "Generate PDF", "取消生成": "Cancel Generation",
        "上移选中": "Move Selected Up", "下移选中": "Move Selected Down",
        "应用排序": "Apply Sort", "移动端一键优化": "Mobile One-Click Optimize",
        "随便看看 · 最小最快": "Quick Look · Smallest & Fastest",
        "切换：预览小图 / 文字详细信息": "Toggle: Thumbnails / Detail Table",
        "使用说明": "User Guide", "关于 ": "About ", "关闭": "Close",
        "语言": "Language", "外观": "Appearance", "跟随系统": "Follow System",
        "浅色": "Light", "深色": "Dark",
        "已切换为英文，界面将持续使用英文。": "Language set to English; it will be used next time too.",
        "已切换为中文，界面将持续使用中文。": "Language set to Chinese; it will be used next time too.",
        "切换语言后，新打开的窗口与弹窗将使用新语言。": "New windows and dialogs will use the selected language.",
        "已切换为跟随系统主题。": "Theme now follows the system setting.",
        "已切换为浅色主题。": "Light theme applied.",
        "已切换为深色主题。": "Dark theme applied.",

        # ---- 列表 / 视图
        "图片列表": "Image List", "切换为：详细信息": "Switch to: Details",
        "切换为：预览小图": "Switch to: Thumbnails", "排序：": "Sort:",
        "文件名（自然 · 升序）": "Filename (natural · ascending)",
        "文件名（自然 · 降序）": "Filename (natural · descending)",
        "文件名（字母 · 升序）": "Filename (alphabetic · ascending)",
        "修改时间（旧→新）": "Modified (old → new)", "修改时间（新→旧）": "Modified (new → old)",
        "文件大小（小→大）": "Size (small → large)", "文件大小（大→小）": "Size (large → small)",
        "扩展名": "Extension", "当前手动顺序": "Current manual order",
        "#": "#", "文件名": "Filename", "格式": "Format", "像素尺寸": "Pixels",
        "DPI": "DPI", "页面尺寸 (mm)": "Page (mm)", "文件大小": "File Size",
        "修改时间": "Modified", "所在路径": "Path",
        "提示：可直接把图片/文件夹拖进窗口；列表内拖拽调整顺序；右键可置顶、上移、下移、置底；双击预览大图。":
            "Tip: drag images/folders into the window; drag inside the list to reorder; right-click for pin/move; double-click to preview.",
        "详细信息模式：纯文字、不显示预览图。列含像素尺寸、DPI、按当前设置算出的实际页面尺寸、体积与修改时间；右键同样可置顶 / 移动 / 排序 / 移除，双击预览大图。":
            "Detail mode: text only. Columns: pixels, DPI, computed page size, file size and mtime. Right-click menu and double-click preview still work.",
        "置顶": "Pin to Top", "上移": "Move Up", "下移": "Move Down", "置底": "Pin to Bottom",
        "按文件名排序选中项": "Sort Selected by Filename", "反转选中项顺序": "Reverse Selected Order",
        "预览大图": "Preview Full Image", "打开输出文件夹": "Open Output Folder", "取消": "Cancel",

        # ---- ① 页面
        "① 页面尺寸（每页跟随图片，不强制 A4）": "① Page Size (follows each image, no forced A4)",
        "按图片实际尺寸（等同 Acrobat「保留原始尺寸」）": "Use actual image size (like Acrobat 'Keep Original Size')",
        "统一纸张尺寸（图片等比居中适配）": "Uniform paper size (fit image proportionally)",
        "尺寸依据": "Size Basis", "读取图片自带 DPI": "Read image DPI",
        "固定 DPI（忽略元数据）": "Fixed DPI (ignore metadata)",
        "默认 DPI": "Default DPI", "元数据缺失时使用": "Used when metadata is missing",
        "固定 DPI": "Fixed DPI", "px ÷ DPI × 72 = 页面 pt": "px ÷ DPI × 72 = page pt",
        "最长边限制": "Max Edge Limit", "不限制": "Unlimited",
        "297 mm（A4 长边）": "297 mm (A4 long edge)", "420 mm（A3 长边）": "420 mm (A3 long edge)",
        "自定义长边": "Custom long edge", "防止 72dpi 手机照生成巨页": "Prevents huge pages from 72 dpi phone photos",
        "纸张": "Paper", "自定义": "Custom", "宽 × 高": "Width × Height",
        "横图自动使用横向纸张": "Auto landscape paper for landscape images",
        "页边距": "Margin", "按图片尺寸模式下建议 0": "0 recommended in image-size mode",
        "按图片实际尺寸": "Actual image size", "统一纸张": "Uniform paper",

        # ---- ② 压缩
        "② 压缩 / 图像优化（仿 Acrobat DC PDF 优化器）": "② Compression / Image Optimization (Acrobat-style)",
        "预设档位": "Preset", "无损 · 原始嵌入（不重编码）": "Lossless · original embed (no re-encode)",
        "屏幕阅读 · 150 ppi / 中等质量": "Screen reading · 150 ppi / medium quality",
        "均衡 · 200 ppi / 高质量": "Balanced · 200 ppi / high quality",
        "印刷 · 300 ppi / 最高质量": "Print · 300 ppi / highest quality",
        "极限压缩 · 96 ppi / 低质量": "Extreme · 96 ppi / low quality",
        "120 ppi / 质量 70 / 最长边 297mm / 统一 baseline JPEG / 单页 ≤4MP": "120 ppi / quality 70 / max 297 mm / baseline JPEG / ≤4 MP per page",
        "96 ppi / 质量 55 / 最长边 210mm / 统一 baseline JPEG / 单页 ≤1MP；只求能快速翻看，画质够用即可":
            "96 ppi / quality 55 / max 210 mm / baseline JPEG / ≤1 MP per page; fast scrolling, good enough quality",
        "目标分辨率": "Target Resolution", "屏幕 150 / 印刷 300": "Screen 150 / Print 300",
        "低于 96 ppi：移动端放大后明显模糊": "Below 96 ppi: noticeably blurry when zoomed on mobile",
        "仅高于此值时": "Only above", "Acrobat: for images above": "Acrobat: for images above",
        "JPEG 质量": "JPEG Quality", "75 · 高": "75 · High",
        "重采样算法": "Resampling", "双立方（渐变最平滑，推荐）": "Bicubic (smoothest gradients, recommended)",
        "平均（平坦色块）": "Average (flat areas)", "次取样（线稿最快）": "Subsample (fastest for line art)",
        "仅在体积变小时才替换（不反向增大文件）": "Replace only if smaller (never increase file size)",
        "灰度图自动转灰度（进一步减小）": "Convert grayscale images to grayscale",
        "剥离 EXIF / ICC 元数据": "Strip EXIF / ICC metadata",
        "透明背景转白底（可用 JPEG）": "Flatten transparency to white (allows JPEG)",
        "图形类图片自动选用调色板 PNG（照片不会走量化）": "Use palette PNG for graphics (photos are never quantized)",
        "阅读流畅优先：先把所有图片统一转成 baseline JPEG（PDF 内不再有 Flate 图像）":
            "Smooth reading first: preprocess all images to baseline JPEG (no Flate images in PDF)",
        "单页图像像素上限": "Max image pixels per page", "4 MP ≈ 12 MB 解码内存；移动端建议 3–4 MP":
            "4 MP ≈ 12 MB decode memory; 3–4 MP recommended for mobile",

        # ---- ③ 输出 / ④ 安全 / ⑤ 压缩包
        "③ 输出位置与文件名": "③ Output Location & Filename", "保存目录": "Save Folder",
        "浏览…": "Browse…", "文件名": "Filename", "按文件名生成 PDF 书签（目录）": "Create PDF bookmarks from filenames",
        "输出为单个 PDF，图片张数 = 页数；文件不存在时自动建目录": "One PDF; images = pages; folders are created automatically",
        "④ PDF 密码与权限": "④ PDF Password & Permissions", "启用密码保护（打开 PDF 必须输入口令）":
            "Enable password protection (required to open)",
        "打开密码": "Open Password", "必填 · 打开 PDF 时输入": "Required when opening the PDF",
        "确认密码": "Confirm Password", "再输入一次": "Enter again",
        "所有者密码": "Owner Password", "可选 · 留空则与打开密码相同": "Optional; empty = same as open password",
        "显示密码": "Show Password", "偏短，建议 ≥ 8 位": "Too short; 8+ characters recommended",
        "长度良好": "Good length", "长度中等": "Fair length",
        "加密方式": "Encryption", "AES-256（推荐，Acrobat X+）": "AES-256 (recommended, Acrobat X+)",
        "AES-128（兼容旧版 Acrobat）": "AES-128 (older Acrobat compatible)",
        "RC4-128（兼容性最好，安全性较低）": "RC4-128 (most compatible, weaker security)",
        "AES-256": "AES-256", "版本": "Version",
        "允许的操作（取消勾选 = 禁用相应权限）": "Allowed Actions (uncheck = deny)",
        "打印": "Print", "高质量打印": "High-quality print", "复制文本 / 图像": "Copy text / images",
        "修改内容 / 页面组装": "Modify / assemble pages", "注释 / 填写表单": "Annotate / fill forms",
        "⑤ 压缩包解压上限": "⑤ Archive Extraction Limit", "解压总体积上限": "Total extraction limit",
        "设为 0（不限制）可完整解压任意大小的压缩包": "Set 0 (unlimited) to extract archives of any size",
        "超限时弹窗询问是否继续（关闭则直接中止）": "Ask to continue when limit exceeded (off = abort)",
        "快捷：": "Quick:", "不限制": "Unlimited",

        # ---- 弹窗 / 状态
        "解压体积超过上限": "Extraction Size Limit Exceeded",
        " GB，超过设定上限 ": " GB, exceeding the limit of ",
        " GB。\n\n可能是压缩包炸弹，也可能只是正常的大图包。\n是否继续解压？":
            " GB.\n\nThis may be an archive bomb or just a large image set.\nContinue extracting?",
        "选择图片（可多选）": "Select Images (multiple allowed)",
        "图片文件 (*.jpg *.jpeg *.jfif *.png *.bmp *.tif *.tiff *.webp *.gif);;所有文件 (*.*)":
            "Images (*.jpg *.jpeg *.jfif *.png *.bmp *.tif *.tiff *.webp *.gif);;All files (*.*)",
        "选择图片文件夹": "Select Image Folder", "选择压缩包（可多选）": "Select Archives (multiple allowed)",
        "压缩包 (*.zip *.7z *.rar);;所有文件 (*.*)": "Archives (*.zip *.7z *.rar);;All files (*.*)",
        "选择保存目录": "Select Output Folder", "无图片": "No Images", "请先添加图片。": "Add images first.",
        "文件已存在": "File Exists", "覆盖现有文件？\n": "Overwrite existing file?\n",
        "缺少打开密码": "Open Password Missing", "已启用密码保护，请在「④ PDF 密码与权限」填写打开密码。":
            "Password protection is enabled. Set the open password in section ④.",
        "密码不一致": "Passwords Do Not Match", "「打开密码」与「确认密码」不一致，请重新输入。":
            "Open password and confirmation differ. Please re-enter.",
        "正在转换 …": "Converting…", "正在取消 …": "Cancelling…", "生成失败": "Conversion Failed",
        "生成完成": "Conversion Complete", "输出：": "Output: ", "\n\n页数：": "\n\nPages: ",
        "\n源文件合计：": "\nSource total: ", "\nPDF 大小：": "\nPDF size: ",
        "  （为源文件的 ": "  (", "）": ")",
        "\n已预处理为 baseline JPEG（阅读流畅优先，PDF 内无 Flate 图像）":
            "\nPreprocessed to baseline JPEG (no Flate images in PDF)",
        "\n已加密：": "\nEncrypted: ", " · 打开需输入口令": " · password required to open",
        "\n\n以下图片失败：\n": "\n\nFailed images:\n",
        "完成 · ": "Done · ", " 页 · ": " pages · ",
        "已应用移动端优化：120 ppi / 质量70 / 最长边297mm / 统一 baseline JPEG / 单页≤4MP":
            "Mobile preset applied: 120 ppi / quality 70 / max 297 mm / baseline JPEG / ≤4 MP per page",
        "已应用「随便看看」：96 ppi / 质量55 / 最长边210mm / 统一 baseline JPEG / 单页≤1MP":
            "Quick-look preset applied: 96 ppi / quality 55 / max 210 mm / baseline JPEG / ≤1 MP per page",
        "压缩包需要密码": "Archive Password Required", " 已加密，请输入解压密码：": " is encrypted. Enter password:",
        "密码错误": "Wrong Password", " 密码不正确，请重新输入（取消可跳过）：": " password is wrong. Re-enter (Cancel to skip):",
        "已中止解压": "Extraction Aborted",
        "\n\n如需导入，请在「⑤ 压缩包解压上限」调高数值或选择「不限制」，或在超限弹窗中点「继续」。":
            "\n\nRaise the limit in section ⑤ (or set Unlimited), or choose Continue in the prompt.",
        "压缩包导入失败": "Archive Import Failed", "无图片": "No Images",
        " 中未找到支持的图片。": " contains no supported images.",
        "从 ": "Imported ", " 导入 ": " images from ", " 张图片": "",

        # ---- 状态栏 / 关于 / 帮助
        "图片列表  ·  ": "Images  ·  ", " 张": "", "共 ": "Total ", " 张（选中 ": " (selected ",
        "） · 源文件合计 ": ") · Source total ", " · 页面：": " · Pages: ",
        "—（用默认）": "— (use default)",
        "按图片实际尺寸生成 PDF · Acrobat DC 式压缩 · 移动端阅读优化<br>支持图片 / 文件夹 / 压缩包（含密码）导入、灵活排序、PDF 口令保护。<br><br><b>技术栈</b>：PySide6 · Pillow · PyMuPDF · py7zr · pyzipper<br><b>许可证</b>：":
            "Images to PDF at original page size · Acrobat-style optimization · mobile-friendly<br>Image / folder / archive (password) import, sorting, PDF protection.<br><br><b>Stack</b>: PySide6 · Pillow · PyMuPDF · py7zr · pyzipper<br><b>License</b>: ",
        "<br><b>运行环境</b>：Windows x64 · Python ": "<br><b>Runtime</b>: Windows x64 · Python ",
        "<br><b>构建日期</b>：": "<br><b>Built</b>: ",
        "<br><b>项目主页</b>：": "<br><b>Project</b>: ",
        "版本 v": "Version v", "按图片原尺寸生成 PDF": "Generate PDF at original image size",
        "图片合集_": "Images_", "为源文件的 ": "of source size ",
        "张": "images", "张（选中 ": " images (", "帮助": "Help", "开始": "Start", "文件": "File",
        "左侧在「预览小图」与「文字详细信息（无缩略图）」之间切换":
            "Switch between thumbnail preview and text-only detail view",
        "逻辑：按页面实际 ppi 双立方下采样 → baseline JPEG（不用渐进式，兼容移动端）→ 仅图形类图片尝试调色板 PNG → 与无损流比体积取小者。页面物理尺寸不变；想再缩小，优先用「最长边限制」缩小页面，而不是把 ppi 压到 72 以下。":
            "Logic: bicubic downsample to effective page ppi → baseline JPEG (no progressive, mobile-friendly) → palette PNG for graphics → keep the smaller stream. Physical page size stays unchanged; use Max Edge Limit rather than very low ppi.",
        "打开密码是硬保护；权限限制取决于阅读器是否遵守标准，部分工具可绕过。忘记密码无法恢复。旧版移动阅读器可能不支持 AES-256，若移动端白页，改用 AES-128 / RC4-128 或不加密。":
            "The open password is hard protection; permission flags depend on reader compliance. A forgotten password cannot be recovered. Some older mobile readers do not support AES-256; use AES-128 / RC4-128 or no encryption if pages appear blank.",
        "超过上限时不再自动终止：默认弹窗问「继续 / 中止」，选继续即完整解压；也可把上限调高或设为「不限制」。单文件 100 MB、最多 500 张仍固定。RAR 需本机安装 7-Zip 或 WinRAR。":
            "When the limit is exceeded: a dialog asks Continue / Abort; Continue extracts everything. You can also raise the limit or set Unlimited. Fixed limits: 100 MB per file, 500 images. RAR needs local 7-Zip or WinRAR.",
        "1. 添加：工具栏「添加图片 / 添加文件夹 / 添加压缩包」，或直接把图片、文件夹、压缩包拖进窗口。\n   压缩包支持 ZIP（含 AES 密码）、7Z（含密码）、RAR；加密包会弹窗询问密码，本次会话记住。包内图片按文件名自然排序后进入列表；菜单「文件 → 导入压缩包并直接生成 PDF」可一步出文件。RAR 需要本机安装 7-Zip 或 WinRAR，ZIP / 7Z 无需任何外部工具。\n2. 左侧视图：点「切换为：详细信息」可在「预览小图」与「纯文字详细信息（不显示缩略图）」之间切换。文字视图列出序号、文件名、格式、像素尺寸、DPI、按当前设置算出的页面尺寸(mm)、文件大小、修改时间、所在路径；两种视图顺序完全同步，右键菜单与双击预览都可用。\n\n3. 排序：右上角选择排序依据后点「应用排序」；也可列表内拖拽、右键置顶 / 上移 / 下移 / 置底 / 仅对选中项排序。\n\n4. 页面尺寸（关键差异）：默认「按图片实际尺寸」—— 读取每张图片的 DPI，按 像素 ÷ DPI × 72 生成对应 pt 的页面，横图横页、竖图竖页、每页可不同尺寸，与 Acrobat「保留原始尺寸」一致；不强制 A4。\n   若图片 DPI 缺失或偏低，可用「固定 DPI」或「最长边限制」避免生成超大页面。\n   需要统一 A4 / A3 / 自定义纸张时，切到「统一纸张尺寸」。\n\n5. 压缩：仿 Acrobat PDF 优化器。按图像在页面上的实际 ppi 判断是否超过触发阈值，超过则双立方（LANCZOS）下采样到目标 ppi → JPEG 编码（高质量自动 4:4:4） → 与调色板 PNG 比体积取小者 → 若仍大于无损流则保留原始。页面物理尺寸全程不变，只降低图像分辨率。\n   无损档直接嵌入原始 JPEG/PNG 字节，零重编码。\n   移动端兼容：只输出 baseline JPEG（不用渐进式），照片不走 256 色量化；想再缩小体积，优先用「最长边限制」缩小页面，而不是把 ppi 压到 96 以下。\n   打开/翻页卡：勾「阅读流畅优先」把所有图片先统一转成 baseline JPEG，或点「移动端一键优化」（120 ppi / 质量70 / 长边297mm / 单页≤4MP）。PNG/Flate 虽然体积更小，但阅读器要解压成原始像素，实测比 JPEG 慢。\n   只要随便看看：点「随便看看 · 最小最快」（96 ppi / 质量55 / 长边210mm / 单页≤1MP）。图片网站流畅是因为它下发的是 1200px 展示副本（约为 10MB 原图的 2%），PDF 没有服务端，必须在生成时就把图片降维到展示尺寸；只调质量/ppi 而页面仍是几十英寸，几乎没用。\n\n6. 输出：选择目录 + 文件名，生成单个 PDF，并可按文件名写入书签目录。\n\n7. 密码：在「④ PDF 密码与权限」勾选启用，填打开密码 + 确认密码；可选填所有者密码（留空同打开密码）、选加密方式（AES-256 / AES-128 / RC4-128）、勾选允许的打印/复制/修改/注释权限。打开密码是硬保护，忘记无法恢复。\n\n8. 菜单：顶部横栏「文件 / 开始 / 视图 / 帮助」，右上角常显版本号；「开始」集中常用操作与两个一键档，「帮助 → 关于」显示版本、许可证、技术栈与项目主页。\n\n9. 压缩包上限：「⑤ 压缩包解压上限」可设 0（不限制）～100 GB，默认 1 GB，另有 1/3/10 GB/不限制快捷按钮。超限时弹窗询问「继续 / 中止」，不再自动终止；关闭「超限时弹窗询问」才会直接中止。单文件 100 MB、最多 500 张仍固定。":
            "1. Add: toolbar Add Images / Add Folder / Add Archive, or drag files into the window.\n   ZIP (AES password), 7Z (password), RAR are supported; encrypted archives prompt for a password, remembered for this session. RAR needs local 7-Zip or WinRAR.\n2. Left view: switch between thumbnails and a text-only detail table (pixels, DPI, computed page size, file size, mtime, path). Both views stay in sync; context menu and double-click preview work in both.\n3. Sorting: pick a criterion top-right and click Apply Sort; drag items or use the right-click menu.\n4. Page size: default is actual image size (like Acrobat Keep Original Size) — DPI metadata drives page pt; landscape images get landscape pages. No forced A4.\n5. Compression: bicubic downsample → baseline JPEG → palette PNG for graphics → keep smallest. Physical page size unchanged. Use the Max Edge Limit to shrink pages further.\n6. Output: set folder + filename; one PDF with optional filename bookmarks.\n7. Password: enable in section ④, set open + confirm passwords. The open password is hard protection.\n8. Menus: File / Start / View / Preferences / Help; Preferences has Language and Appearance (light / dark / follow system).\n9. Archive limit: section ⑤ (0 = unlimited to 100 GB, default 1 GB). Over-limit asks Continue / Abort.",
    },
}


class _Bus(QObject):
    language_changed = Signal(str)
    theme_changed = Signal(str)


bus = _Bus()
_settings = QSettings("BorisKP", "ImageToPDF_Studio")
_current = _settings.value("language", DEFAULT_LANG)
if _current not in dict(LANGS):
    _current = DEFAULT_LANG


def current_lang() -> str:
    return _current


def set_lang(code: str, *, notify: bool = True) -> None:
    global _current
    if code not in dict(LANGS) or code == _current:
        return
    _current = code
    _settings.setValue("language", code)
    if notify:
        bus.language_changed.emit(code)


def tr(text: str) -> str:
    """把中文原文翻译成当前语言；没有词条则原样返回。"""
    if _current == "zh":
        return text
    return TRANSLATIONS.get(_current, {}).get(text, text)


def lang_name(code: str) -> str:
    return dict(LANGS).get(code, code)


def convert(text: str, target: str) -> str:
    """把任一当前语言已显示的文本转换为目标语言（用于运行时重翻译已有控件）。"""
    if not text or target not in dict(LANGS):
        return text
    if target == "zh":
        for zh, en in TRANSLATIONS.get("en", {}).items():
            if en == text:
                return zh
        return text
    return TRANSLATIONS.get(target, {}).get(text, text)

