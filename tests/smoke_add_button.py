"""独立冒烟脚本：验证「添加源盘」两个入口都能触发对话框。

不依赖 pytest：直接断言，失败抛 AssertionError。
把 AddCardDialog.exec 打桩成立即返回，只验证信号链是否接通。
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QPushButton

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

    print("PASS: 工具栏与侧边栏「添加源盘」入口均正常触发对话框")
    print(f"  toolbar calls = {_state['toolbar']}, sidebar calls = {_state['sidebar']}")


if __name__ == "__main__":
    main()
