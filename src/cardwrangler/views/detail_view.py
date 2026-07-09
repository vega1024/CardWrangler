"""详情区：选中任务按「目标」分卡片展示。

- 每个目标（拷贝目的地）一张卡片，默认只显示目标名 + 成功/失败。
- 点击卡片标题展开，显示该目标下每个文件的校验结果（✓/✗）。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models.card_job import CardJob
from ..models.item import Item, ItemStatus


class _TargetCard(QWidget):
    """单个目标卡片：可点击标题展开 / 折叠。"""

    _BASE_STYLE = (
        "QPushButton{text-align:left; padding:7px 10px; "
        "border:1px solid #d1d5db; border-radius:6px; font-weight:600; "
        "background:#f9fafb;}"
    )

    def __init__(self, di: int, name: str, full_path: str) -> None:
        super().__init__()
        self.di = di
        self.name = name
        self.full_path = full_path
        self.expanded = False
        self.row_for: dict[str, int] = {}
        self.table: Optional[QTableWidget] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QPushButton()
        self.header.setToolTip(full_path)
        self.header.clicked.connect(self.toggle)
        layout.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(10, 6, 10, 6)
        layout.addWidget(self.body)
        self.body.setVisible(False)

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)
        # 箭头刷新由 set_status 负责（沿用当前文案）

    def set_status(self, text: str, color: str) -> None:
        arrow = "▾" if self.expanded else "▸"
        self.header.setText(f"{arrow}  目标 {self.di + 1} · {self.name}    —  {text}")
        self.header.setStyleSheet(self._BASE_STYLE + f" color:{color};")


class DetailView(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(self.scroll.Shape.NoFrame)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(8)
        self.container_layout.addStretch(1)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

        self.status = QLabel("未选择任务")
        self.status.setStyleSheet("color:#6b7280; font-size:12px;")
        layout.addWidget(self.status)

        self.cards: List[_TargetCard] = []

    # ---------- 任务展示 ----------
    def show_job(self, job: CardJob | None) -> None:
        self._clear_cards()
        if job is None:
            self.status.setText("未选择任务")
            return

        for di, root in enumerate(job.dest_roots):
            name = Path(root).name or root
            card = _TargetCard(di, name, root)
            card.table = QTableWidget(0, 2)
            card.table.setHorizontalHeaderLabels(["文件", "校验"])
            card.table.horizontalHeader().setStretchLastSection(True)
            card.table.setEditTriggers(card.table.EditTrigger.NoEditTriggers)
            for item in job.items:
                self._add_row(card, item)
            card.body_layout.addWidget(card.table)

            status_text, color, _ = self._summary(job, di)
            card.set_status(status_text, color)
            self.container_layout.insertWidget(self.container_layout.count() - 1, card)
            self.cards.append(card)

        self.status.setText(
            f"任务：{job.label} · {len(job.dest_roots)} 个目标 · "
            f"{len(job.items)} 个文件"
            + ("" if job.verify_after_copy else " · 未校验")
        )

    def _add_row(self, card: _TargetCard, item: Item) -> None:
        row = card.table.rowCount()
        card.table.insertRow(row)
        card.table.setItem(row, 0, QTableWidgetItem(item.name))
        card.table.setItem(row, 1, QTableWidgetItem(self._mark_for(item, card.di)))
        card.row_for[item.id] = row

    # ---------- 进度回调 ----------
    def update_progress(self, item: Item, percent: int) -> None:
        for card in self.cards:
            row = card.row_for.get(item.id)
            if row is None or card.table is None:
                continue
            card.table.setItem(row, 1, QTableWidgetItem(self._mark_for(item, card.di)))

    # ---------- 帮助 ----------
    def _mark_for(self, item: Item, di: int) -> str:
        if di < len(item.checksums_dest) and item.checksum_source:
            if item.checksums_dest[di] == item.checksum_source:
                return "✓"
            if item.checksums_dest[di]:
                return "✗"
        if item.status == ItemStatus.FAILED:
            return "✗"
        return ""

    def _summary(self, job: CardJob, di: int):
        total = len(job.items)
        verified = 0
        failed = 0
        for it in job.items:
            if di < len(it.checksums_dest) and it.checksum_source:
                if it.checksums_dest[di] == it.checksum_source:
                    verified += 1
                elif it.checksums_dest[di]:
                    failed += 1
        if not job.verify_after_copy:
            return (f"已拷贝 {total}", "#2563eb", total)
        if total > 0 and verified == total:
            return (f"成功 {verified}/{total}", "#16a34a", verified)
        if failed > 0 or verified < total:
            return (f"失败 {verified}/{total}", "#dc2626", verified)
        return (f"校验中 {verified}/{total}", "#6b7280", verified)

    def _clear_cards(self) -> None:
        for card in self.cards:
            card.deleteLater()
        self.cards = []
