"""应用启动：创建 QApplication、装载样式、呈现主窗口。"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .persistence.repository import JobRepository
from .viewmodels.content_view_model import ContentViewModel
from .views.main_window import MainWindow

# 轻量浅色主题（与 WorkBuddy 浅色 IDE 风格一致）
BASE_STYLE = """
QMainWindow, QWidget { background: #f7f8fa; color: #1f2937; }
QToolBar { background: #eef0f3; border: none; padding: 4px; }
QPushButton {
    background: #2563eb; color: white; border: none;
    padding: 6px 14px; border-radius: 6px; font-weight: 600;
}
QPushButton:hover { background: #1d4ed8; }
QListWidget, QTableWidget {
    background: white; border: 1px solid #e5e7eb; border-radius: 6px;
}
QHeaderView::section { background: #f3f4f6; padding: 4px; border: none; }
QLabel { color: #1f2937; }
"""


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("CardWrangler")
    app.setStyleSheet(BASE_STYLE)

    repo = JobRepository.default()
    vm = ContentViewModel(repo)
    window = MainWindow(vm)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(run())
