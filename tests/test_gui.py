# -*- coding: utf-8 -*-
# --- 允许从仓库任意位置运行：把 src 加入模块搜索路径 ---
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
"""GUI 无头自测：构造、枚举兼容、排序/置顶/移动、设置映射、端到端转换"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
import core
import app as gui

BASE = os.path.dirname(os.path.abspath(__file__))
TESTDIR = os.path.join(BASE, "_test_images")
OUTDIR = os.path.join(BASE, "_test_out")


def names(w):
    return [os.path.basename(p) for p in w.current_paths()]


def run():
    qa = QApplication.instance() or QApplication(sys.argv)
    qa.setStyle("Fusion")
    w = gui.MainWindow()
    print("窗口构造 OK")

    ps = [os.path.join(TESTDIR, n) for n in sorted(os.listdir(TESTDIR))]
    w.add_paths(ps)
    print("添加:", names(w))
    assert w.lst.count() == 3

    # ---- 新功能：预览小图 ⇄ 文字详细信息 ----
    assert w.stack.currentIndex() == 0
    w.toggle_view()
    assert w.stack.currentIndex() == 1
    assert w.detail.rowCount() == 3
    row0 = [w.detail.item(0, c).text() for c in range(9)]
    print("详情第 1 行:", row0)
    assert row0[0] == "01" and row0[2] == "JPG" and row0[3] == "3000 × 2000"
    assert row0[4] == "300 × 300" and "mm" not in row0[5]
    assert "254.0 × 169.3" == row0[5] or "×" in row0[5]
    # 详情视图选中同步到缩略图列表，右键操作共用
    w.detail.selectRow(2)
    assert w.selected_rows() == [2], "详情视图选中未同步"
    w.pin_top()
    assert w.detail.item(0, 1).text().startswith("10_"), "详情视图未随置顶刷新"
    # 页面设置变化 → 详情里的「页面尺寸」列重算
    before = w.detail.item(0, 5).text()
    w.rb_paper.setChecked(True)
    w.paper.setCurrentText("A4")
    after = w.detail.item(0, 5).text()
    print("页面尺寸列:", before, "->", after)
    assert before != after
    w.rb_image.setChecked(True)
    w.toggle_view()
    assert w.stack.currentIndex() == 0
    print("视图切换 OK")

    # 文件名自然排序
    w.sort_combo.setCurrentIndex(0)
    w.apply_sort()
    print("自然升序:", names(w))
    assert names(w) == sorted([os.path.basename(p) for p in ps], key=core.natural_key)

    # 反转
    w.reverse_order()
    print("反转:", names(w))
    w.apply_sort()

    # 选中第 3 项置顶
    w.lst.item(2).setSelected(True)
    w.pin_top()
    print("置顶后:", names(w))
    assert names(w)[0] == "10_截图_1600x900_96dpi.png"

    # 选中第 2 项上移 / 下移
    w.lst.clearSelection()
    w.lst.item(1).setSelected(True)
    before = names(w)
    w.move_selected(-1)
    print("上移:", before, "->", names(w))
    w.lst.clearSelection()
    w.lst.item(0).setSelected(True)
    w.move_selected(1)
    print("下移:", names(w))

    # 右键选中项排序
    w.lst.clearSelection()
    for i in (0, 1):
        w.lst.item(i).setSelected(True)
    w.sort_selected_only()
    print("选中项排序:", names(w))

    # 设置映射 + 端到端
    st = w.build_settings()
    print("设置:", st.page_mode, st.dpi_source, "压缩开启=", st.compress.enabled,
          "target=", st.compress.target_dpi, "quality=", st.compress.quality)
    out = os.path.join(OUTDIR, "GUI端到端.pdf")
    r = core.convert(w.current_paths(), out, st)
    print("端到端:", r["pages"], "页", r["pdf_bytes"], "bytes", "错误:", r["errors"])
    assert r["pages"] == 3 and not r["errors"]

    # 切到统一 A4
    w.rb_paper.setChecked(True)
    w.paper.setCurrentText("A3")
    st2 = w.build_settings()
    assert st2.page_mode == "paper" and st2.paper_name == "A3"
    print("A3 设置映射 OK; 控件可用状态:", w.paper.isEnabled(), w.dpi_source.isEnabled())

    # ---- 密码与权限设置映射
    assert not w.build_settings().security.enabled
    w.cb_encrypt.setChecked(True)
    w.pw_user.setText("abc123")
    w.pw_confirm.setText("abc123")
    w.pw_owner.setText("owner")
    w.enc_method.setCurrentIndex(1)  # AES-128
    w.sec_copy.setChecked(False)
    w.sec_modify.setChecked(False)
    sec = w.build_settings().security
    print("安全设置:", sec)
    assert sec.enabled and sec.user_pw == "abc123" and sec.owner_pw == "owner"
    assert sec.method == "aes128" and not sec.allow_copy and not sec.allow_modify
    kw = core.security_kwargs(w.build_settings())
    assert kw["encryption"] == 4 and kw["user_pw"] == "abc123" and kw["owner_pw"] == "owner"
    assert w.pw_user.echoMode() == gui.QLineEdit.EchoMode.Password
    w.cb_show_pw.setChecked(True)
    assert w.pw_user.echoMode() == gui.QLineEdit.EchoMode.Normal
    w.cb_encrypt.setChecked(False)
    assert core.security_kwargs(w.build_settings()) == {}
    print("密码设置映射 OK")

    # ---- 移动端一键优化
    w.apply_mobile_preset()
    s = w.build_settings()
    print("一键优化:", s.compress.target_dpi, s.compress.quality,
          s.max_long_edge_mm, s.compress.reading_mode, s.compress.max_megapixels)
    assert s.compress.reading_mode and s.compress.max_megapixels == 4.0
    assert s.compress.target_dpi == 120 and s.compress.quality == 70
    assert s.max_long_edge_mm == 297.0 and w.cb_reading.isChecked()
    print("移动端一键优化 OK")

    # ---- 随便看看一键档
    w.apply_casual_preset()
    c = w.build_settings()
    print("随便看看:", c.compress.target_dpi, c.compress.quality,
          c.max_long_edge_mm, c.compress.max_megapixels)
    assert c.compress.reading_mode and c.compress.max_megapixels == 1.0
    assert c.compress.target_dpi == 96 and c.compress.quality == 55
    assert c.max_long_edge_mm == 210.0
    print("随便看看一键档 OK")

    print("\n>>> GUI 自测全部通过")


if __name__ == "__main__":
    run()
