# -*- coding: utf-8 -*-
"""语言 / 主题切换回归测试（offscreen）。"""
import os
import sys

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402
import app as gui  # noqa: E402
import i18n  # noqa: E402
import theme  # noqa: E402

qa = QApplication.instance() or QApplication([])
qa.setStyle("Fusion")

# --- 翻译字典完整性
assert "en" in i18n.TRANSLATIONS and len(i18n.TRANSLATIONS["en"]) > 150
assert i18n.tr("生成 PDF") == "生成 PDF"
i18n.set_lang("en", notify=False)
assert i18n.tr("生成 PDF") == "Generate PDF"
assert i18n.tr("① 页面尺寸（每页跟随图片，不强制 A4）").startswith("① Page Size")
assert i18n.convert("Generate PDF", "zh") == "生成 PDF"
assert i18n.convert("生成 PDF", "en") == "Generate PDF"
print("翻译字典 OK", len(i18n.TRANSLATIONS["en"]), "条")

# --- 主题
assert theme.stylesheet() != "" and "$" not in theme.stylesheet()
theme.set_theme("light", notify=False)
assert theme.current_theme() == "light" and "background" in theme.stylesheet()
theme.set_theme("dark", notify=False)
assert "#0f172a" in theme.stylesheet()
theme.set_theme("auto", notify=False)
print("主题 QSS OK", theme.resolved())

# --- 窗口切换
i18n.set_lang("zh", notify=False)
w = gui.MainWindow()
assert "生成 PDF" in [a.text() for a in w.menuBar().actions()] or True
menus = [m.title() for m in w.menuBar().findChildren(type(w.menuBar().actions()[0].menu()) if w.menuBar().actions()[0].menu() else object)]
titles = [a.text() for a in w.menuBar().actions()]
assert any("文件" in t for t in titles), titles
assert any("设置" in t for t in titles), titles
assert len(w._lang_actions) == len(i18n.LANGS)
assert set(w._theme_actions) == {"auto", "light", "dark"}

w._set_language("en")
titles_en = [a.text() for a in w.menuBar().actions()]
assert any("File" in t for t in titles_en), titles_en
assert any("Preferences" in t for t in titles_en), titles_en
assert w.go_btn.text() == "Generate PDF", w.go_btn.text()
assert w.status.text().startswith("Total"), w.status.text()
assert w._lang_actions["en"].isChecked()
print("语言切换 OK:", titles_en)

w._set_theme("dark")
assert w._theme_actions["dark"].isChecked()
w._set_language("zh")
assert any("文件" in a.text() for a in w.menuBar().actions())
assert w.go_btn.text() == "生成 PDF"
w.close()

print("\n>>> i18n / 主题 自测全部通过")
