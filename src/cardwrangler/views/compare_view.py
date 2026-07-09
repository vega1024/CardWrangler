"""目录比对对话框：选择两个任意路径 → 递归逐文件校验和比对。"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
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

        # 结果树：两个分组（不一致默认展开，一致默认折叠）
        self.tree = QTreeWidget()
        self.tree.setColumnCount(6)
        self.tree.setHeaderLabels(
            ["相对路径", "结果", "大小 A", "大小 B", "校验和 A", "校验和 B"]
        )
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setExpandsOnDoubleClick(True)
        layout.addWidget(self.tree)

        self.g_mismatch = QTreeWidgetItem(["不一致 (0)", "", "", "", "", ""])
        self.g_match = QTreeWidgetItem(["一致 (0)", "", "", "", "", ""])
        self.tree.addTopLevelItem(self.g_mismatch)
        self.tree.addTopLevelItem(self.g_match)
        self.g_mismatch.setExpanded(True)   # 默认展开：先看问题
        self.g_match.setExpanded(False)     # 默认折叠：一致的想看再点开

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
        # 清空上一次的分组内容，但保留分组节点与展开状态
        self.g_mismatch.takeChildren()
        self.g_match.takeChildren()
        self.g_mismatch.setText(0, "不一致 (0)")
        self.g_match.setText(0, "一致 (0)")
        self.g_mismatch.setExpanded(True)
        self.g_match.setExpanded(False)
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

    # ---------- 渲染 ----------
    def _append_entry(self, entry: CompareEntry) -> None:
        is_match = entry.status == CompareStatus.MATCH
        group = self.g_match if is_match else self.g_mismatch
        child = QTreeWidgetItem(
            [
                entry.rel_path,
                STATUS_LABELS[entry.status],
                self._fmt_size(entry.size_a),
                self._fmt_size(entry.size_b),
                entry.checksum_a or "—",
                entry.checksum_b or "—",
            ]
        )
        child.setFlags(child.flags() & ~Qt.ItemIsEditable)
        color = ROW_COLORS.get(entry.status)
        if color is not None:
            for c in range(child.columnCount()):
                child.setBackground(c, color)
        group.addChild(child)
        # 刷新分组计数
        label = "一致" if is_match else "不一致"
        group.setText(0, f"{label} ({group.childCount()})")

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
