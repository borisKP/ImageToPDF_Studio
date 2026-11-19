# 开发与发版约定

## 环境

- Windows x64，Python 3.10+（本项目在 3.13 构建）
- `python -m pip install -r requirements.txt`

## 目录约定

| 目录 | 放什么 |
|---|---|
| `src/` | 可运行的模块：`app.py`（界面与入口）、`core.py`（转换引擎）、`archive.py`（压缩包导入） |
| `tests/` | 回归测试，运行前会把 `src/` 加入 `sys.path` |
| `docs/` | 使用者说明 `使用说明.html`、源码说明 `源码说明.html` |
| `assets/` | 图标 `app.ico` / `app.png` |
| `scripts/` | 诊断脚本、图标生成、源码包生成器 |
| `.github/workflows/` | CI |
| `dist/`、`源码交付/` | 构建产物，不入库 |

`src/` 内模块使用扁平导入（`import core` / `import archive`），PyInstaller 通过 `pathex=['src']` 解析。
若要把 `src/` 改成 Python 包，需同步修改所有导入、`ImageToPDF_Studio.spec` 与 `scripts/make_source_bundle.py` 的内联逻辑。

## 测试

```bash
python tests/test_core.py
python tests/test_archive.py
QT_QPA_PLATFORM=offscreen python tests/test_gui.py
python src/app.py --selftest
```

改动涉及 PDF 编码时，建议同时跑 `scripts/diagnose_compression.py` 检查产物是否仍为 baseline JPEG。

## 发版（重要）

1. **只改一处版本号**：`src/app.py` 的 `APP_VER`。禁止在别处手写硬编码版本。
2. 在 `CHANGELOG.md` 与 `docs/源码说明.html` 的「版本演进」表补一行本次更新内容。
3. 运行 `build.bat`。它会：
   - 安装依赖；
   - 用 `ImageToPDF_Studio.spec` 打包 `dist/ImageToPDF_Studio.exe`；
   - 调用 `scripts/make_source_bundle.py`，自动同步 `README.md` / `requirements.txt` / 两份 HTML 说明 / `dist/使用说明.html` 的版本号与页脚日期，重建 `源码交付/ImageToPDF_整合版源码.py` 与 `源码交付/ImageToPDF_源码_v<版本>.zip`。
4. 验证：
   ```bash
   dist/ImageToPDF_Studio.exe --selftest    # 检查 _selftest.txt 全绿
   python tests/test_core.py
   python tests/test_archive.py
   QT_QPA_PLATFORM=offscreen python tests/test_gui.py
   ```
5. 交付 `dist/ImageToPDF_Studio.exe`、`dist/使用说明.html` 与 `源码交付/` 三个产物。

> **不允许只更新 EXE 而不重跑源码生成器。** 若生成器提示「版本演进表缺少当前版本」，先补表再发版。

## 打包注意事项

`ImageToPDF_Studio.spec` 顶部把 `set_exe_build_timestamp` / `update_exe_pe_checksum` 置为 no-op，用于绕开构建机对成品 exe 的 `open(exe,'wb')` 写入保护。这两步是可选后处理，跳过不影响 EXE 运行；在其他机器上可删掉这 3 行。

## 打包体积（v1.8 起）

`ImageToPDF_Studio.spec` 里的过滤规则是有意为之，勿轻易删：

- `collect_dynamic_libs('pymupdf')` 会让 `mupdfcpp64.dll` 收两份（+13.8 MB）。
- PySide6 hook 会连带收集 QML / Quick / PDF / OpenGL / SVG 等 DLL 与多余 imageformats 插件，按文件名剔除。
- PyMuPDF 2.x 的 `pymupdf/layout` 附带约 40 MB ONNX 模型，`excludes` 管不到数据文件，需在 `a.datas` / `a.binaries` 里按路径过滤。
- `upx=False`：onefile 已 zlib 压缩，UPX 反而使 EXE 变大。

改完后可运行 `python scripts/analyze_exe_size.py` 核对各组件体积；目标 ≤ 55 MB。

若构建机系统盘空间不足，可把依赖装到其它盘后用 `PYTHONPATH` 指向它，并把 `TMPDIR` / `TEMP` / `TMP` 与 `PYINSTALLER_CONFIG_DIR` 指到空间充足的盘。

## 开源信息

- 许可证：MIT（`LICENSE`）。更换许可证时同步修改 `src/app.py` 的 `LICENSE_NAME`。
- 项目主页已写入 `src/app.py` 的 `PROJECT_URL`：`https://github.com/borisKP/ImageToPDF_Studio`。迁移仓库时同步更新该常量与 `README.md` 的仓库地址。
- 发版由维护者本地执行 `git push`；推送前务必运行 `build.bat` 同步源码交付物。
