# -*- coding: utf-8 -*-
"""ImageToPDF Studio — 图形界面入口"""
from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import time
import traceback
import zipfile
from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal, QObject, QSize, QThreadPool, QRunnable, QUrl, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage, QAction, QDesktopServices, QFont, QColor, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QListWidget, QListWidgetItem, QAbstractItemView, QPushButton, QLabel,
    QGroupBox, QComboBox, QCheckBox, QLineEdit, QSpinBox, QDoubleSpinBox,
    QSlider, QRadioButton, QButtonGroup, QFileDialog, QMessageBox, QProgressBar,
    QScrollArea, QSplitter, QMenu, QDialog, QFrame, QSizePolicy, QToolBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QStackedWidget, QInputDialog,
)

from PIL import Image
import core
import archive

APP_NAME = "ImageToPDF Studio"
APP_VER = "1.8"
LICENSE_NAME = "MIT License"
PROJECT_URL = "https://github.com/borisKP/ImageToPDF_Studio"
BUILD_DATE = "2026-11-09"


def resource_path(rel: str) -> str:
    """兼容源码运行与 PyInstaller onefile 运行时的资源路径。"""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 仓库根
    return os.path.join(base, rel)


QUALITY_LABELS = [(0, 30, "最低"), (30, 50, "低"), (50, 70, "中"),
                  (70, 88, "高"), (88, 101, "最高")]

QSS = """
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 12px; color: #1f2937; }
QMainWindow, QDialog { background: #f4f6fa; }
QGroupBox {
    border: 1px solid #e2e8f0; border-radius: 8px; margin-top: 12px;
    background: #ffffff; padding: 10px 8px 8px 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #0f172a; font-weight: 600; }
QLabel#hint { color: #64748b; font-size: 11px; }
QLabel#section { color: #334155; font-weight: 600; }
QPushButton {
    background: #ffffff; border: 1px solid #d7dfea; border-radius: 6px;
    padding: 6px 12px; color: #1e293b;
}
QPushButton:hover { background: #eef4ff; border-color: #9bbcf7; }
QPushButton:pressed { background: #e0ebff; }
QPushButton:disabled { color: #9aa5b4; background: #f1f3f6; }
QPushButton#primary { background: #2563eb; border: 1px solid #2563eb; color: #ffffff; font-weight: 600; padding: 8px 18px; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#primary:disabled { background: #a9bff0; border-color: #a9bff0; color: #f8fafc; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #d7dfea; border-radius: 6px;
    padding: 5px 7px; selection-background-color: #bfdbfe;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: #60a5fa; }
QComboBox::drop-down { border: none; width: 18px; }
QListWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 6px; }
QListWidget::item { border-radius: 6px; padding: 4px; color: #334155; }
QListWidget::item:selected { background: #dbeafe; color: #1e3a8a; }
QListWidget::item:hover { background: #f1f5fd; }
QTableWidget { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px;
    gridline-color: #eef2f7; selection-background-color: #dbeafe; selection-color: #1e3a8a; }
QTableWidget::item { padding: 3px 6px; }
QHeaderView::section { background: #f1f5f9; border: none; border-right: 1px solid #e8edf4;
    border-bottom: 1px solid #dfe6ef; padding: 6px 8px; color: #334155; font-weight: 600; }
QProgressBar { border: 1px solid #e2e8f0; border-radius: 6px; background: #eef2f7; height: 16px; text-align: center; }
QProgressBar::chunk { background: #3b82f6; border-radius: 5px; }
QSlider::groove:horizontal { height: 5px; background: #e2e8f0; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; background: #2563eb; border-radius: 7px; margin: -5px 0; }
QCheckBox, QRadioButton { spacing: 6px; }
QToolBar { background: #ffffff; border-bottom: 1px solid #e2e8f0; spacing: 4px; padding: 6px; }
QStatusBar { color: #475569; }
QSplitter::handle { background: #e2e8f0; }
QMenuBar { background: #ffffff; border-bottom: 1px solid #e2e8f0; padding: 3px 6px; }
QMenuBar::item { padding: 5px 12px; border-radius: 5px; color: #1e293b; }
QMenuBar::item:selected { background: #e8f0fe; color: #1e3a8a; }
QMenu { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 26px 6px 18px; border-radius: 4px; }
QMenu::item:selected { background: #dbeafe; color: #1e3a8a; }
QMenu::separator { height: 1px; background: #e8edf4; margin: 4px 8px; }
QLabel#version { color: #64748b; padding-right: 12px; font-size: 11px; }
QLabel#aboutTitle { font-size: 19px; font-weight: 700; color: #0f172a; }
QLabel#aboutBody { color: #475569; font-size: 12px; }
"""


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def quality_text(q: int) -> str:
    for lo, hi, t in QUALITY_LABELS:
        if lo <= q < hi:
            return t
    return "中"


# ---------------------------------------------------------------- 缩略图任务

class ThumbSignals(QObject):
    done = Signal(str, QImage)


