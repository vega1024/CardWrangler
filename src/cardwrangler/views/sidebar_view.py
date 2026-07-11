"""侧边栏：任务列表 + 添加按钮。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QPushButton, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from ..models.card_job import CardJob
from .components.card_row import CardRow


class SidebarView(QWidget):
    job_selected = Signal(str)   # 选中的任务 id
    add_requested = Signal()     # 点击「添加存储卡」
    delete_requested = Signal(str)  # 请求删除某任务 id

    def __init__(self) -> None:
        super().__init__()
        self._selected_id: str | None = None
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
            self.list.setItemWidget(
                item, CardRow(job, lambda jid: self.delete_requested.emit(jid))
            )
        if self._selected_id:
            self.set_selected(self._selected_id)

    def set_selected(self, job_id: str | None) -> None:
        """高亮选中的任务行（绿色背景）。"""
        self._selected_id = job_id
        for i in range(self.list.count()):
            it = self.list.item(i)
            w = self.list.itemWidget(it)
            if isinstance(w, CardRow):
                w.set_selected(it.data(Qt.UserRole) == job_id)
