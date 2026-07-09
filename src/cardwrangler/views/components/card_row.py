"""侧边栏里单个任务的行控件（仅 UI 展示，不含逻辑）。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout

from ...models.card_job import CardJob


def make_card_row(job: CardJob) -> QWidget:
    """为一个任务生成一个两行（标题 + 副标题）的小卡片。"""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.setContentsMargins(8, 6, 8, 6)
    layout.setSpacing(2)

    title = QLabel(job.label)
    title.setStyleSheet("font-weight: 600; font-size: 13px;")

    sub = QLabel(f"{len(job.items)} 个文件 · {job.status.value}")
    sub.setStyleSheet("color: #6b7280; font-size: 11px;")

    layout.addWidget(title)
    layout.addWidget(sub)
    return w
