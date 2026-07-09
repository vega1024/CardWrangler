"""添加存储卡对话框：同屏明确选择「源（存储卡）」与「目标（转卡目录）」。"""
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
    """让用户一次性看清并填好源与目标，确认前可任意修改。"""

    def __init__(self, parent=None, default_dest: str = "") -> None:
        super().__init__(parent)
        self.setWindowTitle("添加存储卡")
        self.resize(640, 200)
        self.source = ""
        self.dest = ""
        self._build_ui(default_dest)

    def _build_ui(self, default_dest: str) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("选择存储卡所在目录（源）")
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("选择素材转存到的目录（目标）")
        if default_dest:
            self.dest_edit.setText(default_dest)
        form.addRow("源（存储卡）", self._with_browse(self.source_edit, "选择存储卡目录"))
        form.addRow("目标（转卡到）", self._with_browse(self.dest_edit, "选择目标目录"))
        layout.addLayout(form)

        layout.addWidget(
            QLabel("确认无误后点「添加」；任一路径选错了，可随时改完再添加。")
        )

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("添加")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        dst = self.dest_edit.text().strip()
        if not src or not dst:
            QMessageBox.warning(self, "提示", "请同时选择源目录和目标目录。")
            return
        if src == dst:
            QMessageBox.warning(self, "提示", "源和目标不能是同一个目录。")
            return
        self.source = src
        self.dest = dst
        self.accept()