class ThumbTask(QRunnable):
    def __init__(self, path: str, signals: ThumbSignals):
        super().__init__()
        self.path = path
        self.signals = signals

    def run(self):
        try:
            with Image.open(self.path) as src:
                try:
                    src.seek(0)
                except Exception:
                    pass
                im = src.convert("RGB")
                im.thumbnail((168, 118), Image.Resampling.LANCZOS)
                w, h = im.size
                canvas = Image.new("RGB", (180, 132), "#ffffff")
                canvas.paste(im, ((180 - w) // 2, (132 - h) // 2))
                qimg = QImage(canvas.tobytes(), 180, 132, QImage.Format.Format_RGB888).copy()
                self.signals.done.emit(self.path, qimg)
        except Exception:
            pass


# ---------------------------------------------------------------- 转换线程

class ConvertWorker(QThread):
    progressed = Signal(int, int, str)
    succeeded = Signal(dict)
    failed = Signal(str)

    def __init__(self, paths, out_path, settings):
        super().__init__()
        self.paths = list(paths)
        self.out_path = out_path
        self.settings = settings
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            result = core.convert(
                self.paths, self.out_path, self.settings,
                progress=lambda a, b, m: self.progressed.emit(a, b, m),
                should_cancel=lambda: self._cancel,
            )
            self.succeeded.emit(result)
        except Exception as e:
            self.failed.emit(f"{e}\n\n{traceback.format_exc(limit=3)}")


# ---------------------------------------------------------------- 图片列表

class ImageList(QListWidget):
    filesDropped = Signal(list)
    reordered = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(180, 132))
        self.setGridSize(QSize(200, 178))
        self.setSpacing(8)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAcceptDrops(True)
        self.setWordWrap(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.itemDoubleClicked.connect(self._preview)

    def dropEvent(self, event):
        md = event.mimeData()
        if md.hasUrls() and event.source() is not self:
            paths = [u.toLocalFile() for u in md.urls()]
            self.filesDropped.emit(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)
        QTimer.singleShot(0, self.reordered.emit)

    def _preview(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path or not os.path.exists(path):
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(os.path.basename(path))
        dlg.resize(900, 660)
        lay = QVBoxLayout(dlg)
        lab = QLabel()
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(path)
        if not pix.isNull():
            lab.setPixmap(pix.scaled(860, 610, Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))
        lay.addWidget(lab)
        dlg.exec()


# ---------------------------------------------------------------- 主窗口

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VER}   —   按图片原尺寸生成 PDF")
        self.resize(1240, 800)
        self.setMinimumSize(1020, 660)
        self.setAcceptDrops(True)
        self.worker = None
        self.icons = {}       # path -> QIcon，重排时复用，避免重新解码
        self.info_cache = {}  # path -> ((size, mtime), 图片元信息)
        self._syncing = False # 两个视图之间选中同步的防重入标志
        self.temp_dirs = []          # 压缩包解压出的临时目录，关闭窗口时清理
        self.archive_password = None # 本次会话记住的压缩包密码
        self.thumb_signals = ThumbSignals()
        self.thumb_signals.done.connect(self.on_thumb_ready)
        QThreadPool.globalInstance().setMaxThreadCount(4)
        self.last_output = ""
        self._build_ui()
        self._refresh_status()

    # ------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        tb = QToolBar()
        tb.setMovable(False)
        for text, slot, tip in [
            ("添加图片", self.add_files, "选择任意数量的图片"),
            ("添加文件夹", self.add_folder, "导入整个文件夹内的图片"),
            ("添加压缩包", self.add_archives, "ZIP / 7Z / RAR，可带密码；直接把图片导入列表"),
            ("|", None, ""),
            ("移除选中", self.remove_selected, "从列表移除"),
            ("清空", self.clear_all, ""),
            ("|", None, ""),
            ("↑ 上移", lambda: self.move_selected(-1), ""),
            ("↓ 下移", lambda: self.move_selected(1), ""),
            ("置顶", self.pin_top, ""),
            ("反转顺序", self.reverse_order, ""),
        ]:
            if text == "|":
                tb.addSeparator()
            else:
                a = QAction(text, self)
                a.setToolTip(tip)
                a.triggered.connect(slot)
                tb.addAction(a)
        self.addToolBar(tb)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, 1)

        # 左：列表
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(12, 10, 6, 10)
        head = QHBoxLayout()
        self.count_label = QLabel("图片列表")
        self.count_label.setObjectName("section")
        head.addWidget(self.count_label)
        self.view_btn = QPushButton("切换为：详细信息")
        self.view_btn.setToolTip("左侧在「预览小图」与「文字详细信息（无缩略图）」之间切换")
        self.view_btn.clicked.connect(self.toggle_view)
        head.addWidget(self.view_btn)
        head.addStretch(1)
        head.addWidget(QLabel("排序："))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems([
            "文件名（自然 · 升序）", "文件名（自然 · 降序）", "文件名（字母 · 升序）",
            "修改时间（旧→新）", "修改时间（新→旧）", "文件大小（小→大）", "文件大小（大→小）",
            "扩展名", "当前手动顺序",
        ])
        self.sort_combo.setMinimumWidth(180)
        head.addWidget(self.sort_combo)
        sort_btn = QPushButton("应用排序")
        sort_btn.clicked.connect(self.apply_sort)
        head.addWidget(sort_btn)
        lv.addLayout(head)

        self.stack = QStackedWidget()
        self.lst = ImageList(self)
        self.lst.filesDropped.connect(self.add_paths)
        self.lst.reordered.connect(self.on_list_reordered)
        self.lst.customContextMenuRequested.connect(self.show_context_menu)
        self.lst.itemSelectionChanged.connect(self._refresh_status)
        self.stack.addWidget(self.lst)

        self.detail = QTableWidget(0, 9)
        self.detail.setHorizontalHeaderLabels([
            "#", "文件名", "格式", "像素尺寸", "DPI", "页面尺寸 (mm)",
            "文件大小", "修改时间", "所在路径",
        ])
        self.detail.verticalHeader().setVisible(False)
        self.detail.verticalHeader().setDefaultSectionSize(25)
        self.detail.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.detail.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.detail.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.detail.setAlternatingRowColors(True)
        self.detail.setShowGrid(False)
        self.detail.setWordWrap(False)
        self.detail.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        hh = self.detail.horizontalHeader()
        hh.setHighlightSections(False)
        for col, width in [(0, 42), (2, 62), (3, 105), (4, 78), (5, 125), (6, 92), (7, 132)]:
            self.detail.setColumnWidth(col, width)
        self.detail.setColumnWidth(1, 230)
        hh.setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        self.detail.itemSelectionChanged.connect(self.on_detail_selection)
        self.detail.customContextMenuRequested.connect(self.show_detail_context_menu)
        self.detail.doubleClicked.connect(self.on_detail_double_clicked)
        self.stack.addWidget(self.detail)
        lv.addWidget(self.stack, 1)

        self.tip_label = QLabel(
            "提示：可直接把图片/文件夹拖进窗口；列表内拖拽调整顺序；右键可置顶、上移、下移、置底；双击预览大图。")
        self.tip_label.setObjectName("hint")
        self.tip_label.setWordWrap(True)
        lv.addWidget(self.tip_label)
        splitter.addWidget(left)

        # 右：设置
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(6, 10, 12, 10)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        panel = QWidget()
        pv = QVBoxLayout(panel)
        pv.setSpacing(10)
        pv.addWidget(self._page_group())
        pv.addWidget(self._compress_group())
        pv.addWidget(self._output_group())
        pv.addWidget(self._security_group())
        pv.addWidget(self._archive_group())
        pv.addStretch(1)
        scroll.setWidget(panel)
        rv.addWidget(scroll)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([760, 420])

        # 底栏
        bottom = QFrame()
        bottom.setStyleSheet("QFrame{background:#ffffff;border-top:1px solid #e2e8f0;}")
        bl = QHBoxLayout(bottom)
        bl.setContentsMargins(14, 9, 14, 9)
        self.status = QLabel("")
        bl.addWidget(self.status, 1)
        self.prog = QProgressBar()
        self.prog.setFixedWidth(260)
        self.prog.setVisible(False)
        bl.addWidget(self.prog)
        self.open_btn = QPushButton("打开输出文件夹")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self.open_output_folder)
        bl.addWidget(self.open_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_convert)
        bl.addWidget(self.cancel_btn)
        self.go_btn = QPushButton("生成 PDF")
        self.go_btn.setObjectName("primary")
        self.go_btn.clicked.connect(self.start_convert)
        bl.addWidget(self.go_btn)
        root.addWidget(bottom)

        self._build_menu_bar()

    def _build_menu_bar(self):
        """顶部横栏菜单：文件 / 开始 / 视图 / 帮助，右侧常显版本号。"""
        mb = self.menuBar()

        def add(menu, text, slot, shortcut=None):
            act = QAction(text, self)
            if shortcut:
                act.setShortcut(shortcut)
            act.triggered.connect(slot)
            menu.addAction(act)
            return act

        m_file = mb.addMenu("文件(&F)")
        add(m_file, "添加图片…", self.add_files, "Ctrl+O")
        add(m_file, "添加文件夹…", self.add_folder, "Ctrl+Shift+O")
        add(m_file, "添加压缩包…（ZIP / 7Z / RAR）", self.add_archives, "Ctrl+Alt+O")
        add(m_file, "导入压缩包并直接生成 PDF", self.add_archives_and_convert)
        m_file.addSeparator()
        add(m_file, "清空列表", self.clear_all)
        m_file.addSeparator()
        add(m_file, "退出", self.close, "Ctrl+Q")

        m_start = mb.addMenu("开始(&S)")
        add(m_start, "生成 PDF", self.start_convert, "Ctrl+Return")
        add(m_start, "取消生成", self.cancel_convert)
        m_start.addSeparator()
        add(m_start, "上移选中", lambda: self.move_selected(-1), "Ctrl+Up")
        add(m_start, "下移选中", lambda: self.move_selected(1), "Ctrl+Down")
        add(m_start, "置顶", self.pin_top, "Ctrl+Home")
        add(m_start, "置底", self.pin_bottom, "Ctrl+End")
        add(m_start, "反转顺序", self.reverse_order)
        add(m_start, "应用排序", self.apply_sort)
        m_start.addSeparator()
        add(m_start, "移动端一键优化", self.apply_mobile_preset)
        add(m_start, "随便看看 · 最小最快", self.apply_casual_preset)

        m_view = mb.addMenu("视图(&V)")
        add(m_view, "切换：预览小图 / 文字详细信息", self.toggle_view, "Ctrl+T")

        m_help = mb.addMenu("帮助(&H)")
        add(m_help, "使用说明", self.show_help, "F1")
        m_help.addSeparator()
        add(m_help, f"关于 {APP_NAME}", self.show_about)

        ver = QLabel(f"v{APP_VER}")
        ver.setObjectName("version")
        mb.setCornerWidget(ver, Qt.Corner.TopRightCorner)

    def _page_group(self):
        g = QGroupBox("① 页面尺寸（每页跟随图片，不强制 A4）")
        v = QVBoxLayout(g)
        self.rb_image = QRadioButton("按图片实际尺寸（等同 Acrobat「保留原始尺寸」）")
        self.rb_image.setChecked(True)
        self.rb_paper = QRadioButton("统一纸张尺寸（图片等比居中适配）")
        bg = QButtonGroup(self)
        bg.addButton(self.rb_image)
        bg.addButton(self.rb_paper)
        v.addWidget(self.rb_image)
        v.addWidget(self.rb_paper)

        form = QGridLayout()
        form.setSpacing(6)
        r = 0
        form.addWidget(QLabel("尺寸依据"), r, 0)
        self.dpi_source = QComboBox()
        self.dpi_source.addItems(["读取图片自带 DPI", "固定 DPI（忽略元数据）"])
        form.addWidget(self.dpi_source, r, 1, 1, 2)
        r += 1
        form.addWidget(QLabel("默认 DPI"), r, 0)
        self.default_dpi = QDoubleSpinBox()
        self.default_dpi.setRange(24, 1200)
        self.default_dpi.setValue(96)
        self.default_dpi.setDecimals(0)
        form.addWidget(self.default_dpi, r, 1)
        form.addWidget(self._hint("元数据缺失时使用"), r, 2)
        r += 1
        form.addWidget(QLabel("固定 DPI"), r, 0)
        self.fixed_dpi = QDoubleSpinBox()
        self.fixed_dpi.setRange(24, 1200)
        self.fixed_dpi.setValue(150)
        self.fixed_dpi.setDecimals(0)
        form.addWidget(self.fixed_dpi, r, 1)
        form.addWidget(self._hint("px ÷ DPI × 72 = 页面 pt"), r, 2)
        r += 1
        form.addWidget(QLabel("最长边限制"), r, 0)
        self.max_edge = QComboBox()
        self.max_edge.addItems(["不限制", "297 mm（A4 长边）", "420 mm（A3 长边）", "自定义"])
        form.addWidget(self.max_edge, r, 1, 1, 2)
        r += 1
        form.addWidget(QLabel("自定义长边"), r, 0)
        self.max_edge_mm = QDoubleSpinBox()
        self.max_edge_mm.setRange(20, 5000)
        self.max_edge_mm.setValue(297)
        self.max_edge_mm.setDecimals(0)
        self.max_edge_mm.setSuffix(" mm")
        form.addWidget(self.max_edge_mm, r, 1)
        form.addWidget(self._hint("防止 72dpi 手机照生成巨页"), r, 2)
        r += 1
        form.addWidget(QLabel("纸张"), r, 0)
        self.paper = QComboBox()
        self.paper.addItems(list(core.PAPERS.keys()) + ["自定义"])
        form.addWidget(self.paper, r, 1, 1, 2)
        r += 1
        form.addWidget(QLabel("宽 × 高"), r, 0)
        self.paper_w = QDoubleSpinBox()
        self.paper_w.setRange(20, 2000)
        self.paper_w.setValue(210)
        self.paper_w.setSuffix(" mm")
        self.paper_h = QDoubleSpinBox()
        self.paper_h.setRange(20, 2000)
        self.paper_h.setValue(297)
        self.paper_h.setSuffix(" mm")
        fw = QWidget()
        fl = QHBoxLayout(fw)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.addWidget(self.paper_w)
        fl.addWidget(self.paper_h)
        form.addWidget(fw, r, 1, 1, 2)
        r += 1
        self.auto_rotate = QCheckBox("横图自动使用横向纸张")
        self.auto_rotate.setChecked(True)
        form.addWidget(self.auto_rotate, r, 0, 1, 3)
        r += 1
        form.addWidget(QLabel("页边距"), r, 0)
        self.margin = QDoubleSpinBox()
        self.margin.setRange(0, 100)
        self.margin.setValue(0)
        self.margin.setSuffix(" mm")
        form.addWidget(self.margin, r, 1)
        form.addWidget(self._hint("按图片尺寸模式下建议 0"), r, 2)
        v.addLayout(form)

        self.rb_image.toggled.connect(self._sync_enabled)
        self.dpi_source.currentIndexChanged.connect(self._sync_enabled)
        self.max_edge.currentIndexChanged.connect(self._sync_enabled)
        self.paper.currentIndexChanged.connect(self._sync_enabled)
        self._sync_enabled()
        # 页面设置变化时，文字详情里的「页面尺寸」列同步重算
        for sig in (self.rb_image.toggled, self.dpi_source.currentIndexChanged,
                    self.default_dpi.valueChanged, self.fixed_dpi.valueChanged,
                    self.max_edge.currentIndexChanged, self.max_edge_mm.valueChanged,
                    self.paper.currentIndexChanged, self.paper_w.valueChanged,
                    self.paper_h.valueChanged, self.auto_rotate.toggled,
                    self.margin.valueChanged):
            sig.connect(lambda *_: self.refresh_detail())
        return g

    def _compress_group(self):
        g = QGroupBox("② 压缩 / 图像优化（仿 Acrobat DC PDF 优化器）")
        v = QVBoxLayout(g)
        hl = QHBoxLayout()
        hl.addWidget(QLabel("预设档位"))
        self.preset = QComboBox()
        for key, (label, _) in core.PRESETS.items():
            self.preset.addItem(label, key)
        self.preset.addItem("自定义", "custom")
        self.preset.setCurrentIndex(1)  # 默认「屏幕阅读」
        hl.addWidget(self.preset, 1)
        v.addLayout(hl)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.mobile_btn = QPushButton("移动端一键优化")
        self.mobile_btn.setToolTip(
            "120 ppi / 质量 70 / 最长边 297mm / 统一 baseline JPEG / 单页 ≤4MP")
        self.mobile_btn.clicked.connect(self.apply_mobile_preset)
        btn_row.addWidget(self.mobile_btn)
        self.casual_btn = QPushButton("随便看看 · 最小最快")
        self.casual_btn.setObjectName("primary")
        self.casual_btn.setToolTip(
            "96 ppi / 质量 55 / 最长边 210mm / 统一 baseline JPEG / 单页 ≤1MP；"
            "只求能快速翻看，画质够用即可")
        self.casual_btn.clicked.connect(self.apply_casual_preset)
        btn_row.addWidget(self.casual_btn)
        v.addLayout(btn_row)

        form = QGridLayout()
        form.setSpacing(6)
        r = 0
        form.addWidget(QLabel("目标分辨率"), r, 0)
        self.target_dpi = QSpinBox()
        self.target_dpi.setRange(72, 1200)   # 下限 72 ppi：再低移动端拉伸后不可读
        self.target_dpi.setValue(150)
        self.target_dpi.setSuffix(" ppi")
        form.addWidget(self.target_dpi, r, 1)
        self.dpi_hint = self._hint("屏幕 150 / 印刷 300")
        form.addWidget(self.dpi_hint, r, 2)
        self.target_dpi.valueChanged.connect(self._update_dpi_hint)
        r += 1
        form.addWidget(QLabel("仅高于此值时"), r, 0)
        self.trigger_dpi = QSpinBox()
        self.trigger_dpi.setRange(24, 2000)
        self.trigger_dpi.setValue(225)
        self.trigger_dpi.setSuffix(" ppi")
        form.addWidget(self.trigger_dpi, r, 1)
        form.addWidget(self._hint("Acrobat: for images above"), r, 2)
        r += 1
        form.addWidget(QLabel("JPEG 质量"), r, 0)
        self.quality = QSlider(Qt.Orientation.Horizontal)
        self.quality.setRange(1, 100)
        self.quality.setValue(75)
        form.addWidget(self.quality, r, 1)
        self.quality_lbl = QLabel("75 · 高")
        form.addWidget(self.quality_lbl, r, 2)
        self.quality.valueChanged.connect(
            lambda v: self.quality_lbl.setText(f"{v} · {quality_text(v)}"))
        r += 1
        form.addWidget(QLabel("重采样算法"), r, 0)
        self.resample = QComboBox()
        self.resample.addItems(["双立方（渐变最平滑，推荐）", "平均（平坦色块）", "次取样（线稿最快）"])
        form.addWidget(self.resample, r, 1, 1, 2)
        v.addLayout(form)

        self.cb_smaller = QCheckBox("仅在体积变小时才替换（不反向增大文件）")
        self.cb_smaller.setChecked(True)
        self.cb_gray = QCheckBox("灰度图自动转灰度（进一步减小）")
        self.cb_gray.setChecked(True)
        self.cb_meta = QCheckBox("剥离 EXIF / ICC 元数据")
        self.cb_meta.setChecked(True)
        self.cb_alpha = QCheckBox("透明背景转白底（可用 JPEG）")
        self.cb_alpha.setChecked(True)
        self.cb_graphics = QCheckBox("图形类图片自动选用调色板 PNG（照片不会走量化）")
        self.cb_graphics.setChecked(True)
        for cb in (self.cb_smaller, self.cb_gray, self.cb_meta, self.cb_alpha, self.cb_graphics):
            v.addWidget(cb)

        self.cb_reading = QCheckBox(
            "阅读流畅优先：先把所有图片统一转成 baseline JPEG（PDF 内不再有 Flate 图像）")
        v.addWidget(self.cb_reading)
        mp_row = QHBoxLayout()
        mp_row.addWidget(QLabel("单页图像像素上限"))
        self.max_mp = QDoubleSpinBox()
        self.max_mp.setRange(0, 40)
        self.max_mp.setValue(4.0)
        self.max_mp.setDecimals(1)
        self.max_mp.setSuffix(" MP")
        self.max_mp.setSpecialValueText("不限制")
        mp_row.addWidget(self.max_mp)
        mp_row.addWidget(self._hint("4 MP ≈ 12 MB 解码内存；移动端建议 3–4 MP"), 1)
        v.addLayout(mp_row)
        self.cb_reading.toggled.connect(lambda *_: self._sync_reading_enabled())
        self._sync_reading_enabled()

        note = QLabel("逻辑：按页面实际 ppi 双立方下采样 → baseline JPEG（不用渐进式，兼容移动端）"
                      "→ 仅图形类图片尝试调色板 PNG → 与无损流比体积取小者。页面物理尺寸不变；"
                      "想再缩小，优先用「最长边限制」缩小页面，而不是把 ppi 压到 72 以下。")
        note.setObjectName("hint")
        note.setWordWrap(True)
        v.addWidget(note)
        self.preset.currentIndexChanged.connect(self.on_preset_changed)
        self.on_preset_changed()
        self._sync_compress_enabled()
        return g

    def _output_group(self):
        g = QGroupBox("③ 输出位置与文件名")
        v = QGridLayout(g)
        v.setSpacing(7)
        v.addWidget(QLabel("保存目录"), 0, 0)
        self.out_dir = QLineEdit()
        self.out_dir.setText(os.path.join(os.path.expanduser("~"), "Desktop"))
        v.addWidget(self.out_dir, 0, 1)
        b1 = QPushButton("浏览…")
        b1.clicked.connect(self.choose_dir)
        v.addWidget(b1, 0, 2)
        v.addWidget(QLabel("文件名"), 1, 0)
        self.out_name = QLineEdit()
        self.out_name.setText("图片合集_" + datetime.now().strftime("%Y%m%d_%H%M"))
        v.addWidget(self.out_name, 1, 1, 1, 2)
        self.cb_bookmark = QCheckBox("按文件名生成 PDF 书签（目录）")
        self.cb_bookmark.setChecked(True)
        v.addWidget(self.cb_bookmark, 2, 0, 1, 3)
        v.addWidget(self._hint("输出为单个 PDF，图片张数 = 页数；文件不存在时自动建目录"), 3, 0, 1, 3)
        return g

    def _security_group(self):
        g = QGroupBox("④ PDF 密码与权限")
        v = QVBoxLayout(g)
        self.cb_encrypt = QCheckBox("启用密码保护（打开 PDF 必须输入口令）")
        v.addWidget(self.cb_encrypt)

        form = QGridLayout()
        form.setSpacing(6)
        r = 0
        form.addWidget(QLabel("打开密码"), r, 0)
        self.pw_user = QLineEdit()
        self.pw_user.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_user.setPlaceholderText("必填 · 打开 PDF 时输入")
        form.addWidget(self.pw_user, r, 1, 1, 2)
        r += 1
        form.addWidget(QLabel("确认密码"), r, 0)
        self.pw_confirm = QLineEdit()
        self.pw_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_confirm.setPlaceholderText("再输入一次")
        form.addWidget(self.pw_confirm, r, 1, 1, 2)
        r += 1
        form.addWidget(QLabel("所有者密码"), r, 0)
        self.pw_owner = QLineEdit()
        self.pw_owner.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_owner.setPlaceholderText("可选 · 留空则与打开密码相同")
        form.addWidget(self.pw_owner, r, 1, 1, 2)
        r += 1
        self.cb_show_pw = QCheckBox("显示密码")
        form.addWidget(self.cb_show_pw, r, 1)
        self.pw_hint = QLabel("")
        self.pw_hint.setObjectName("hint")
        form.addWidget(self.pw_hint, r, 2)
        r += 1
        form.addWidget(QLabel("加密方式"), r, 0)
        self.enc_method = QComboBox()
        for key, label in core.ENCRYPTION_LABELS.items():
            self.enc_method.addItem(label, key)
        form.addWidget(self.enc_method, r, 1, 1, 2)
        v.addLayout(form)

        lab = QLabel("允许的操作（取消勾选 = 禁用相应权限）")
        lab.setObjectName("section")
        v.addWidget(lab)
        self.sec_print = QCheckBox("打印")
        self.sec_print_hq = QCheckBox("高质量打印")
        self.sec_copy = QCheckBox("复制文本 / 图像")
        self.sec_modify = QCheckBox("修改内容 / 页面组装")
        self.sec_annotate = QCheckBox("注释 / 填写表单")
        grid = QGridLayout()
        for i, cb in enumerate((self.sec_print, self.sec_print_hq, self.sec_copy,
                                self.sec_modify, self.sec_annotate)):
            cb.setChecked(True)
            grid.addWidget(cb, i // 2, i % 2)
        v.addLayout(grid)

        note = QLabel("打开密码是硬保护；权限限制取决于阅读器是否遵守标准，部分工具可绕过。"
                      "忘记密码无法恢复。旧版移动阅读器可能不支持 AES-256，若移动端白页，"
                      "改用 AES-128 / RC4-128 或不加密。")
        note.setObjectName("hint")
        note.setWordWrap(True)
        v.addWidget(note)

        self.cb_encrypt.toggled.connect(lambda *_: self._sync_security_enabled())
        self.cb_show_pw.toggled.connect(self._toggle_pw_echo)
        self.pw_user.textChanged.connect(self._update_pw_hint)
        self._sync_security_enabled()
        return g

    def _archive_group(self):
        g = QGroupBox("⑤ 压缩包解压上限")
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        row.addWidget(QLabel("解压总体积上限"))
        self.archive_limit_gb = QDoubleSpinBox()
        self.archive_limit_gb.setRange(0, 100)
        self.archive_limit_gb.setDecimals(1)
        self.archive_limit_gb.setSingleStep(0.5)
        self.archive_limit_gb.setValue(1.0)
        self.archive_limit_gb.setSuffix(" GB")
        self.archive_limit_gb.setSpecialValueText("不限制")
        self.archive_limit_gb.setToolTip("设为 0（不限制）可完整解压任意大小的压缩包")
        row.addWidget(self.archive_limit_gb)
        row.addStretch(1)
        v.addLayout(row)

        self.cb_archive_ask = QCheckBox("超限时弹窗询问是否继续（关闭则直接中止）")
        self.cb_archive_ask.setChecked(True)
        v.addWidget(self.cb_archive_ask)

        quick = QHBoxLayout()
        quick.addWidget(QLabel("快捷："))
        for label, val in (("1 GB", 1.0), ("3 GB", 3.0), ("10 GB", 10.0),
                           ("不限制", 0.0)):
            b = QPushButton(label)
            b.clicked.connect(lambda _=False, x=val: self.archive_limit_gb.setValue(x))
            quick.addWidget(b)
        v.addLayout(quick)

        note = QLabel(
            "超过上限时不再自动终止：默认弹窗问「继续 / 中止」，选继续即完整解压；"
            "也可把上限调高或设为「不限制」。单文件 100 MB、最多 500 张仍固定。"
            "RAR 需本机安装 7-Zip 或 WinRAR。")
        note.setObjectName("hint")
        note.setWordWrap(True)
        v.addWidget(note)
        return g

    def archive_limit_bytes(self) -> int:
        """0 = 不限制；其余按 GB 换算成字节。"""
        return int(float(self.archive_limit_gb.value()) * 1024 ** 3)

    def _on_archive_limit(self, total: int, limit: int) -> bool:
        """解压超限时由用户决定；一次导入只弹一次。"""
        if not self.cb_archive_ask.isChecked():
            return False
        r = QMessageBox.question(
            self, "解压体积超过上限",
            f"该压缩包已解压 {total / 1024 ** 3:.2f} GB，超过设定上限 "
            f"{limit / 1024 ** 3:.1f} GB。\n\n"
            "可能是压缩包炸弹，也可能只是正常的大图包。\n是否继续解压？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        return r == QMessageBox.StandardButton.Yes

    def _sync_security_enabled(self):
        on = self.cb_encrypt.isChecked()
        for w in (self.pw_user, self.pw_confirm, self.pw_owner, self.enc_method,
                  self.sec_print, self.sec_print_hq, self.sec_copy, self.sec_modify,
                  self.sec_annotate, self.cb_show_pw):
            w.setEnabled(on)

    def _toggle_pw_echo(self, show):
        mode = (QLineEdit.EchoMode.Normal if show
                else QLineEdit.EchoMode.Password)
        for w in (self.pw_user, self.pw_confirm, self.pw_owner):
            w.setEchoMode(mode)

    def _update_pw_hint(self, text):
        if not text:
            self.pw_hint.setText("")
        elif len(text) < 6:
            self.pw_hint.setText("偏短，建议 ≥ 8 位")
        elif len(text) >= 12:
            self.pw_hint.setText("长度良好")
        else:
            self.pw_hint.setText("长度中等")

    def _update_dpi_hint(self, v):
        self.dpi_hint.setText("低于 96 ppi：移动端放大后明显模糊" if v < 96
                              else "屏幕 150 / 印刷 300")

    def _sync_reading_enabled(self):
        self.max_mp.setEnabled(self.cb_reading.isChecked())

    def apply_mobile_preset(self):
        """一键：缩小页面 + 统一 baseline JPEG 预处理 + 限制单页解码内存。"""
        self.preset.setCurrentIndex(5)      # 自定义
        self.target_dpi.setValue(120)
        self.trigger_dpi.setValue(180)
        self.quality.setValue(70)
        self.resample.setCurrentIndex(0)
        self.cb_reading.setChecked(True)
        self.max_mp.setValue(4.0)
        self.max_edge.setCurrentIndex(1)    # 最长边 297 mm
        if self.cb_encrypt.isChecked() and self.enc_method.currentIndex() == 0:
            self.enc_method.setCurrentIndex(1)  # AES-128，兼容旧移动阅读器
        self.status.setText(
            "已应用移动端优化：120 ppi / 质量70 / 最长边297mm / 统一 baseline JPEG / 单页≤4MP")
        QTimer.singleShot(6000, self._refresh_status)

    def apply_casual_preset(self):
        """一键「随便看看」：把图片降维到图片网站展示副本级别，只求快速翻看。"""
        self.preset.setCurrentIndex(5)      # 自定义
        self.target_dpi.setValue(96)
        self.trigger_dpi.setValue(150)
        self.quality.setValue(55)
        self.resample.setCurrentIndex(0)
        self.cb_reading.setChecked(True)
        self.max_mp.setValue(1.0)
        self.max_edge.setCurrentIndex(3)    # 自定义长边
        self.max_edge_mm.setValue(210)      # A5 长边，页面小、翻页快
        self.cb_smaller.setChecked(False)
        if self.cb_encrypt.isChecked() and self.enc_method.currentIndex() == 0:
            self.enc_method.setCurrentIndex(1)  # AES-128，兼容旧移动阅读器
        self.status.setText(
            "已应用「随便看看」：96 ppi / 质量55 / 最长边210mm / 统一 baseline JPEG / 单页≤1MP")
        QTimer.singleShot(6000, self._refresh_status)

    def _hint(self, text):
        lab = QLabel(text)
        lab.setObjectName("hint")
        return lab

    # ------------------------------------------------------------ 视图切换 / 文字详细信息
    def toggle_view(self):
        """左侧：预览小图 ⇄ 纯文字详细信息（不加载缩略图）。"""
        if self.stack.currentIndex() == 0:
            self.stack.setCurrentIndex(1)
            self.view_btn.setText("切换为：预览小图")
            self.tip_label.setText(
                "详细信息模式：纯文字、不显示预览图。列含像素尺寸、DPI、按当前设置算出的实际页面尺寸、"
                "体积与修改时间；右键同样可置顶 / 移动 / 排序 / 移除，双击预览大图。")
            self.refresh_detail(force=True)
        else:
            self.stack.setCurrentIndex(0)
            self.view_btn.setText("切换为：详细信息")
            self.tip_label.setText(
                "提示：可直接把图片/文件夹拖进窗口；列表内拖拽调整顺序；右键可置顶、上移、下移、置底；双击预览大图。")
            self.reload_icons()
        self._refresh_status()

    def reload_icons(self):
        """从文字详情切回缩略图时，补载缺失的预览图（已缓存的直接复用）。"""
        for i, p in enumerate(self.current_paths()):
            it = self.lst.item(i)
            if it is None:
                continue
            if p in self.icons:
                it.setIcon(self.icons[p])
            else:
                it.setIcon(QIcon())
                QThreadPool.globalInstance().start(ThumbTask(p, self.thumb_signals))

    def _file_info(self, path):
        """只读图片头取元信息，按 (体积, 修改时间) 缓存。"""
        try:
            st = os.stat(path)
            key = (st.st_size, int(st.st_mtime))
        except OSError:
            return None
        hit = self.info_cache.get(path)
        if hit and hit[0] == key:
            return hit[1]
        try:
            with Image.open(path) as im:
                w, h = im.size
                dpi = core.get_dpi(im)
                fmt = (im.format or os.path.splitext(path)[1][1:] or "?").upper()
            if fmt == "JPEG":
                fmt = "JPG"
        except Exception:
            w, h, dpi, fmt = 0, 0, None, "?"
        info = (w, h, dpi, fmt, st.st_size, st.st_mtime)
        self.info_cache[path] = (key, info)
        return info

    def refresh_detail(self, force=False):
        """文字视图始终以缩略图列表的顺序为唯一数据源。"""
        if self._syncing or (not force and self.stack.currentIndex() != 1):
            return
        self._syncing = True
        self.detail.blockSignals(True)
        try:
            paths = self.current_paths()
            try:
                st = self.build_settings()
            except Exception:
                st = core.ConvertSettings()
            self.detail.setRowCount(len(paths))
            for i, p in enumerate(paths):
                info = self._file_info(p)
                if info is None:
                    continue
                w, h, dpi, fmt, size, mtime = info
                try:
                    pw, ph = core.compute_page_size(w, h, dpi, st)
                    page_txt = f"{pw / 72 * 25.4:.1f} × {ph / 72 * 25.4:.1f}"
                except Exception:
                    page_txt = "—"
                dpi_txt = f"{dpi[0]:.0f} × {dpi[1]:.0f}" if dpi else "—（用默认）"
                cells = [
                    f"{i + 1:02d}", os.path.basename(p), fmt,
                    f"{w} × {h}", dpi_txt, page_txt,
                    human_size(size),
                    datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                    os.path.dirname(p),
                ]
                for c, txt in enumerate(cells):
                    it = QTableWidgetItem(txt)
                    if c in (0, 3, 4, 5, 6):
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    if c == 8:
                        it.setToolTip(p)
                    self.detail.setItem(i, c, it)
        finally:
            self.detail.blockSignals(False)
            self._syncing = False

    def on_detail_selection(self):
        """文字视图选中同步到缩略图列表，工具栏与右键菜单共用同一套逻辑。"""
        if self._syncing:
            return
        self._syncing = True
        try:
            rows = sorted({idx.row() for idx in self.detail.selectedIndexes()})
            self.lst.clearSelection()
            for r in rows:
                it = self.lst.item(r)
                if it:
                    it.setSelected(True)
        finally:
            self._syncing = False
        self._refresh_status()

    # ------------------------------------------------------------ 状态同步
    def _sync_enabled(self):
        img_mode = self.rb_image.isChecked()
        auto_dpi = self.dpi_source.currentIndex() == 0
        self.dpi_source.setEnabled(img_mode)
        self.default_dpi.setEnabled(img_mode and auto_dpi)
        self.fixed_dpi.setEnabled(img_mode and not auto_dpi)
        self.max_edge.setEnabled(img_mode)
        self.max_edge_mm.setEnabled(img_mode and self.max_edge.currentIndex() == 3)
        self.paper.setEnabled(not img_mode)
        self.paper_w.setEnabled(not img_mode and self.paper.currentText() == "自定义")
        self.paper_h.setEnabled(not img_mode and self.paper.currentText() == "自定义")
        self.auto_rotate.setEnabled(not img_mode)

    def _sync_compress_enabled(self):
        on = self.preset.currentData() != "lossless"
        for w in (self.target_dpi, self.trigger_dpi, self.quality, self.resample,
                  self.cb_smaller, self.cb_gray, self.cb_meta, self.cb_alpha, self.cb_graphics):
            w.setEnabled(on)

    def on_preset_changed(self):
        key = self.preset.currentData()
        if key in core.PRESETS:
            p = core.PRESETS[key][1]
            self.target_dpi.setValue(int(p.get("target_dpi", self.target_dpi.value())))
            self.trigger_dpi.setValue(int(p.get("trigger_dpi", self.trigger_dpi.value())))
            self.quality.setValue(int(p.get("quality", self.quality.value())))
        self._sync_compress_enabled()

    # ------------------------------------------------------------ 列表操作
    def current_paths(self):
        return [self.lst.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.lst.count())]

    def add_paths(self, paths, sort_new=False):
        existing = set(self.current_paths())
        files, folders, archives = [], [], []
        for p in paths:
            if os.path.isdir(p):
                folders.append(p)
            elif os.path.isfile(p):
                if core.is_image(p):
                    files.append(os.path.abspath(p))
                elif archive.is_archive(p):
                    archives.append(os.path.abspath(p))
        for d in folders:
            try:
                for name in sorted(os.listdir(d), key=core.natural_key):
                    fp = os.path.join(d, name)
                    if os.path.isfile(fp) and core.is_image(fp):
                        files.append(os.path.abspath(fp))
            except Exception:
                pass
        if archives:
            files.extend(self._import_archives(archives))
        if sort_new:
            files.sort(key=lambda x: core.natural_key(os.path.basename(x)))
        added = 0
        for fp in files:
            if fp in existing:
                continue
            existing.add(fp)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, fp)
            item.setSizeHint(QSize(200, 178))
            self.lst.addItem(item)
            if fp in self.icons:
                item.setIcon(self.icons[fp])
            elif self.stack.currentIndex() == 0:  # 文字详情模式不解码缩略图
                QThreadPool.globalInstance().start(ThumbTask(fp, self.thumb_signals))
            added += 1
        self.refresh_labels()
        self._refresh_status()
        return added

    def on_thumb_ready(self, path, qimg):
        icon = QIcon(QPixmap.fromImage(qimg))
        self.icons[path] = icon
        for i in range(self.lst.count()):
            it = self.lst.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == path:
                it.setIcon(icon)
                break

    def set_order(self, paths, selected=None):
        """只替换 item 上的路径与图标，复用缩略图缓存，避免重排后图标错位。"""
        selected = set(selected or [])
        for i, p in enumerate(paths):
            it = self.lst.item(i)
            if it is None:
                break
            it.setData(Qt.ItemDataRole.UserRole, p)
            it.setIcon(self.icons.get(p, QIcon()))
            it.setSelected(p in selected)
        self.refresh_labels()
        self._refresh_status()

    def refresh_labels(self):
        for i in range(self.lst.count()):
            it = self.lst.item(i)
            p = it.data(Qt.ItemDataRole.UserRole)
            name = os.path.basename(p)
            info = self._file_info(p)
            wh = f"{info[0]}×{info[1]}" if info else "?"
            it.setText(f"{i + 1:02d}. {name}\n{wh}")

    def on_list_reordered(self):
        self.refresh_labels()
        self._refresh_status()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片（可多选）", "",
            "图片文件 (*.jpg *.jpeg *.jfif *.png *.bmp *.tif *.tiff *.webp *.gif);;所有文件 (*.*)")
        if files:
            self.add_paths(files)

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if d:
            self.add_paths([d], sort_new=True)

    def add_archives(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择压缩包（可多选）", "",
            "压缩包 (*.zip *.7z *.rar);;所有文件 (*.*)")
        if files:
            return self.add_paths(files)
        return 0

    def add_archives_and_convert(self):
        """导入压缩包后立即生成 PDF（列表里已有的图片会一并输出）。"""
        n = self.add_archives()
        if n and self.current_paths():
            self.start_convert()

    def _import_archives(self, paths):
        """解压压缩包里的图片到临时目录；按需询问密码，最多重试 3 次。"""
        result = []
        for path in paths:
            name = os.path.basename(path)
            pw = self.archive_password
            for _attempt in range(4):
                dest = tempfile.mkdtemp(prefix="i2p_arc_")
                try:
                    imgs = archive.extract_archive(
                        path, dest, pw,
                        limit_bytes=self.archive_limit_bytes(),
                        on_limit=self._on_archive_limit)
                except archive.PasswordRequired:
                    shutil.rmtree(dest, ignore_errors=True)
                    text, ok = QInputDialog.getText(
                        self, "压缩包需要密码",
                        f"{name} 已加密，请输入解压密码：",
                        QLineEdit.EchoMode.Password)
                    if not ok:
                        break
                    pw = text or None
                    self.archive_password = pw
                    continue
                except archive.BadPassword:
                    shutil.rmtree(dest, ignore_errors=True)
                    text, ok = QInputDialog.getText(
                        self, "密码错误",
                        f"{name} 密码不正确，请重新输入（取消可跳过）：",
                        QLineEdit.EchoMode.Password)
                    if not ok:
                        break
                    pw = text or None
                    self.archive_password = pw
                    continue
                except archive.LimitExceeded as e:
                    shutil.rmtree(dest, ignore_errors=True)
                    QMessageBox.warning(
                        self, "已中止解压",
                        f"{name}\n\n{e}\n\n"
                        "如需导入，请在「⑤ 压缩包解压上限」调高数值或选择「不限制」，"
                        "或在超限弹窗中点「继续」。")
                    break
                except archive.ArchiveError as e:
                    shutil.rmtree(dest, ignore_errors=True)
                    QMessageBox.warning(self, "压缩包导入失败", f"{name}\n\n{e}")
                    break
                except Exception as e:
                    shutil.rmtree(dest, ignore_errors=True)
                    QMessageBox.warning(self, "压缩包导入失败", f"{name}\n\n{e}")
                    break
                else:
                    if imgs:
                        self.temp_dirs.append(dest)
                        result.extend(imgs)
                        self.status.setText(f"从 {name} 导入 {len(imgs)} 张图片")
                    else:
                        shutil.rmtree(dest, ignore_errors=True)
                        QMessageBox.information(self, "无图片",
                                                f"{name} 中未找到支持的图片。")
                    break
        return result

    def show_about(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(f"关于 {APP_NAME}")
        dlg.setFixedSize(470, 400)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(24, 22, 24, 18)
        head = QHBoxLayout()
        png = resource_path("assets/app.png")
        if os.path.exists(png):
            lab = QLabel()
            lab.setPixmap(QPixmap(png).scaled(
                64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
            head.addWidget(lab)
        title = QLabel(
            f"{APP_NAME}<br><span style='color:#2563eb;font-size:13px'>版本 v{APP_VER}</span>")
        title.setObjectName("aboutTitle")
        head.addWidget(title, 1)
        lay.addLayout(head)
        body = QLabel(
            "按图片实际尺寸生成 PDF · Acrobat DC 式压缩 · 移动端阅读优化<br>"
            "支持图片 / 文件夹 / 压缩包（含密码）导入、灵活排序、PDF 口令保护。<br><br>"
            "<b>技术栈</b>：PySide6 · Pillow · PyMuPDF · py7zr · pyzipper<br>"
            f"<b>许可证</b>：{LICENSE_NAME}<br>"
            f"<b>运行环境</b>：Windows x64 · Python {sys.version.split()[0]}<br>"
            f"<b>构建日期</b>：{BUILD_DATE}<br>"
            f"<b>项目主页</b>：{PROJECT_URL or '待发布（上传 GitHub 后见 README.md）'}")
        body.setObjectName("aboutBody")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.RichText)
        lay.addWidget(body)
        lay.addStretch(1)
        row = QHBoxLayout()
        row.addStretch(1)
        b_help = QPushButton("使用说明")
        b_help.clicked.connect(self.show_help)
        row.addWidget(b_help)
        b_close = QPushButton("关闭")
        b_close.setObjectName("primary")
        b_close.clicked.connect(dlg.accept)
        row.addWidget(b_close)
        lay.addLayout(row)
        dlg.exec()

    def closeEvent(self, event):
        for d in self.temp_dirs:
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        self.temp_dirs.clear()
        super().closeEvent(event)

    def selected_rows(self):
        return sorted([self.lst.row(i) for i in self.lst.selectedItems()])

    def remove_selected(self):
        for row in reversed(self.selected_rows()):
            self.lst.takeItem(row)
        self.refresh_labels()
        self._refresh_status()

    def clear_all(self):
        self.lst.clear()
        self._refresh_status()

    def move_selected(self, delta):
        """把选中的连续块整体与相邻的非选中项交换位置。"""
        rows = self.selected_rows()
        if not rows:
            return
        paths = self.current_paths()
        sel = set(rows)
        chosen = [paths[r] for r in rows]
        n = len(paths)
        if delta < 0:
            out, i = [], 0
            while i < n:
                if i in sel:
                    j = i
                    while j < n and j in sel:
                        j += 1
                    block = paths[i:j]
                    if out:
                        prev = out.pop()
                        out.extend(block)
                        out.append(prev)
                    else:
                        out.extend(block)
                    i = j
                else:
                    out.append(paths[i])
                    i += 1
            paths = out
        else:
            out, i = [], n - 1
            while i >= 0:
                if i in sel:
                    j = i
                    while j >= 0 and j in sel:
                        j -= 1
                    block = paths[j + 1:i + 1]
                    if out:
                        nxt = out.pop(0)
                        out = [nxt] + block + out
                    else:
                        out = block + out
                    i = j
                else:
                    out.insert(0, paths[i])
                    i -= 1
            paths = out
        self.set_order(paths, chosen)

    def pin_top(self):
        rows = self.selected_rows()
        if not rows:
            return
        paths = self.current_paths()
        sel = set(rows)
        chosen = [p for i, p in enumerate(paths) if i in sel]
        others = [p for i, p in enumerate(paths) if i not in sel]
        self.set_order(chosen + others, chosen)

    def pin_bottom(self):
        rows = self.selected_rows()
        if not rows:
            return
        paths = self.current_paths()
        sel = set(rows)
        chosen = [p for i, p in enumerate(paths) if i in sel]
        others = [p for i, p in enumerate(paths) if i not in sel]
        self.set_order(others + chosen, chosen)

    def reverse_order(self):
        self.set_order(list(reversed(self.current_paths())))

    def apply_sort(self):
        mode = self.sort_combo.currentIndex()
        paths = self.current_paths()
        if mode == 0:
            paths.sort(key=lambda p: core.natural_key(os.path.basename(p)))
        elif mode == 1:
            paths.sort(key=lambda p: core.natural_key(os.path.basename(p)), reverse=True)
        elif mode == 2:
            paths.sort(key=lambda p: os.path.basename(p).casefold())
        elif mode == 3:
            paths.sort(key=lambda p: os.path.getmtime(p))
        elif mode == 4:
            paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        elif mode == 5:
            paths.sort(key=lambda p: os.path.getsize(p))
        elif mode == 6:
            paths.sort(key=lambda p: os.path.getsize(p), reverse=True)
        elif mode == 7:
            paths.sort(key=lambda p: (os.path.splitext(p)[1].lower(),
                                      core.natural_key(os.path.basename(p))))
        else:
            return
        self.rebuild(paths)

    def rebuild(self, paths):
        if self.lst.count() != len(paths):
            self.lst.clear()
            for p in paths:
                it = QListWidgetItem()
                it.setSizeHint(QSize(200, 178))
                self.lst.addItem(it)
                if p not in self.icons and self.stack.currentIndex() == 0:
                    QThreadPool.globalInstance().start(ThumbTask(p, self.thumb_signals))
        self.set_order(paths)

    def show_context_menu(self, pos):
        self._build_context_menu(self.lst.itemAt(pos), self.lst.mapToGlobal(pos))

    def show_detail_context_menu(self, pos):
        self.on_detail_selection()
        vpos = self.detail.viewport().mapFrom(self.detail, pos)
        row = self.detail.indexAt(vpos).row()
        if row < 0:
            return
        self._build_context_menu(self.lst.item(row),
                                 self.detail.viewport().mapToGlobal(vpos))

    def on_detail_double_clicked(self, idx):
        it = self.lst.item(idx.row())
        if it:
            self.lst._preview(it)

    def _build_context_menu(self, item, global_pos):
        if not item:
            return
        menu = QMenu(self)
        acts = [
            ("置顶", self.pin_top), ("上移", lambda: self.move_selected(-1)),
            ("下移", lambda: self.move_selected(1)), ("置底", self.pin_bottom),
        ]
        for t, fn in acts:
            a = menu.addAction(t)
            a.triggered.connect(fn)
        menu.addSeparator()
        a = menu.addAction("按文件名排序选中项")
        a.triggered.connect(self.sort_selected_only)
        a = menu.addAction("反转选中项顺序")
        a.triggered.connect(self.reverse_selected_only)
        menu.addSeparator()
        a = menu.addAction("移除选中")
        a.triggered.connect(self.remove_selected)
        a = menu.addAction("预览大图")
        a.triggered.connect(lambda: self.lst._preview(item))
        menu.exec(global_pos)

    def _selected_to_positions(self, new_paths):
        rows = self.selected_rows()
        paths = self.current_paths()
        for r, p in zip(rows, new_paths):
            paths[r] = p
        self.set_order(paths, [paths[r] for r in rows])

    def sort_selected_only(self):
        rows = self.selected_rows()
        if len(rows) < 2:
            return
        ps = [self.lst.item(r).data(Qt.ItemDataRole.UserRole) for r in rows]
        ps.sort(key=lambda p: core.natural_key(os.path.basename(p)))
        self._selected_to_positions(ps)

    def reverse_selected_only(self):
        rows = self.selected_rows()
        if len(rows) < 2:
            return
        ps = [self.lst.item(r).data(Qt.ItemDataRole.UserRole) for r in reversed(rows)]
        self._selected_to_positions(ps)

    # ------------------------------------------------------------ 拖放（窗口级）
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        if e.mimeData().hasUrls():
            self.add_paths([u.toLocalFile() for u in e.mimeData().urls()])
            e.acceptProposedAction()

    # ------------------------------------------------------------ 转换
    def _refresh_status(self):
        n = self.lst.count()
        sel = len(self.lst.selectedItems())
        total = 0
        for i in range(n):
            try:
                total += os.path.getsize(self.lst.item(i).data(Qt.ItemDataRole.UserRole))
            except Exception:
                pass
        mode = "按图片实际尺寸" if self.rb_image.isChecked() else "统一纸张"
        self.count_label.setText(f"图片列表  ·  {n} 张")
        self.status.setText(f"共 {n} 张（选中 {sel}） · 源文件合计 {human_size(total)} · 页面：{mode}")
        self.refresh_detail()

    def build_settings(self):
        st = core.ConvertSettings()
        st.page_mode = "image" if self.rb_image.isChecked() else "paper"
        st.dpi_source = "auto" if self.dpi_source.currentIndex() == 0 else "fixed"
        st.default_dpi = float(self.default_dpi.value())
        st.fixed_dpi = float(self.fixed_dpi.value())
        mi = self.max_edge.currentIndex()
        st.max_long_edge_mm = 0.0 if mi == 0 else (297.0 if mi == 1 else
                              (420.0 if mi == 2 else float(self.max_edge_mm.value())))
        st.paper_name = self.paper.currentText()
        st.paper_w_mm = float(self.paper_w.value())
        st.paper_h_mm = float(self.paper_h.value())
        st.auto_rotate_paper = self.auto_rotate.isChecked()
        st.margin_mm = float(self.margin.value())
        st.bookmarks = self.cb_bookmark.isChecked()

        key = self.preset.currentData()
        co = core.CompressOptions()
        core.apply_preset(co, key)
        if key == "custom":
            co.enabled = True
        co.target_dpi = float(self.target_dpi.value())
        co.trigger_dpi = float(self.trigger_dpi.value())
        co.quality = int(self.quality.value())
        co.resample = ["bicubic", "average", "subsample"][self.resample.currentIndex()]
        co.only_if_smaller = self.cb_smaller.isChecked()
        co.auto_grayscale = self.cb_gray.isChecked()
        co.strip_metadata = self.cb_meta.isChecked()
        co.flatten_alpha = self.cb_alpha.isChecked()
        co.graphics_mode = self.cb_graphics.isChecked()
        co.reading_mode = self.cb_reading.isChecked()
        co.max_megapixels = float(self.max_mp.value())
        if co.reading_mode:
            co.enabled = True  # 预处理本身即重编码，独立于压缩档位
        st.compress = co

        sec = core.SecurityOptions()
        sec.enabled = self.cb_encrypt.isChecked()
        sec.user_pw = self.pw_user.text()
        sec.owner_pw = self.pw_owner.text()
        sec.method = self.enc_method.currentData()
        sec.allow_print = self.sec_print.isChecked()
        sec.allow_copy = self.sec_copy.isChecked()
        sec.allow_modify = self.sec_modify.isChecked()
        sec.allow_annotate = self.sec_annotate.isChecked()
        sec.allow_print_hq = self.sec_print_hq.isChecked()
        st.security = sec
        return st

    def choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存目录", self.out_dir.text())
        if d:
            self.out_dir.setText(d)

    def start_convert(self):
        paths = self.current_paths()
        if not paths:
            QMessageBox.warning(self, "无图片", "请先添加图片。")
            return
        folder = self.out_dir.text().strip() or os.getcwd()
        name = self.out_name.text().strip() or ("图片合集_" + datetime.now().strftime("%Y%m%d_%H%M"))
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        out = os.path.join(folder, name)
        if os.path.exists(out):
            r = QMessageBox.question(self, "文件已存在", f"覆盖现有文件？\n{out}",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return
        if self.cb_encrypt.isChecked():
            pw = self.pw_user.text()
            if not pw:
                QMessageBox.warning(self, "缺少打开密码",
                                    "已启用密码保护，请在「④ PDF 密码与权限」填写打开密码。")
                return
            if pw != self.pw_confirm.text():
                QMessageBox.warning(self, "密码不一致",
                                    "「打开密码」与「确认密码」不一致，请重新输入。")
                return
        st = self.build_settings()
        st.title = os.path.splitext(name)[0]

        self.worker = ConvertWorker(paths, out, st)
        self.worker.progressed.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.prog.setVisible(True)
        self.prog.setRange(0, len(paths))
        self.prog.setValue(0)
        self.go_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.open_btn.setEnabled(False)
        self.status.setText("正在转换 …")
        self.worker.start()

    def on_progress(self, done, total, msg):
        self.prog.setValue(done)
        self.status.setText(msg)

    def cancel_convert(self):
        if self.worker:
            self.worker.cancel()
            self.status.setText("正在取消 …")

    def on_failure(self, text):
        self._finish_ui()
        QMessageBox.critical(self, "生成失败", text)

    def on_success(self, result):
        self._finish_ui()
        self.last_output = result["output"]
        self.open_btn.setEnabled(True)
        ratio = result["ratio"]
        desc = (f"输出：{result['output']}\n\n"
                f"页数：{result['pages']}\n"
                f"源文件合计：{human_size(result['source_bytes'])}\n"
                f"PDF 大小：{human_size(result['pdf_bytes'])}  "
                f"（为源文件的 {ratio * 100:.0f}%）")
        if result.get("preprocessed"):
            desc += "\n已预处理为 baseline JPEG（阅读流畅优先，PDF 内无 Flate 图像）"
        if result.get("encrypted"):
            desc += f"\n已加密：{result.get('encryption', '')} · 打开需输入口令"
        if result["errors"]:
            desc += "\n\n以下图片失败：\n" + "\n".join(result["errors"][:8])
        self.status.setText(f"完成 · {result['pages']} 页 · {human_size(result['pdf_bytes'])}")
        QMessageBox.information(self, "生成完成", desc)

    def _finish_ui(self):
        self.go_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.prog.setVisible(False)

    def open_output_folder(self):
        if self.last_output and os.path.exists(self.last_output):
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.last_output)))

    def show_help(self):
        QMessageBox.information(self, "使用说明", (
            "1. 添加：工具栏「添加图片 / 添加文件夹 / 添加压缩包」，或直接把图片、文件夹、压缩包拖进窗口。\n"
            "   压缩包支持 ZIP（含 AES 密码）、7Z（含密码）、RAR；加密包会弹窗询问密码，本次会话记住。"
            "包内图片按文件名自然排序后进入列表；菜单「文件 → 导入压缩包并直接生成 PDF」可一步出文件。"
            "RAR 需要本机安装 7-Zip 或 WinRAR，ZIP / 7Z 无需任何外部工具。\n"
            "2. 左侧视图：点「切换为：详细信息」可在「预览小图」与「纯文字详细信息（不显示缩略图）」之间切换。"
            "文字视图列出序号、文件名、格式、像素尺寸、DPI、按当前设置算出的页面尺寸(mm)、文件大小、修改时间、所在路径；"
            "两种视图顺序完全同步，右键菜单与双击预览都可用。\n\n"
            "3. 排序：右上角选择排序依据后点「应用排序」；也可列表内拖拽、"
            "右键置顶 / 上移 / 下移 / 置底 / 仅对选中项排序。\n\n"
            "4. 页面尺寸（关键差异）：默认「按图片实际尺寸」—— 读取每张图片的 DPI，"
            "按 像素 ÷ DPI × 72 生成对应 pt 的页面，横图横页、竖图竖页、每页可不同尺寸，"
            "与 Acrobat「保留原始尺寸」一致；不强制 A4。\n"
            "   若图片 DPI 缺失或偏低，可用「固定 DPI」或「最长边限制」避免生成超大页面。\n"
            "   需要统一 A4 / A3 / 自定义纸张时，切到「统一纸张尺寸」。\n\n"
            "5. 压缩：仿 Acrobat PDF 优化器。按图像在页面上的实际 ppi 判断是否超过触发阈值，"
            "超过则双立方（LANCZOS）下采样到目标 ppi → JPEG 编码（高质量自动 4:4:4）"
            " → 与调色板 PNG 比体积取小者 → 若仍大于无损流则保留原始。"
            "页面物理尺寸全程不变，只降低图像分辨率。\n"
            "   无损档直接嵌入原始 JPEG/PNG 字节，零重编码。\n"
            "   移动端兼容：只输出 baseline JPEG（不用渐进式），照片不走 256 色量化；"
            "想再缩小体积，优先用「最长边限制」缩小页面，而不是把 ppi 压到 96 以下。\n"
            "   打开/翻页卡：勾「阅读流畅优先」把所有图片先统一转成 baseline JPEG，"
            "或点「移动端一键优化」（120 ppi / 质量70 / 长边297mm / 单页≤4MP）。"
            "PNG/Flate 虽然体积更小，但阅读器要解压成原始像素，实测比 JPEG 慢。\n"
            "   只要随便看看：点「随便看看 · 最小最快」（96 ppi / 质量55 / 长边210mm / 单页≤1MP）。"
            "图片网站流畅是因为它下发的是 1200px 展示副本（约为 10MB 原图的 2%），PDF 没有服务端，"
            "必须在生成时就把图片降维到展示尺寸；只调质量/ppi 而页面仍是几十英寸，几乎没用。\n\n"
            "6. 输出：选择目录 + 文件名，生成单个 PDF，并可按文件名写入书签目录。\n\n"
            "7. 密码：在「④ PDF 密码与权限」勾选启用，填打开密码 + 确认密码；"
            "可选填所有者密码（留空同打开密码）、选加密方式（AES-256 / AES-128 / RC4-128）、"
            "勾选允许的打印/复制/修改/注释权限。打开密码是硬保护，忘记无法恢复。\n\n"
            "8. 菜单：顶部横栏「文件 / 开始 / 视图 / 帮助」，右上角常显版本号；"
            "「开始」集中常用操作与两个一键档，「帮助 → 关于」显示版本、许可证、技术栈与项目主页。\n\n"
            "9. 压缩包上限：「⑤ 压缩包解压上限」可设 0（不限制）～100 GB，默认 1 GB，"
            "另有 1/3/10 GB/不限制快捷按钮。超限时弹窗询问「继续 / 中止」，不再自动终止；"
            "关闭「超限时弹窗询问」才会直接中止。单文件 100 MB、最多 500 张仍固定。"))


