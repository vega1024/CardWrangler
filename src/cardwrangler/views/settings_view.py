"""设置对话框：拷贝后校验开关、校验算法、默认目标目录。"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QFileDialog,
    QPushButton,
    QCheckBox,
)


class SettingsView(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.resize(420, 180)

        layout = QFormLayout(self)

        self.verify = QCheckBox("拷贝完成后做校验和比对")
        self.verify.setChecked(True)

        self.algorithm = QComboBox()
        self.algorithm.addItems(["sha256", "sha1", "md5", "sha512"])
        self.algorithm.setCurrentText("sha256")

        self.dest = QLineEdit()
        self.dest.setPlaceholderText("默认转卡目标目录（留空则每次手动选择）")
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._browse)

        layout.addRow(self.verify)
        layout.addRow("校验算法", self.algorithm)
        layout.addRow("默认目标", self.dest)
        layout.addRow("", browse)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择默认目标目录")
        if d:
            self.dest.setText(d)

    # 方便外部读取 / 写入
    def values(self) -> dict:
        return {
            "verify_after_copy": self.verify.isChecked(),
            "checksum_algorithm": self.algorithm.currentText(),
            "default_dest": self.dest.text(),
        }

    def set_values(self, v: dict) -> None:
        self.verify.setChecked(v.get("verify_after_copy", True))
        self.algorithm.setCurrentText(v.get("checksum_algorithm", "sha256"))
        self.dest.setText(v.get("default_dest", ""))
