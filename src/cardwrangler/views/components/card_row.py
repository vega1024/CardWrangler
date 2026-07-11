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
_GREEN = "#639922"


def _make_x_icon(color: str = _RED) -> QIcon:
    """画一个纯色的 X 图标，避免依赖字体字形（部分系统 ✕ 会显示成方块）。"""
    size = 16
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        m = 4
        painter.drawLine(m, m, size - m, size - m)
        painter.drawLine(size - m, m, m, size - m)
    finally:
        painter.end()
    return QIcon(pm)


class CardRow(QWidget):
    """一个任务行：左侧标题 + 副标题，右侧红色 X 删除按钮。

    支持 set_selected 切换选中态（绿色背景整行高亮）。
    """

    def __init__(self, job: CardJob, on_delete: Callable[[str], None]) -> None:
        super().__init__()
        self.job = job

        h = QHBoxLayout(self)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(8)

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(2)

        self.title = QLabel(job.label)
        self.sub = QLabel(f"{len(job.items)} 个文件 · {job.status.value}")

        col.addWidget(self.title)
        col.addWidget(self.sub)
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

        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet("background:#639922; border-radius:6px;")
            self.title.setStyleSheet("color:#ffffff; font-weight:600; font-size:13px;")
            self.sub.setStyleSheet("color:#e6f0e6; font-size:11px;")
        else:
            self.setStyleSheet("")
            self.title.setStyleSheet("font-weight:600; font-size:13px;")
            self.sub.setStyleSheet("color:#6b7280; font-size:11px;")
