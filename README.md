# ImageToPDF Studio v1.8

把图片直接转成 PDF 的 Windows 桌面工具。**页面尺寸跟随每张图片自身尺寸**（不强制 A4），提供类 Acrobat DC 的压缩与口令保护，支持图片 / 文件夹 / 压缩包（含密码）导入。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20x64-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

## 特性

| 能力 | 说明 |
|---|---|
| 页面尺寸 | 读取图片 DPI 元数据，按 `px ÷ DPI × 72 = pt` 生成页面；横图横页、竖图竖页、每页尺寸可不同。另支持固定 DPI、最长边限制、统一 A4/A3/自定义纸张 |
| 导入 | 图片、文件夹、ZIP / 7Z / RAR 压缩包；支持拖放 |
| 加密压缩包 | AES 加密 ZIP、带密码 7Z；密码弹窗输入，本次会话记住。RAR 需本机装有 7-Zip 或 WinRAR |
| 排序 | 文件名自然排序、修改时间、大小、扩展名；列表拖拽、右键置顶/上移/下移/置底/置底、仅选中项排序 |
| 视图 | 预览小图 ⇄ 纯文字详细信息（9 列：尺寸、DPI、页面尺寸、体积、修改时间、路径） |
| 压缩 | 双立方下采样 + baseline JPEG + 图形类图片调色板 PNG + 仅在体积减小时替换；屏幕/均衡/印刷/极限/自定义档 |
| 阅读优化 | 「阅读流畅优先」统一预处理为 baseline JPEG；单页像素上限；「移动端一键优化」「随便看看 · 最小最快」两个一键档 |
| PDF 安全 | AES-256 / AES-128 / RC4-128，打开密码 + 所有者密码 + 打印/复制/修改/注释权限 |
| 其它 | 按文件名写书签、后台转换与取消、双击预览、进度条、顶部横栏菜单与「关于」对话框 |

## 快速开始

### 直接用（推荐，免 Python 环境）

下载 `dist/ImageToPDF_Studio.exe`，双击运行。首次启动需数秒（单文件自解压）。
若被 SmartScreen 拦截：右键 → 属性 → 勾选「解除锁定」，或点「更多信息 → 仍要运行」。

### 从源码运行

```bash
git clone https://github.com/borisKP/ImageToPDF_Studio.git
cd ImageToPDF
python -m pip install -r requirements.txt
python src/app.py
```

无窗口自检：

```bash
python src/app.py --selftest      # 生成 _selftest.txt，检查全部依赖链路
```

### 打包成 EXE

```bat
build.bat
```

或：

```bash
python -m PyInstaller --noconfirm --distpath dist --workpath build ImageToPDF_Studio.spec
python scripts/make_source_bundle.py
```

## 使用要点

1. 「文件 → 添加图片 / 添加文件夹 / 添加压缩包」，或直接拖进窗口。
2. 想一步出文件：「文件 → 导入压缩包并直接生成 PDF」。
3. 只求快速翻看：点「随便看看 · 最小最快」（96 ppi / 质量 55 / 最长边 210 mm / 单页 ≤1 MP）。
4. 兼顾画质：点「移动端一键优化」（120 ppi / 质量 70 / 最长边 297 mm / ≤4 MP）。
5. 「③ 输出位置与文件名」设置目录与名称 → 「生成 PDF」。

> 图片网站之所以流畅，是因为下发的是 1200 px 展示副本（约为 10 MB 原图的 2%）。PDF 没有服务端，必须在生成时就把图片降维到展示尺寸。只调 JPEG 质量而页面仍是几十英寸，几乎没用。

完整说明见 [`docs/使用说明.html`](docs/使用说明.html)（浏览器打开）。

## 压缩包支持

| 格式 | 密码 | 依赖 | 备注 |
|---|---|---|---|
| ZIP（Store/Deflate） | 否 | 内置 | 标准库 / pyzipper |
| ZIP（ZipCrypto / WinZip AES） | 是 | 内置 pyzipper | 弹窗输入密码 |
| 7Z | 是 | 内置 py7zr | 含文件名加密也可（需密码） |
| RAR / RAR5 | 是 | **外部** 7-Zip 或 WinRAR | 未安装时给出明确提示；ZIP/7Z 无需任何外部工具 |

