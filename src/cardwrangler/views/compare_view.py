"""目录比对对话框：选择两个任意路径 → 递归逐文件校验和比对。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..models.compare_result import CompareEntry, CompareStatus, STATUS_LABELS
from .workers import CompareWorker

# 状态对应的行底色（浅色主题下清晰可读）
ROW_COLORS = {
    CompareStatus.MATCH: QColor(220, 245, 220),       # 浅绿
    CompareStatus.MISMATCH: QColor(250, 220, 220),    # 浅红
    CompareStatus.MISSING_IN_B: QColor(250, 235, 210),  # 浅橙
    CompareStatus.EXTRA_IN_B: QColor(235, 225, 250),  # 浅紫
}

_HEADERS = ["相对路径", "结果", "大小 A", "大小 B", "校验和 A", "校验和 B"]


class CompareDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("比对两个路径")
        self.resize(900, 560)
        self.worker: CompareWorker | None = None
        self._build_ui()

    # ---------- 界面 ----------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 路径选择
        form = QFormLayout()
        self.path_a = QLineEdit()
        self.path_a.setPlaceholderText("路径 A（源 / 基准）")
        self.path_b = QLineEdit()
        self.path_b.setPlaceholderText("路径 B（目标 / 副本）")
        form.addRow("路径 A", self._with_browse(self.path_a))
        form.addRow("路径 B", self._with_browse(self.path_b))
        layout.addLayout(form)

        # 算法 + 开始
        bar = QHBoxLayout()
        self.algorithm = QComboBox()
        self.algorithm.addItems(["sha256", "sha1", "md5", "sha512"])
        self.algorithm.setCurrentText("sha256")
        bar.addWidget(QLabel("校验算法"))
        bar.addWidget(self.algorithm)
        bar.addStretch(1)
        self.start_btn = QPushButton("开始比对")
        self.start_btn.clicked.connect(self._start)
        bar.addWidget(self.start_btn)
        layout.addLayout(bar)

        # 进度
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        # 汇总
        self.summary = QLabel("选择两个路径后点击「开始比对」")
        layout.addWidget(self.summary)

        # 结果区：两个独立表格（不一致常显，一致默认折叠）
        self.mismatch_box = QGroupBox("不一致 (0)")
        self.mismatch_box.setCheckable(False)
        self.mismatch_table = self._make_table()
        self.mismatch_box.setLayout(QVBoxLayout())
        self.mismatch_box.layout().addWidget(self.mismatch_table)
        layout.addWidget(self.mismatch_box)

        self.match_box = QGroupBox("一致 (0)")
        self.match_box.setCheckable(False)
        mb_layout = QVBoxLayout()
        self.match_toggle = QPushButton("▸ 展开一致结果")
        self.match_toggle.clicked.connect(self._toggle_match)
        mb_layout.addWidget(self.match_toggle)
        self.match_table = self._make_table()
        self.match_table.setVisible(False)   # 默认折叠：想看再点开
        mb_layout.addWidget(self.match_table)
        self.match_box.setLayout(mb_layout)
        layout.addWidget(self.match_box)

    def _make_table(self) -> QTableWidget:
        t = QTableWidget(0, 6)
        t.setHorizontalHeaderLabels(_HEADERS)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        t.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        t.setAlternatingRowColors(True)
        return t

    def _with_browse(self, line: QLineEdit) -> QWidget:
        row = QHBoxLayout()
        row.addWidget(line)
        btn = QPushButton("浏览…")
        btn.clicked.connect(lambda: self._browse(line))
        row.addWidget(btn)
        box = QWidget()
        box.setLayout(row)
        return box

    def _browse(self, line: QLineEdit) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择目录")
        if d:
            line.setText(d)

    # ---------- 比对 ----------
    def _start(self) -> None:
        a, b = self.path_a.text().strip(), self.path_b.text().strip()
        if not a or not b:
            self.summary.setText("请先选择路径 A 和路径 B。")
            return
        self.start_btn.setEnabled(False)
        self.mismatch_table.setRowCount(0)
        self.match_table.setRowCount(0)
        self.mismatch_box.setTitle("不一致 (0)")
        self.match_box.setTitle("一致 (0)")
        self.match_table.setVisible(False)
        self.match_toggle.setText("▸ 展开一致结果")   # 每次重新折叠一致表
        self.progress.setValue(0)
        self.summary.setText("比对中…")
        self.worker = CompareWorker(a, b, self.algorithm.currentText())
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.errored.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, entry: CompareEntry, percent: int) -> None:
        self.progress.setValue(percent)
        self._append_entry(entry)

    def _on_finished(self, results) -> None:
        self.start_btn.setEnabled(True)
        self.progress.setValue(100)
        self._show_summary(results)

    def _on_error(self, message: str) -> None:
        self.start_btn.setEnabled(True)
        self.summary.setText(f"比对出错：{message}")

    def _toggle_match(self) -> None:
        visible = not self.match_table.isVisible()
        self.match_table.setVisible(visible)
        self.match_toggle.setText("▾ 收起一致结果" if visible else "▸ 展开一致结果")

    # ---------- 渲染 ----------
    def _append_entry(self, entry: CompareEntry) -> None:
        is_match = entry.status == CompareStatus.MATCH
        table = self.match_table if is_match else self.mismatch_table
        row = table.rowCount()
        table.insertRow(row)

        values = [
            entry.rel_path,
            STATUS_LABELS[entry.status],
            self._fmt_size(entry.size_a),
            self._fmt_size(entry.size_b),
            entry.checksum_a or "—",
            entry.checksum_b or "—",
        ]
        color = ROW_COLORS.get(entry.status)
        for col, text in enumerate(values):
            item = QTableWidgetItem(str(text))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            if color is not None:
                item.setBackground(color)
            table.setItem(row, col, item)

        if is_match:
            self.match_box.setTitle(f"一致 ({table.rowCount()})")
        else:
            self.mismatch_box.setTitle(f"不一致 ({table.rowCount()})")

    def _show_summary(self, results) -> None:
        n = len(results)
        match = sum(1 for r in results if r.status == CompareStatus.MATCH)
        mismatch = sum(1 for r in results if r.status == CompareStatus.MISMATCH)
        missing = sum(1 for r in results if r.status == CompareStatus.MISSING_IN_B)
        extra = sum(1 for r in results if r.status == CompareStatus.EXTRA_IN_B)
        if mismatch == missing == extra == 0:
            self.summary.setText(
                f"✅ 完全一致：共 {n} 个文件，全部匹配。"
            )
        else:
            self.summary.setText(
                f"共 {n} 个文件 ｜ 一致 {match} ｜ 不一致 {mismatch} ｜ "
                f"A有B缺 {missing} ｜ B多出 {extra}"
            )

    @staticmethod
    def _fmt_size(n: int) -> str:
        if not n:
            return "—"
        return f"{n:,} B"
