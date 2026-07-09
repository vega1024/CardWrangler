"""侧边栏里单个任务的行控件（仅 UI 展示，不含业务逻辑）。"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ...models.card_job import CardJob


def make_card_row(job: CardJob, on_delete: Callable[[str], None]) -> QWidget:
    """为一个任务生成一行：左侧标题+副标题，右侧删除按钮。

    on_delete(job_id) 在点击删除按钮时回调，由调用方决定具体逻辑。
    """
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(8, 6, 8, 6)
    h.setSpacing(8)

    col = QVBoxLayout()
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(2)

    title = QLabel(job.label)
    title.setStyleSheet("font-weight: 600; font-size: 13px;")

    sub = QLabel(f"{len(job.items)} 个文件 · {job.status.value}")
    sub.setStyleSheet("color: #6b7280; font-size: 11px;")

    col.addWidget(title)
    col.addWidget(sub)
    h.addLayout(col, 1)

    del_btn = QPushButton("✕")
    del_btn.setFixedSize(22, 22)
    del_btn.setToolTip("删除此任务")
    del_btn.setStyleSheet(
        "QPushButton{border:none; color:#9ca3af; font-weight:700; "
        "border-radius:4px;} QPushButton:hover{color:#dc2626; background:#fee2e2;}"
    )
    del_btn.clicked.connect(lambda: on_delete(job.id))
    h.addWidget(del_btn)
    return w