解压有安全限制：仅提取图片、跳过隐藏文件与目录穿越、单文件 ≤100 MB、最多 500 张。
总体积默认上限 1 GB，但**可在「⑤ 压缩包解压上限」调整（0 = 不限制，最高 100 GB）**；
超限时弹窗询问「继续 / 中止」，不再自动终止（v1.7 起）。
密码包解压到临时目录，关闭窗口时自动清理。

## 体积

单文件 EXE 约 **52 MB**，免 Python 环境。`ImageToPDF_Studio.spec` 里做了这些精简，改动时请勿回退：

- 不调用 `collect_dynamic_libs('pymupdf')`：hook 已自动收集，重复会多 13.8 MB。
- 按文件名剔除未使用的 Qt 动态库与图片格式插件（QML / Quick / PDF / OpenGL / SVG、tiff / webp / jpeg / gif / bmp 等）。
- 剔除 `pymupdf/layout` 附带的约 40 MB ONNX 布局模型与 Pillow 的 AVIF 解码器（本程序都用不到）。
- **不启用 UPX**：onefile 的 CArchive 已 zlib 压缩，UPX 后的高熵数据反而让 EXE 变大（实测 75 → 96 MB）。

自查组成：`python scripts/analyze_exe_size.py`（无需安装 PyInstaller）。

## 目录结构

```
ImageToPDF/
├── .github/workflows/build.yml  # Windows CI：测试 + 打包
├── .gitignore
├── LICENSE                      # MIT
├── README.md                    # 本文件
├── CHANGELOG.md                 # 版本演进
├── CONTRIBUTING.md              # 开发与发版约定
├── requirements.txt
├── build.bat                    # 一键打包 EXE 并同步源码交付物
├── ImageToPDF_Studio.spec       # PyInstaller 配置
├── src/
│   ├── app.py                   # 图形界面与入口
│   ├── core.py                  # 转换引擎
│   └── archive.py               # 压缩包导入
├── tests/                       # 回归测试
├── docs/                        # 使用者 / 源码说明（HTML）
├── assets/                      # 图标
├── scripts/                     # 诊断脚本与源码包生成器
├── dist/                        # （构建产物，不入库）
└── 源码交付/                    # （构建产物，不入库）
```

## 开发

```bash
python -m pip install -r requirements.txt
python tests/test_core.py
python tests/test_archive.py
QT_QPA_PLATFORM=offscreen python tests/test_gui.py
```

诊断脚本位于 `scripts/`，可复现压缩编码、渲染耗时、WebP 可行性、大原图降维等实测数据。

**发版规则**：版本号唯一来源是 `src/app.py` 的 `APP_VER`。改完版本只需运行 `build.bat`，它会依次打包 EXE、调用 `scripts/make_source_bundle.py` 同步所有文档版本号并重建 `源码交付/` 里的 zip 与整合版单文件源码。详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

## 开源

- 许可证：MIT，见 [`LICENSE`](LICENSE)。如改用其它许可证，替换该文件并同步 `src/app.py` 的 `LICENSE_NAME`。
- 项目主页：`https://github.com/borisKP/ImageToPDF_Studio`（已写入 `src/app.py` 的 `PROJECT_URL`，关于对话框可直接打开）。
- 维护者推送：

```bash
git remote add origin https://github.com/borisKP/ImageToPDF_Studio.git
git push -u origin main
```

## 致谢

[PySide6](https://doc.qt.io/qtforpython/) · [Pillow](https://python-pillow.org/) · [PyMuPDF](https://pymupdf.readthedocs.io/) · [py7zr](https://github.com/miurahr/py7zr) · [pyzipper](https://github.com/danifus/pyzipper) · [PyInstaller](https://pyinstaller.org/)
