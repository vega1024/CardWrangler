"""详情区：选中任务以「单卡片 + 目标盘表格」展示。

- 顶部：源盘标题、任务统计（任务 / 拷贝完成 / 校验完成）、创建报告按钮、空状态引导。
- 一个任务一张卡片，默认展示任务名 + 完成状态 + 耗时 + 文件数 + 完成时间。
- 点击卡片头部展开，显示该任务在各目标盘上的结果表格：
  目标盘信息 / 拷贝容量 / 目标路径 / 拷贝 / 校验（含完成时间与耗时）。
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QEvent, QSize, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models.card_job import CardJob
from ..models.item import ItemStatus


# ---------- 小工具 ----------
def _colored_box(color: str, size: int = 40, radius: int = 8) -> QLabel:
    """生成一个纯色圆角方块作为图标占位（不依赖字体字形）。"""
    label = QLabel()
    label.setFixedSize(size, size)
    label.setStyleSheet(
        f"background:{color}; border-radius:{radius}px;"
    )
    return label


def _check_icon() -> QLabel:
    """画一个绿色圆圈 + 白色对勾，表示成功。"""
    size = 16
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#639922"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(0, 0, size, size)
    p.setBrush(Qt.PenStyle.NoBrush)
    pen = QPen(QColor("#ffffff"))
    pen.setWidth(2)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.drawLine(4, 8, 7, 11)
    p.drawLine(7, 11, 12, 5)
    p.end()
    label = QLabel()
    label.setPixmap(pm)
    return label


def _fmt_dur(sec: float) -> str:
    if not sec:
        return ""
    sec = int(round(sec))
    if sec < 60:
        return f"{sec}秒"
    m = sec // 60
    s = sec % 60
    if m < 60:
        return f"{m}分{s}秒"
    h = m // 60
    return f"{h}时{m % 60}分"


def _fmt_bytes(b: int) -> str:
    if not b:
        return "0B"
    value = float(b)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.2f}{unit}" if unit != "B" else f"{int(value)}{unit}"
        value /= 1024
    return f"{value:.2f}PB"


def _disk_info(path: str):
    """返回 (卷名, 容量文本)。容量取不到时返回空字符串。"""
    p = Path(path)
    parts = p.parts
    vol = parts[1] if len(parts) >= 2 and parts[1] else (parts[0] if parts else str(path))
    cap = ""
    try:
        total = shutil.disk_usage(p).total
        cap = _fmt_bytes(total)
    except (OSError, PermissionError):
        cap = ""
    return vol, cap


def _shorten(text: str, n: int = 48) -> str:
    text = str(text)
    return text if len(text) <= n else "…" + text[-(n - 1):]


# ---------- 单任务卡片 ----------
class _JobCard(QWidget):
    """一个任务的卡片：可点击头部展开 / 折叠，展开后显示目标盘表格。"""

    def __init__(self, job: CardJob) -> None:
        super().__init__()
        self.job = job
        self.expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QWidget()
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.setStyleSheet(
            "QWidget#hdr{background:#f9fafb; border:1px solid #d1d5db; "
            "border-radius:8px; padding:8px 10px;}"
        )
        self.header.setObjectName("hdr")
        self.header.installEventFilter(self)
        self._build_header()
        layout.addWidget(self.header)

        self.body = QWidget()
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setSpacing(0)
        self._build_body()
        layout.addWidget(self.body)
        self.body.setVisible(False)

    # ---- 头部 ----
    def _build_header(self) -> None:
        h = QHBoxLayout(self.header)
        h.setContentsMargins(10, 10, 10, 10)
        h.setSpacing(12)

        h.addWidget(_colored_box("#85B7EB", 40, 8))

        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        name = QLabel(self.job.label)
        name.setStyleSheet("font-weight:600; font-size:14px; color:#111827;")
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.check = _check_icon()
        self.status_text = QLabel()
        status_row.addWidget(self.check)
        status_row.addWidget(self.status_text)
        files = QLabel(f"{len(self.job.items)} 个文件")
        files.setStyleSheet("color:#9ca3af; font-size:12px;")
        col.addWidget(name)
        col.addLayout(status_row)
        col.addWidget(files)
        h.addLayout(col, 1)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(4)
        self.time_label = QLabel(self.job.finished_at or "")
        self.time_label.setStyleSheet("color:#9ca3af; font-size:12px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        icons = QHBoxLayout()
        icons.setSpacing(6)
        icons.addWidget(_colored_box("#b4b2a9", 20, 4))
        more = QLabel("⋯")
        more.setStyleSheet("color:#9ca3af; font-size:16px;")
        icons.addWidget(more)
        icons.addStretch(1)
        right.addWidget(self.time_label)
        right.addLayout(icons)
        h.addLayout(right)

        self._apply_status()

    def _apply_status(self) -> None:
        if self.job.status == ItemStatus.VERIFIED:
            dur = _fmt_dur(self.job.duration_seconds)
            self.status_text.setText(f"任务已完成（{dur}）")
            self.status_text.setStyleSheet("color:#16a34a; font-weight:600; font-size:13px;")
        elif self.job.status == ItemStatus.FAILED:
            self.status_text.setText("任务失败")
            self.status_text.setStyleSheet("color:#dc2626; font-weight:600; font-size:13px;")
        else:
            self.status_text.setText("待转卡")
            self.status_text.setStyleSheet("color:#6b7280; font-weight:600; font-size:13px;")

    def set_progress(self, percent: int) -> None:
        self.status_text.setText(f"转卡中 {percent}%")
        self.status_text.setStyleSheet("color:#6b7280; font-weight:600; font-size:13px;")

    # ---- 展开内容：目标盘表格 ----
    def _build_body(self) -> None:
        job = self.job
        n = len(job.dest_roots)
        table = QTableWidget(max(n, 1), 5)
        table.setHorizontalHeaderLabels(
            ["目标盘信息", "拷贝容量", "目标路径", "拷贝", "校验"]
        )
        table.setEditTriggers(table.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.setColumnWidth(0, 150)
        table.setColumnWidth(1, 100)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setShowGrid(False)
        table.setStyleSheet(
            "QTableWidget{border:1px solid #e5e7eb; border-radius:8px; "
            "background:#fff;} "
            "QHeaderView::section{background:#f3f4f6; color:#6b7280; "
            "border:none; padding:6px 8px; font-size:12px;} "
            "QTableWidget::item{padding:8px; border-bottom:1px solid #f3f4f6;}"
        )

        for di in range(max(n, 1)):
            if di < n:
                self._fill_row(table, di, job)
            else:
                table.setItem(di, 0, QTableWidgetItem("（无目标）"))

        self.body_layout.addWidget(table)

    @staticmethod
    def _fill_row(table: QTableWidget, di: int, job: CardJob) -> None:
        root = job.dest_roots[di]
        vol, cap = _disk_info(root)

        # 目标盘信息
        info = QWidget()
        il = QHBoxLayout(info)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(8)
        il.addWidget(_colored_box("#85B7EB" if di == 0 else "#e5e5e5", 28, 4))
        vcol = QVBoxLayout()
        vcol.setContentsMargins(0, 0, 0, 0)
        vcol.setSpacing(1)
        vcol.addWidget(_label(vol, "font-weight:600; font-size:13px; color:#111827;"))
        vcol.addWidget(_label(cap, "color:#9ca3af; font-size:11px;"))
        il.addLayout(vcol)
        il.addStretch(1)
        table.setCellWidget(di, 0, info)

        # 拷贝容量
        table.setItem(di, 1, _item(_fmt_bytes(job.total_bytes)))

        # 目标路径
        path_item = _item(_shorten(root))
        path_item.setToolTip(root)
        table.setItem(di, 2, path_item)

        # 拷贝
        copy_at = job.copy_finished_at[di] if di < len(job.copy_finished_at) else ""
        if copy_at:
            dur = _fmt_dur(job.copy_durations[di] if di < len(job.copy_durations) else 0)
            table.setItem(di, 3, _item(f"已完成\n{copy_at}（{dur}）", "#16a34a"))
        else:
            table.setItem(di, 3, _item("待拷贝", "#9ca3af"))

        # 校验
        if not job.verify_after_copy:
            table.setItem(di, 4, _item("未校验", "#9ca3af"))
        else:
            v_at = job.verify_finished_at[di] if di < len(job.verify_finished_at) else ""
            if v_at:
                dur = _fmt_dur(
                    job.verify_durations[di] if di < len(job.verify_durations) else 0
                )
                table.setItem(di, 4, _item(f"已完成（{job.checksum_algorithm}）\n{v_at}（{dur}）", "#16a34a"))
            else:
                table.setItem(di, 4, _item("待校验", "#9ca3af"))

    # ---- 交互 ----
    def eventFilter(self, obj, event) -> bool:
        if obj is self.header and event.type() == QEvent.Type.MouseButtonPress:
            self.toggle()
            return True
        return super().eventFilter(obj, event)

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.body.setVisible(self.expanded)


def _label(text: str, style: str) -> QLabel:
    w = QLabel(text)
    w.setStyleSheet(style)
    return w


def _item(text: str, color: Optional[str] = None) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    if color:
        it.setForeground(QColor(color))
    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return it


# ---------- 详情区主控件 ----------
class DetailView(QWidget):
    report_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 顶部标题 + 统计 + 报告按钮
        self.title = QLabel("源盘")
        self.title.setStyleSheet("font-weight:600; font-size:16px; color:#111827;")
        layout.addWidget(self.title)

        self.stats = QLabel()
        self.stats.setStyleSheet("color:#6b7280; font-size:12px;")
        self.report_btn = QPushButton("创建报告")
        self.report_btn.clicked.connect(self.report_requested.emit)
        top_row = QHBoxLayout()
        top_row.addWidget(self.stats)
        top_row.addStretch(1)
        top_row.addWidget(self.report_btn)
        layout.addLayout(top_row)

        # 空状态（无选中任务时显示）
        self.empty = QFrame()
        self.empty.setStyleSheet(
            "QFrame#empty{border:1px dashed #cbd5e1; border-radius:12px; "
            "background:#fff;}"
        )
        self.empty.setObjectName("empty")
        el = QVBoxLayout(self.empty)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(10)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus = QLabel("+")
        plus.setStyleSheet("color:#16a34a; font-size:28px; font-weight:300;")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        add_title = QLabel("添加源盘")
        add_title.setStyleSheet("color:#16a34a; font-weight:600; font-size:14px;")
        add_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint = QLabel("未发现源盘，从 Finder 拖拽到这里或点击左侧“添加源盘”按钮进行添加")
        hint.setStyleSheet("color:#9ca3af; font-size:12px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        el.addWidget(plus)
        el.addWidget(add_title)
        el.addWidget(hint)
        self.empty.setFixedHeight(150)
        layout.addWidget(self.empty)

        # 任务卡片滚动区
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
        self.status.setStyleSheet("color:#9ca3af; font-size:12px;")
        layout.addWidget(self.status)

        self.job_card: Optional[_JobCard] = None

    # ---------- 展示 ----------
    def show_job(self, job: CardJob | None, jobs: Optional[List[CardJob]] = None) -> None:
        jobs = jobs if jobs is not None else ([job] if job else [])
        self._update_stats(jobs)

        if job is None:
            self.empty.setVisible(True)
            self._clear_card()
            self.status.setText("未选择任务")
            return

        self.empty.setVisible(False)
        self._clear_card()
        card = _JobCard(job)
        self.container_layout.insertWidget(self.container_layout.count() - 1, card)
        self.job_card = card
        copied = sum(1 for j in jobs if j.copy_finished_at and all(j.copy_finished_at))
        self.status.setText(
            f"任务：{job.label} · {len(job.dest_roots)} 个目标 · "
            f"{len(job.items)} 个文件"
        )

    def _update_stats(self, jobs: List[CardJob]) -> None:
        total = len(jobs)
        copied = sum(
            1 for j in jobs if j.copy_finished_at and all(j.copy_finished_at)
        )
        verified = sum(
            1
            for j in jobs
            if (not j.verify_after_copy)
            or (j.verify_finished_at and all(j.verify_finished_at))
        )
        self.stats.setText(
            f"任务：{total}    拷贝完成：{copied}    校验完成：{verified}"
        )

    def update_progress(self, item, percent: int) -> None:
        if self.job_card is not None:
            self.job_card.set_progress(percent)

    def _clear_card(self) -> None:
        if self.job_card is not None:
            self.job_card.deleteLater()
            self.job_card = None
