"""侧边栏：任务列表 + 添加按钮。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QPushButton, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ..models.card_job import CardJob
from .components.card_row import make_card_row


class SidebarView(QWidget):
    job_selected = Signal(str)   # 选中的任务 id
    add_requested = Signal()     # 点击「添加存储卡」

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.list = QListWidget()
        self.list.setSpacing(4)
        self.list.itemClicked.connect(lambda it: self.job_selected.emit(it.data(Qt.UserRole)))

        add_btn = QPushButton("+ 添加存储卡")
        add_btn.clicked.connect(self.add_requested.emit)

        layout.addWidget(self.list)
        layout.addWidget(add_btn)

    def set_jobs(self, jobs: list[CardJob]) -> None:
        self.list.clear()
        for job in jobs:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, job.id)
            item.setSizeHint(QSize(0, 46))
            self.list.addItem(item)
            self.list.setItemWidget(item, make_card_row(job))
