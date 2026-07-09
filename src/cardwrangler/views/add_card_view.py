"""添加存储卡对话框：一个源（存储卡）+ 多个目标（转卡目录）。

目标框数量由设置里的「默认目标数量」决定；用户可点「+ 添加目标」增加，
点每行末尾的「✕」删除（至少保留一个）。允许部分目标留空，但必须至少有一个。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AddCardDialog(QDialog):
    """让用户一次性看清并填好「源」与若干「目标」，确认前可任意增删修改。"""

    def __init__(
        self,
        parent=None,
        default_dest: str = "",
        default_target_count: int = 1,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加存储卡")
        self.resize(640, 320)
        self.source = ""
        self.targets: list[str] = []
        self._targets: list[tuple[QWidget, QLineEdit]] = []
        self._build_ui(default_dest, default_target_count)

    def _build_ui(self, default_dest: str, default_target_count: int) -> None:
        layout = QVBoxLayout(self)

        # 源（单个）
        form = QFormLayout()
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("选择存储卡所在目录（源）")
        form.addRow("源（存储卡）", self._with_browse(self.source_edit, "选择存储卡目录"))
        layout.addLayout(form)

        # 目标（多个）
        layout.addWidget(QLabel("目标目录（可添加多个；至少填一个，其余可留空）"))
        self.targets_container = QWidget()
        self.targets_layout = QVBoxLayout(self.targets_container)
        self.targets_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.targets_container)

        self.add_target_btn = QPushButton("+ 添加目标")
        self.add_target_btn.clicked.connect(self._add_target_row)
        layout.addWidget(self.add_target_btn)

        # 预填：默认目标目录填到第一个框；其余按默认数量补空框
        n = max(1, default_target_count)
        for i in range(n):
            self._add_target_row(prefill=default_dest if (i == 0 and default_dest) else "")
        if not self._targets:
            self._add_target_row()

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("添加")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---------- 目标行管理 ----------
    def _add_target_row(self, prefill: str = "") -> None:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        line = QLineEdit()
        line.setPlaceholderText("选择转卡目标目录")
        if prefill:
            line.setText(prefill)
        browse = QPushButton("浏览…")
        browse.clicked.connect(lambda: self._browse(line, "选择目标目录"))
        delete = QPushButton("✕")
        delete.setFixedWidth(30)
        delete.clicked.connect(lambda: self._remove_target_row(row))
        h.addWidget(line)
        h.addWidget(browse)
        h.addWidget(delete)
        self.targets_layout.addWidget(row)
        self._targets.append((row, line))
        self._update_delete_state()

    def _remove_target_row(self, row: QWidget) -> None:
        for i, (w, _line) in enumerate(self._targets):
            if w is row:
                self.targets_layout.removeWidget(w)
                w.deleteLater()
                self._targets.pop(i)
                break
        self._update_delete_state()

    def _update_delete_state(self) -> None:
        enabled = len(self._targets) > 1
        for w, _line in self._targets:
            h = w.layout()
            if h is not None and h.count() >= 3:
                del_btn = h.itemAt(2).widget()
                if del_btn is not None:
                    del_btn.setEnabled(enabled)

    # ---------- 通用 ----------
    def _with_browse(self, line: QLineEdit, caption: str) -> QWidget:
        row = QHBoxLayout()
        row.addWidget(line)
        btn = QPushButton("浏览…")
        btn.clicked.connect(lambda: self._browse(line, caption))
        row.addWidget(btn)
        box = QWidget()
        box.setLayout(row)
        return box

    def _browse(self, line: QLineEdit, caption: str) -> None:
        d = QFileDialog.getExistingDirectory(self, caption)
        if d:
            line.setText(d)

    def _on_accept(self) -> None:
        src = self.source_edit.text().strip()
        if not src:
            QMessageBox.warning(self, "提示", "请选择源目录。")
            return

        targets = []
        for _w, line in self._targets:
            t = line.text().strip()
            if t:
                targets.append(t)
        # 去重（保持顺序）
        seen = set()
        dedup = []
        for t in targets:
            if t not in seen:
                seen.add(t)
                dedup.append(t)
        targets = dedup

        if not targets:
            QMessageBox.warning(self, "提示", "请至少填写一个目标目录。")
            return
        if src in targets:
            QMessageBox.warning(self, "提示", "源和目标不能是同一个目录。")
            return

        self.source = src
        self.targets = targets
        self.accept()
