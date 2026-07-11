"""独立冒烟脚本：验证「添加源盘」入口与校验方式布局。

不依赖 pytest：直接断言，失败抛 AssertionError。
把 AddCardDialog.exec 打桩成立即返回，只验证信号链与校验方式横向布局。
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QRadioButton

from cardwrangler.viewmodels.content_view_model import ContentViewModel
from cardwrangler.views.main_window import MainWindow
from cardwrangler.views.add_card_view import AddCardDialog


_state = {"toolbar": 0, "sidebar": 0}


def _fake_exec_toolbar(self):
    _state["toolbar"] += 1
    return QDialog.Rejected


def _fake_exec_sidebar(self):
    _state["sidebar"] += 1
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
    AddCardDialog.exec = _fake_exec_toolbar

    vm = ContentViewModel()
    win = MainWindow(vm)
    win.show()

    # 1) 工具栏「+ 添加源盘」
    win.add_btn.click()
    QTimer.singleShot(0, lambda: None)
    app.processEvents()
    assert _state["toolbar"] >= 1, "FAIL: 工具栏按钮点击后未打开对话框"

    # 2) 侧边栏「+ 添加存储卡」
    AddCardDialog.exec = _fake_exec_sidebar
    sidebar = win.sidebar
    btn = None
    for i in range(sidebar.layout().count()):
        w = sidebar.layout().itemAt(i).widget()
        if isinstance(w, QPushButton) and w.text() == "+ 添加存储卡":
            btn = w
            break
    assert btn is not None, "FAIL: 侧边栏未找到「+ 添加存储卡」按钮"
    btn.click()
    app.processEvents()
    assert _state["sidebar"] >= 1, "FAIL: 侧边栏按钮点击后未打开对话框"

    # 3) 校验方式横向布局 + 标签与默认值
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

    print("PASS: 工具栏与侧边栏「添加源盘」入口均正常触发对话框")
    print(f"  toolbar calls = {_state['toolbar']}, sidebar calls = {_state['sidebar']}")
    print(f"  校验方式横向布局：{texts}")
    print(f"  默认选中：{checked[0]}")


if __name__ == "__main__":
    main()
