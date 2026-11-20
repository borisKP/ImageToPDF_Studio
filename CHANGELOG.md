# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与语义化版本。

## [1.10] - 2026-11-20

### Fixed
- 深色主题右侧设置面板的浅灰底纹：`theme.apply()` 现同步设置 Qt 调色板（Window/Base/Button/Highlight 等），QScrollArea viewport、QCheckBox 勾选框不再是系统浅色；底栏去掉硬编码白色，统一走 QSS。
- README 增加 Releases 历史版本入口说明。

## [1.9] - 2026-11-19

### Added
- **中英文界面切换**：「设置 → 语言」子菜单，中文 / English 即时切换，无需重启；选择写入 `QSettings`，下次启动沿用。静态控件、菜单、工具栏、组合框、弹窗、状态栏全部随之切换。
- **明暗主题**：「设置 → 外观」子菜单，浅色 / 深色 / 跟随系统（Windows 注册表 `AppsUseLightTheme`，每 3 秒检测一次自动切换）；主题选择持久化。
- 新增 `src/i18n.py`（多语言字典 + 双向文本转换，加语言只需新增字典与菜单项自动扩展）与 `src/theme.py`（QSS 模板 + 明暗配色）。
- 新增 `tests/test_i18n_theme.py` 覆盖翻译完整性、主题生成、运行时切换。

### Changed
- 版本号、构建日期同步至 1.9 / 2026-11-19；关于对话框、README、源码说明同步。

## [1.8] - 2026-11-19

### Changed
- EXE 从 75 MB 精简到 **52 MB（-31%）**，功能不变：剔除重复的 `mupdfcpp64.dll`（13.8 MB）、PySide6 hook 收集的 QML/Quick/PDF/OpenGL/SVG 等未使用动态库与图片插件（约 11 MB）、Pillow 的 AVIF 解码器（4.1 MB）、Cryptodome SelfTest 与 setuptools。
- 关闭 UPX：onefile 的 CArchive 已做 zlib 压缩，UPX 后的高熵数据反而使 EXE 从 75 MB 涨到 96 MB。
- 防止新版 PyMuPDF 2.x 把约 40 MB 的 ONNX 文档布局/表格识别模型打进包（excludes 管不到数据文件，spec 里按路径过滤）。
- 新增 `scripts/analyze_exe_size.py`，无需安装 PyInstaller 即可解析 EXE 内各组件体积。

### Fixed
- 构建环境依赖丢失后，支持通过 `PYTHONPATH` + `TMPDIR` 指向其它磁盘完成安装与打包（系统盘仅剩 111 MB 时）。

## [1.7] - 2026-11-13

### Changed
- 压缩包解压总体积上限由「硬性 1 GB 自动终止」改为**可配置选项**：「⑤ 压缩包解压上限」支持 0（不限制）～100 GB 与 1/3/10 GB 快捷按钮。
- 超限时默认弹窗询问「继续 / 中止」，选「继续」即完整解压，不再自动终止；可关闭询问改为直接中止。
- `archive.py` 新增 `limit_bytes` / `on_limit` 参数与 `LimitExceeded` 异常，一次导入只询问一次；单文件 100 MB、最多 500 张仍固定。

### Fixed
- 修复大压缩包导入时提示「解压内容超过 1 GB，已中止（疑似压缩包炸弹）」后无法继续的问题。

## [1.6] - 2026-11-09

### Added
- 顶部横栏菜单：文件 / 开始 / 视图 / 帮助，右侧常显版本号；「关于」对话框显示版本、许可证、技术栈、构建日期与项目主页。
- 压缩包导入：ZIP（含 ZipCrypto / WinZip AES 密码）、7Z（含密码）、RAR（外部 7-Zip / WinRAR）。支持密码弹窗、会话内记住密码、拖放导入。
- 「文件 → 导入压缩包并直接生成 PDF」一步出文件。
- 按 GitHub 开源规范重组仓库：`src/` `tests/` `docs/` `assets/` `scripts/` `.github/` 与 `LICENSE` / `README.md` / `CHANGELOG.md` / `CONTRIBUTING.md` / `.gitignore`。
- `src/archive.py` 与 `tests/test_archive.py`；解压安全限制（防路径穿越、数量/体积上限）。
- 自检新增压缩包导入、菜单栏检查。

### Changed
- `ImageToPDF_Studio.spec` 入口改为 `src/app.py`，图标与运行时资源改为 `assets/`，显式收集 py7zr / pyzipper / Cryptodome 子模块。
- `build.bat` 打包后自动调用 `scripts/make_source_bundle.py`，保证版本与源码交付物同步。
- 整合版单文件源码现在内联 3 个模块（core / archive / app）。

## [1.5] - 2026-11-05

### Added
- 「随便看看 · 最小最快」一键档（96 ppi / 质量 55 / 最长边 210 mm / 单页 ≤1 MP）。
- 源码交付物：完整工程 zip + 整合版单文件源码 + 源码说明。
- 版本更新自动同步源码机制：版本号唯一来源 `APP_VER`，`build.bat` 打包后自动生成源码包。

## [1.4] - 2026-11-05

### Added
- 「阅读流畅优先」预处理：统一转 baseline JPEG，PDF 内不再出现 FlateDecode 图像对象。
- 「单页图像像素上限」与「移动端一键优化」按钮。

### Changed
- 修复「最小体积 ≠ 最快渲染」：Flate 单位解码成本约为 DCT 的 8 倍。

## [1.3] - 2026-11-05

### Fixed
- 强压缩后移动端显示异常：强制 baseline JPEG（禁用 progressive）、照片不再做 256 色量化、目标 ppi 下限 72。

## [1.2] - 2026-11-04

### Added
- PDF 口令保护（AES-256 / AES-128 / RC4-128）与权限控制。

## [1.1] - 2026-11-04

### Added
- 左侧「预览小图 / 文字详细信息」视图切换。

## [1.0] - 2026-11-04

### Added
- 首个版本：按图片实际尺寸生成 PDF、排序与右键置顶、Acrobat DC 式压缩、独立 EXE。
