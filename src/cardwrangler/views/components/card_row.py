"""侧边栏里单个任务的行控件（仅 UI 展示，不含业务逻辑）。"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)

from ...models.card_job import CardJob

_RED = "#dc2626"


def _make_x_icon(color: str = _RED) -> QIcon:
    """画一个纯色的 X 图标，避免依赖字体字形（部分系统 ✕ 会显示成方块）。"""
    size = 16
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    m = 4
    painter.drawLine(m, m, size - m, size - m)
    painter.drawLine(size - m, m, m, size - m)
    painter.end()
    return QIcon(pm)


def make_card_row(job: CardJob, on_delete: Callable[[str], None]) -> QWidget:
    """为一个任务生成一行：左侧标题+副标题，右侧删除按钮（红色 X 图标）。

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

    del_btn = QPushButton()
    del_btn.setIcon(_make_x_icon())
    del_btn.setIconSize(QSize(16, 16))
    del_btn.setFixedSize(24, 24)
    del_btn.setToolTip("删除此任务")
    del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    # 完全透明：无边框、无背景（hover 也保持红色 X，不出现方框）
    del_btn.setStyleSheet(
        "QPushButton{border:none; background:transparent;} "
        "QPushButton:hover{background:transparent;}"
    )
    del_btn.clicked.connect(lambda: on_delete(job.id))
    h.addWidget(del_btn)
    return w
