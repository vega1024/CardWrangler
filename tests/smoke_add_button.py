"""独立冒烟脚本：验证「添加源盘」工具栏入口与校验方式布局。

不依赖 pytest：直接断言，失败抛 AssertionError。
把 AddCardDialog.exec 打桩成立即返回，只验证信号链与校验方式横向布局。
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QRadioButton

from cardwrangler.viewmodels.content_view_model import ContentViewModel
from cardwrangler.views.main_window import MainWindow
from cardwrangler.views.add_card_view import AddCardDialog


_state = {"toolbar": 0}


def _fake_exec(self):
    _state["toolbar"] += 1
    return QDialog.Rejected


def _find_algo_row(dlg: AddCardDialog):
    """找到包含「校验方式」QLabel 的横向布局及其 4 个 QRadioButton。"""
    root = dlg.layout()
    for i in range(root.count()):
        item = root.itemAt(i)
        if item is None or item.layout() is None:
            continue
        lay = item.layout()
        if not isinstance(lay, QHBoxLayout):
            continue
        labels = [w for w in (lay.itemAt(j).widget() for j in range(lay.count())) if isinstance(w, QLabel)]
        radios = [w for w in (lay.itemAt(j).widget() for j in range(lay.count())) if isinstance(w, QRadioButton)]
        if labels and any("校验方式" in (w.text() or "") for w in labels):
            return lay, radios
    raise AssertionError("FAIL: 未找到「校验方式」横向布局")


def main() -> None:
    app = QApplication(sys.argv)
    AddCardDialog.exec = _fake_exec

    vm = ContentViewModel()
    win = MainWindow(vm)
    win.show()

    # 工具栏「+ 添加源盘」
    win.add_btn.click()
    QTimer.singleShot(0, lambda: None)
    app.processEvents()
    assert _state["toolbar"] >= 1, "FAIL: 工具栏按钮点击后未打开对话框"

    # 侧边栏不应再有「+ 添加存储卡」按钮
    sidebar = win.sidebar
    buttons = [
        sidebar.layout().itemAt(i).widget()
        for i in range(sidebar.layout().count())
        if isinstance(sidebar.layout().itemAt(i).widget(), QPushButton)
    ]
    assert len(buttons) == 0, f"FAIL: 侧边栏仍残留按钮 {buttons}"

    # 校验方式横向布局 + 标签与默认值
    dlg = AddCardDialog()
    lay, radios = _find_algo_row(dlg)
    assert lay is not None and isinstance(lay, QHBoxLayout), "FAIL: 校验方式不是横向布局"
    assert len(radios) == 4, f"FAIL: 校验方式应有 4 个单选，实际 {len(radios)}"
    texts = [r.text() for r in radios]
    assert "MD5（较慢，推荐）" in texts, f"FAIL: 未找到 MD5 推荐标签，实际 {texts}"
    assert "不校验，只比较尺寸（不推荐）" in texts, f"FAIL: 不校验标签未对齐截图，实际 {texts}"
    checked = [r.text() for r in radios if r.isChecked()]
    assert len(checked) == 1, f"FAIL: 应只有一个单选被选中，实际 {checked}"
    assert checked[0] == "MD5（较慢，推荐）", f"FAIL: 默认应选中 MD5，实际 {checked[0]}"

    print("PASS: 工具栏「添加源盘」入口正常，侧边栏无添加按钮，校验方式横向默认 MD5")
    print(f"  toolbar calls = {_state['toolbar']}")
    print(f"  校验方式横向布局：{texts}")
    print(f"  默认选中：{checked[0]}")


if __name__ == "__main__":
    main()
