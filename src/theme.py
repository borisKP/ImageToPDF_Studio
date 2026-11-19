# -*- coding: utf-8 -*-
"""明暗主题：浅色 / 深色 / 跟随系统。

QSS 用 _TEMPLATE + 颜色变量生成；主题切换只重设 stylesheet，不重建窗口。
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import QSettings, QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

THEMES = [("auto", "跟随系统"), ("light", "浅色"), ("dark", "深色")]

_TEMPLATE = """
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif; font-size: 12px; color: $text; }
QMainWindow, QDialog { background: $window; }
QGroupBox {
    border: 1px solid $border; border-radius: 8px; margin-top: 12px;
    background: $panel; padding: 10px 8px 8px 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: $title; font-weight: 600; }
QLabel#hint { color: $muted; font-size: 11px; }
QLabel#section { color: $title; font-weight: 600; }
QPushButton {
    background: $panel; border: 1px solid $border; border-radius: 6px;
    padding: 6px 12px; color: $text;
}
QPushButton:hover { background: $hover; border-color: $accent; }
QPushButton:pressed { background: $pressed; }
QPushButton:disabled { color: $muted; background: $window; }
QPushButton#primary { background: $accent; border: 1px solid $accent; color: $on_accent; font-weight: 600; padding: 8px 18px; }
QPushButton#primary:hover { background: $accent_hover; }
QPushButton#primary:disabled { background: $accent_dim; border-color: $accent_dim; color: $on_accent; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: $input; border: 1px solid $border; border-radius: 6px;
    padding: 5px 7px; selection-background-color: $selection;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border-color: $accent; }
QComboBox::drop-down { border: none; width: 18px; }
QListWidget { background: $input; border: 1px solid $border; border-radius: 8px; padding: 6px; }
QListWidget::item { border-radius: 6px; padding: 4px; color: $text; }
QListWidget::item:selected { background: $selection; color: $on_selection; }
QListWidget::item:hover { background: $hover; }
QTableWidget { background: $input; border: 1px solid $border; border-radius: 8px;
    gridline-color: $border; selection-background-color: $selection; selection-color: $on_selection; }
QTableWidget::item { padding: 3px 6px; }
QHeaderView::section { background: $panel; border: none; border-right: 1px solid $border;
    border-bottom: 1px solid $border; padding: 6px 8px; color: $title; font-weight: 600; }
QProgressBar { border: 1px solid $border; border-radius: 6px; background: $window; height: 16px; text-align: center; }
QProgressBar::chunk { background: $accent; border-radius: 5px; }
QSlider::groove:horizontal { height: 5px; background: $border; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; background: $accent; border-radius: 7px; margin: -5px 0; }
QCheckBox, QRadioButton { spacing: 6px; }
QToolBar { background: $panel; border-bottom: 1px solid $border; spacing: 4px; padding: 6px; }
QStatusBar { color: $muted; }
QSplitter::handle { background: $border; }
QMenuBar { background: $panel; border-bottom: 1px solid $border; padding: 3px 6px; }
QMenuBar::item { padding: 5px 12px; border-radius: 5px; color: $text; }
QMenuBar::item:selected { background: $hover; color: $on_selection; }
QMenu { background: $panel; border: 1px solid $border; border-radius: 6px; padding: 4px; }
QMenu::item { padding: 6px 26px 6px 18px; border-radius: 4px; }
QMenu::item:selected { background: $selection; color: $on_selection; }
QMenu::separator { height: 1px; background: $border; margin: 4px 8px; }
QLabel#version { color: $muted; padding-right: 12px; font-size: 11px; }
QLabel#aboutTitle { font-size: 19px; font-weight: 700; color: $title; }
QLabel#aboutBody { color: $muted; font-size: 12px; }
QFrame#bottomBar { background: $panel; border-top: 1px solid $border; }
"""

LIGHT = dict(text="#1f2937", window="#f4f6fa", panel="#ffffff", input="#ffffff",
             border="#e2e8f0", title="#0f172a", muted="#64748b", hover="#eef4ff",
             pressed="#e0ebff", accent="#2563eb", accent_hover="#1d4ed8",
             accent_dim="#a9bff0", on_accent="#ffffff", selection="#dbeafe",
             on_selection="#1e3a8a")

DARK = dict(text="#e2e8f0", window="#0f172a", panel="#1e293b", input="#172033",
            border="#334155", title="#f8fafc", muted="#94a3b8", hover="#334155",
            pressed="#475569", accent="#3b82f6", accent_hover="#60a5fa",
            accent_dim="#1e40af", on_accent="#ffffff", selection="#1e40af",
            on_selection="#eff6ff")


class _Bus(QObject):
    theme_changed = Signal(str)


bus = _Bus()
_settings = QSettings("BorisKP", "ImageToPDF_Studio")
_current = _settings.value("theme", "auto")
if _current not in dict(THEMES):
    _current = "auto"


def current_theme() -> str:
    return _current


def set_theme(mode: str, *, notify: bool = True) -> None:
    global _current
    if mode not in dict(THEMES):
        return
    changed = mode != _current
    _current = mode
    _settings.setValue("theme", mode)
    if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
        apply()
    if changed and notify:
        bus.theme_changed.emit(mode)


def system_is_dark() -> bool:
    """Windows 注册表优先；其它平台用 Qt 调色板亮度判断。"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as k:
                v, _ = winreg.QueryValueEx(k, "AppsUseLightTheme")
                return int(v) == 0
        except Exception:
            pass
    app = QApplication.instance()
    if app is not None:
        bg = app.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128
    return False


def resolved() -> str:
    if _current == "auto":
        return "dark" if system_is_dark() else "light"
    return _current


def stylesheet() -> str:
    """生成可直接 setStyleSheet 的 QSS。"""
    from string import Template
    colors = DARK if resolved() == "dark" else LIGHT
    return Template(_TEMPLATE).substitute(**colors)


def apply() -> None:
    app = QApplication.instance()
    if app is not None:
        app.setStyleSheet(stylesheet())