# ---------------------------------------------------------------- 入口

def _selftest():
    """打包后自检：验证 PyMuPDF DLL、端到端转换、Qt 界面链路（写 _selftest.txt）。"""
    import tempfile
    lines = []
    tmp_img = os.path.join(tempfile.gettempdir(), "_i2p_selftest.png")
    try:
        import pymupdf
        doc = pymupdf.open()
        pg = doc.new_page(width=200, height=100)
        buf = io.BytesIO()
        Image.new("RGB", (20, 10), (255, 0, 0)).save(buf, format="PNG")
        pg.insert_image(pymupdf.Rect(0, 0, 200, 100), stream=buf.getvalue())
        doc.close()
        lines.append("PyMuPDF OK  " + str(pymupdf.VersionBind))
    except Exception:
        lines.append("PyMuPDF FAIL\n" + traceback.format_exc())
    try:
        Image.new("RGB", (800, 600), (30, 90, 180)).save(tmp_img, dpi=(150, 150))
        st = core.ConvertSettings()
        core.apply_preset(st.compress, "screen")
        r = core.convert([tmp_img], tmp_img + ".pdf", st)
        lines.append(f"convert OK  pages={r['pages']} bytes={r['pdf_bytes']}")
    except Exception:
        lines.append("convert FAIL\n" + traceback.format_exc())
    try:
        import pymupdf
        st_enc = core.ConvertSettings()
        st_enc.security = core.SecurityOptions(enabled=True, user_pw="probe123",
                                               method="aes256")
        enc_path = tmp_img + "_enc.pdf"
        core.convert([tmp_img], enc_path, st_enc)
        e = pymupdf.open(enc_path)
        ok = (e.needs_pass and e.authenticate("wrong") == 0
              and e.authenticate("probe123") > 0 and e.page_count == 1)
        lines.append("encryption OK  AES-256" if ok else "encryption FAIL")
        e.close()
    except Exception:
        lines.append("encryption FAIL\n" + traceback.format_exc())
    try:
        # 压缩产物必须是 baseline JPEG(0xC0)，不能是渐进式(0xC2)
        opts = core.CompressOptions(enabled=True, target_dpi=150, trigger_dpi=100,
                                    quality=40, graphics_mode=False)
        im = Image.open(tmp_img)
        im.load()
        packed = core.compress_stream(im, 400, 300, opts, 10 ** 9)
        sof = core.jpeg_sof(packed)
        ok = packed.startswith(b"\xff\xd8") and sof == 0xC0
        lines.append("codec OK  baseline JPEG" if ok else f"codec FAIL  sof={sof}")
        im.close()
    except Exception:
        lines.append("codec FAIL\n" + traceback.format_exc())
    try:
        st_r = core.ConvertSettings()
        st_r.compress.reading_mode = True
        st_r.compress.max_megapixels = 4.0
        rp = tmp_img + "_read.pdf"
        core.convert([tmp_img], rp, st_r)
        rd = pymupdf.open(rp)
        objs = " ".join(rd.xref_object(im[0])
                        for pg in rd for im in pg.get_images(full=True))
        ok = "/DCTDecode" in objs and "/FlateDecode" not in objs
        lines.append("reading mode OK  DCT only" if ok else "reading mode FAIL")
        rd.close()
    except Exception:
        lines.append("reading mode FAIL\n" + traceback.format_exc())
    try:
        zp = tmp_img + "_probe.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tmp_img, "probe.png")
        d = tempfile.mkdtemp(prefix="i2p_st_")
        got = archive.extract_archive(zp, d, None)
        ok = len(got) == 1 and os.path.isfile(got[0])
        lines.append("archive OK  zip import" if ok else "archive FAIL")
        shutil.rmtree(d, ignore_errors=True)
    except Exception:
        lines.append("archive FAIL\n" + traceback.format_exc())
    try:
        # 7z 密码包：验证 py7zr 及其 C 扩展确实打进了 EXE
        import py7zr
        s7 = tmp_img + "_probe.7z"
        with py7zr.SevenZipFile(s7, "w", password="probe123") as z:
            z.write(tmp_img, "probe.png")
        d7 = tempfile.mkdtemp(prefix="i2p_st7_")
        got7 = archive.extract_archive(s7, d7, "probe123")
        ok = len(got7) == 1 and os.path.isfile(got7[0])
        lines.append("archive OK  7z password" if ok else "archive FAIL 7z")
        shutil.rmtree(d7, ignore_errors=True)
    except Exception:
        lines.append("archive FAIL 7z\n" + traceback.format_exc())
    try:
        # 超限时选择「继续」应能完整解压，而不是中止
        d = tempfile.mkdtemp(prefix="i2p_stlim_")
        got = archive.extract_archive(zp, d, None, limit_bytes=1,
                                      on_limit=lambda *_: True)
        ok = len(got) == 1
        lines.append("archive limit OK  continue" if ok else "archive limit FAIL")
        shutil.rmtree(d, ignore_errors=True)
    except Exception:
        lines.append("archive limit FAIL\n" + traceback.format_exc())
    try:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        qa = QApplication(sys.argv)
        qa.setStyle("Fusion")
        w = MainWindow()
        if os.path.exists(tmp_img):
            w.add_paths([tmp_img])
            w.toggle_view()
            ok = (w.stack.currentIndex() == 1 and w.detail.rowCount() == 1
                  and w.detail.item(0, 3).text() == "800 × 600")
            lines.append(("detail view OK  rows=1" if ok else "detail view FAIL"))
            w.toggle_view()
        w.apply_casual_preset()
        c = w.build_settings()
        ok2 = (c.compress.target_dpi == 96 and c.compress.quality == 55
               and c.max_long_edge_mm == 210 and c.compress.max_megapixels == 1.0
               and c.compress.reading_mode)
        lines.append("casual preset OK" if ok2 else "casual preset FAIL")
        titles = [m.title() for m in w.menuBar().findChildren(QMenu)]
        ok3 = (any("开始" in t for t in titles)
               and any("文件" in t for t in titles)
               and any("帮助" in t for t in titles)
               and hasattr(w, "show_about"))
        lines.append("menu bar OK" if ok3 else "menu bar FAIL")
        ok4 = (w.archive_limit_bytes() == 1024 ** 3
               and hasattr(w, "_on_archive_limit") and w.cb_archive_ask.isChecked())
        lines.append("archive options OK" if ok4 else "archive options FAIL")
        lines.append("Qt GUI OK")
        w.close()
    except Exception:
        lines.append("Qt GUI FAIL\n" + traceback.format_exc())
    target = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "_selftest.txt")
    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except Exception:
        pass


def main():
    if "--selftest" in sys.argv:
        _selftest()
        return
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)
    ico = resource_path("assets/app.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
