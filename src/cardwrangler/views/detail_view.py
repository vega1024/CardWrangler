"""详情区：选中任务的文件列表（状态 / 进度 / 校验结果）。"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from ..models.card_job import CardJob
from ..models.item import Item, ItemStatus


class DetailView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件", "状态", "进度", "校验"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)

        self.status = QLabel("未选择任务")
        self.status.setStyleSheet("color: #6b7280; font-size: 12px;")

        layout.addWidget(self.table)
        layout.addWidget(self.status)

        self._row_for: dict[str, int] = {}

    def show_job(self, job: CardJob | None) -> None:
        self.table.setRowCount(0)
        self._row_for = {}
        if job is None:
            self.status.setText("未选择任务")
            return
        for item in job.items:
            self._add_row(item)
        verified = job.verified_count
        self.status.setText(
            f"任务：{job.label} · {len(job.items)} 个文件 · "
            f"{len(job.dest_roots)} 个目标 · 已校验 {verified}"
        )

    def _add_row(self, item: Item) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(item.name))
        self.table.setItem(row, 1, QTableWidgetItem(item.status.value))
        self.table.setItem(row, 2, QTableWidgetItem("0%"))
        self.table.setItem(row, 3, QTableWidgetItem(""))
        self._row_for[item.id] = row

    def update_progress(self, item: Item, percent: int) -> None:
        row = self._row_for.get(item.id)
        if row is None:
            return
        self.table.setItem(row, 1, QTableWidgetItem(item.status.value))
        self.table.setItem(row, 2, QTableWidgetItem(f"{percent}%"))
        if item.status == ItemStatus.VERIFIED:
            mark = "✓"
        elif item.status == ItemStatus.FAILED:
            mark = "✗"
        else:
            mark = ""
        self.table.setItem(row, 3, QTableWidgetItem(mark))
