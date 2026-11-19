# -*- mode: python ; coding: utf-8 -*-
# 环境内的文件保护会拦截 PyInstaller 对成品 exe 的 'wb' 覆写（仅用于写 PE 时间戳/校验和）。
# 这两步为可选后处理，跳过不影响可执行文件运行。
import PyInstaller.utils.win32.winutils as _winutils
_winutils.set_exe_build_timestamp = lambda exe_path, timestamp: None
_winutils.update_exe_pe_checksum = lambda exe_path: None
import os
from PyInstaller.utils.hooks import collect_submodules

# 不要 collect_dynamic_libs('pymupdf')：hook 已自动收集 mupdfcpp64.dll，
# 再收集一次会在 CArchive 里出现两份，EXE 直接多 11 MB。
binaries = []

# 压缩包依赖含动态导入与 C 扩展，显式收集子模块
_hidden = (['pymupdf']
           + collect_submodules('py7zr')
           + collect_submodules('pyzipper')
           # Cryptodome 的自检模块几 MB，纯测试用，运行时不需要
           + [m for m in collect_submodules('Cryptodome')
              if 'SelfTest' not in m and '.Test' not in m])

a = Analysis(
    ['src/app.py'],
    pathex=['src'],
    binaries=binaries,
    datas=[('assets/app.ico', 'assets'), ('assets/app.png', 'assets')],
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'onnxruntime', 'networkx', 'pandas', 'matplotlib', 'scipy', 'tkinter',
              'setuptools', 'PIL.AvifImagePlugin', 'PIL._avif',
              'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineCore', 'PySide6.QtQml',
              'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.Qt3DCore',
              'PySide6.QtMultimedia', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
              'PySide6.QtCharts', 'PySide6.QtDataVisualization'],
    noarchive=False,
    optimize=0,
)
# PySide6 hook 会连带收集本程序用不到的 Qt 动态库与图片格式插件（excludes 只管 Python 模块）。
# 这里按文件名剔除，约可省 11 MB；qwindows / qico / qpng 等必需的保留。
_DROP_NAMES = {
    'opengl32sw.dll',                                   # 软件 OpenGL 后备，约 7.3 MB
    'qt6quick.dll', 'qt6qml.dll', 'qt6qmlmodels.dll',   # QML / Quick 不用
    'qt6pdf.dll', 'qt6pdfwidgets.dll',                  # PDF 显示不用
    'qt6virtualkeyboard.dll', 'qt6svg.dll', 'qt6opengl.dll',
    'qdirect2d.dll',                                    # 平台插件只留 qwindows
    'qtiff.dll', 'qwebp.dll', 'qjpeg.dll', 'qgif.dll', 'qbmp.dll', 'qpbm.dll',
}
def _keep_bin(entry):
    full = str(entry[0]).replace("/", "\\").lower()
    name = os.path.basename(full)
    if name not in _DROP_NAMES and not name.startswith('_avif'):
        # 保留 pymupdf 包内那一份；根目录的同名 DLL 是重复收集，白占 13.8 MB
        if name == 'mupdfcpp64.dll' and not full.startswith('pymupdf\\'):
            return False
        return True
    return False

a.binaries = [e for e in a.binaries if _keep_bin(e)]

# PyMuPDF 2.x 的 layout 模块会附带 ~40 MB ONNX 文档布局/表格识别模型，
# 本程序只用核心 DCT/Flate 封装，完全用不到；excludes 只管 Python 模块，数据要手动剔除。
def _keep_data(entry):
    name = str(entry[0]).replace("/", "\\").lower()
    return ("onnx" not in name
            and "pymupdf\\layout" not in name
            and not name.endswith(".onnx"))

a.datas = [e for e in a.datas if _keep_data(e)]
a.binaries = [e for e in a.binaries if _keep_data(e)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ImageToPDF_Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # onefile 的 CArchive 已 zlib 压缩；UPX 后的高熵数据反而让 EXE 更大
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/app.ico'],
)
