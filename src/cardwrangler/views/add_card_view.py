"""添加源盘向导：选源盘 -> 预览（后缀统计）-> 选目标盘 -> 选校验方式 -> 开始拷贝。

仅用于「添加源盘」按钮。不区分主/关联素材，统计只按文件后缀聚合。
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)


def _fmt_bytes(b: int) -> str:
    if not b:
        return "0B"
    v = float(b)
    for u in ("B", "KB", "MB", "GB", "TB"):
        if v < 1024:
            return f"{v:.2f}{u}" if u != "B" else f"{int(v)}{u}"
        v /= 1024
    return f"{v:.2f}PB"


def _disk_info(path: str):
    p = Path(path)
    parts = p.parts
    vol = parts[1] if len(parts) >= 2 and parts[1] else (parts[0] if parts else str(path))
    cap = free = ""
    try:
        du = shutil.disk_usage(p)
        cap = _fmt_bytes(du.total)
        free = _fmt_bytes(du.free)
    except (OSError, PermissionError):
        pass
    return vol, cap, free


class AddCardDialog(QDialog):
    def __init__(
        self,
        parent=None,
        default_dest: str = "",
        default_target_count: int = 1,
        default_algorithm: str = "sha256",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加源盘")
        self.resize(680, 600)
        self.source = ""
        self.label = ""
        self.targets: List[str] = []
        self.algorithm = default_algorithm
        self.verify = True
        self._default_dest = default_dest
        self._default_algo = default_algorithm
        self._total_bytes = 0
        self._target_rows: List[Tuple[QWidget, QLineEdit, QLabel, QCheckBox]] = []
        self._algo_buttons: List[Tuple[QRadioButton, str]] = []
        self._build_ui(default_dest, default_target_count, default_algorithm)

    # ---------- 构建 ----------
    def _build_ui(self, default_dest, default_target_count, default_algorithm) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # 源盘区
        src_box = QGroupBox("源盘")
        sl = QVBoxLayout(src_box)
        top = QHBoxLayout()
        top.addWidget(QLabel("选择存储卡（源）目录："))
        top.addStretch(1)
        pick = QPushButton("选择源盘…")
        pick.clicked.connect(self._pick_source)
        top.addWidget(pick)
        sl.addLayout(top)

        self.src_hint = QLabel("尚未选择源盘。")
        self.src_hint.setStyleSheet("color:#9ca3af;")
        sl.addWidget(self.src_hint)

        self.src_info = QWidget()
        self.src_info.setVisible(False)
        sil = QVBoxLayout(self.src_info)
        sil.setContentsMargins(0, 0, 0, 0)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("名称："))
        self.src_name = QLineEdit()
        name_row.addWidget(self.src_name, 1)
        sil.addLayout(name_row)
        self.src_stat = QLabel()
        self.src_stat.setStyleSheet("color:#374151; font-weight:600;")
        sil.addWidget(self.src_stat)
        self.src_ext = QLabel()
        self.src_ext.setStyleSheet("color:#6b7280; font-size:12px;")
        self.src_ext.setWordWrap(True)
        sil.addWidget(self.src_ext)
        view_btn = QPushButton("查看文件")
        view_btn.setFixedWidth(90)
        view_btn.clicked.connect(self._toggle_files)
        sil.addWidget(view_btn)
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(140)
        self.files_list.setVisible(False)
        sil.addWidget(self.files_list)
        sl.addWidget(self.src_info)
        root.addWidget(src_box)

        arrow = QLabel("↓")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setStyleSheet("color:#9ca3af; font-size:18px;")
        root.addWidget(arrow)

        # 目标盘区
        dst_box = QGroupBox("目标盘")
        dl = QVBoxLayout(dst_box)
        self.dst_container = QWidget()
        self.dst_layout = QVBoxLayout(self.dst_container)
        self.dst_layout.setContentsMargins(0, 0, 0, 0)
        self.dst_layout.setSpacing(6)
        dl.addWidget(self.dst_container)
        add_dst = QPushButton("+ 添加目标…")
        add_dst.clicked.connect(lambda: self._add_target_row())
        dl.addWidget(add_dst)
        for _ in range(max(1, default_target_count)):
            self._add_target_row()
        if not self._target_rows:
            self._add_target_row()
        root.addWidget(dst_box)

        # 校验方式（横向单选条，对齐参考截图）
        algo_row = QHBoxLayout()
        algo_row.setSpacing(12)
        algo_row.addWidget(QLabel("校验方式"))
        self._verify_group = QButtonGroup(self)
        for label, algo in [
            ("MD5（较慢，推荐）", "md5"),
            ("SHA1（较慢）", "sha1"),
            ("SHA256（较慢）", "sha256"),
            ("不校验，只比较尺寸（不推荐）", ""),
        ]:
            rb = QRadioButton(label)
            self._verify_group.addButton(rb)
            self._algo_buttons.append((rb, algo))
            algo_row.addWidget(rb)
            if algo == default_algorithm or (
                algo == "" and default_algorithm not in ("md5", "sha1", "sha256")
            ):
                rb.setChecked(True)
        algo_row.addStretch(1)
        root.addLayout(algo_row)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        start = QPushButton("开始拷贝")
        start.setStyleSheet(
            "QPushButton{background:#16a34a; color:#fff; font-weight:600; "
            "padding:6px 16px; border-radius:6px;} "
            "QPushButton:hover{background:#15803d;}"
        )
        start.clicked.connect(self._on_accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(start)
        root.addLayout(btn_row)

    # ---------- 源盘 ----------
    def _pick_source(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择源盘目录")
        if d:
            self._on_source_chosen(d)

    def _on_source_chosen(self, path: str) -> None:
        p = Path(path)
        total = 0
        total_bytes = 0
        ext: dict[str, Tuple[int, int]] = {}
        files: List[str] = []
        if p.exists():
            for f in sorted(p.rglob("*")):
                if f.is_file():
                    total += 1
                    sz = f.stat().st_size
                    total_bytes += sz
                    e = f.suffix.lower() or "(无后缀)"
                    c, b = ext.get(e, (0, 0))
                    ext[e] = (c + 1, b + sz)
                    if len(files) < 500:
                        files.append(str(f.relative_to(p)))
        self._total_bytes = total_bytes
        self.source = str(p)
        self.label = p.name or str(p)
        self.src_hint.setVisible(False)
        self.src_info.setVisible(True)
        self.src_name.setText(self.label)
        self.src_stat.setText(f"{total} 个文件 · {_fmt_bytes(total_bytes)}")
        self.src_ext.setText(
            "后缀统计：" + (", ".join(f"{e} ×{c}" for e, (c, b) in sorted(ext.items())) or "—")
        )
        self.files_list.clear()
        self.files_list.addItems(files)

        name = p.name or "card"
        prefill = f"{self._default_dest}/{name}" if self._default_dest else ""
        if self._target_rows and not self._target_rows[0][1].text().strip():
            self._target_rows[0][1].setText(prefill)
        for _w, edit, disk, _c in self._target_rows:
            self._refresh_disk(disk, edit.text())

    def _toggle_files(self) -> None:
        self.files_list.setVisible(not self.files_list.isVisible())

    # ---------- 目标盘 ----------
    def _add_target_row(self, prefill: str = "") -> None:
        row = QWidget()
        v = QVBoxLayout(row)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit()
        edit.setPlaceholderText("选择转卡目标目录")
        if prefill:
            edit.setText(prefill)
        browse = QPushButton("浏览…")
        browse.clicked.connect(lambda: self._browse(edit))
        chk = QCheckBox("启用")
        chk.setChecked(True)
        del_btn = QPushButton("✕")
        del_btn.setFixedWidth(28)
        del_btn.setStyleSheet(
            "QPushButton{border:none; color:#dc2626; background:transparent;} "
            "QPushButton:hover{color:#b91c1c;}"
        )
        del_btn.clicked.connect(lambda: self._remove_target_row(row))
        h.addWidget(edit, 1)
        h.addWidget(browse)
        h.addWidget(chk)
        h.addWidget(del_btn)
        v.addLayout(h)
        disk = QLabel()
        disk.setStyleSheet("color:#6b7280; font-size:12px;")
        v.addWidget(disk)
        edit.textChanged.connect(lambda _=0: self._refresh_disk(disk, edit.text()))
        self.dst_layout.addWidget(row)
        self._target_rows.append((row, edit, disk, chk))
        self._refresh_disk(disk, edit.text())

    def _browse(self, edit: QLineEdit) -> None:
        d = QFileDialog.getExistingDirectory(self, "选择目标目录")
        if d:
            edit.setText(d)

    def _refresh_disk(self, disk_label: QLabel, path: str) -> None:
        if not path:
            disk_label.setText("")
            return
        vol, cap, free = _disk_info(path)
        parts = [vol]
        if cap:
            parts.append(f"共 {cap}")
        if free:
            remain = ""
            try:
                if self._total_bytes:
                    rb_free = shutil.disk_usage(Path(path)).free - self._total_bytes
                    remain = f" · 拷贝后剩余 {_fmt_bytes(max(rb_free, 0))}"
            except (OSError, PermissionError):
                pass
            parts.append(f"可用 {free}{remain}")
        disk_label.setText(" · ".join(parts))

    def _remove_target_row(self, row: QWidget) -> None:
        for i, (w, _e, _d, _c) in enumerate(self._target_rows):
            if w is row:
                self.dst_layout.removeWidget(w)
                w.deleteLater()
                self._target_rows.pop(i)
                break

    # ---------- 确认 ----------
    def _on_accept(self) -> None:
        if not self.source:
            QMessageBox.warning(self, "提示", "请先选择源盘目录。")
            return
        targets: List[str] = []
        for _w, edit, _d, chk in self._target_rows:
            t = edit.text().strip()
            if t and chk.isChecked():
                targets.append(t)
        seen = set()
        dedup = [t for t in targets if not (t in seen or seen.add(t))]
        targets = dedup
        if not targets:
            QMessageBox.warning(self, "提示", "请至少启用并填写一个目标目录。")
            return
        if self.source in targets:
            QMessageBox.warning(self, "提示", "源目录不能当作目标目录。")
            return

        self.targets = targets
        self.label = self.src_name.text().strip() or self.label
        for btn, algo in self._algo_buttons:
            if btn.isChecked():
                if algo == "":
                    self.verify = False
                    self.algorithm = self._default_algo
                else:
                    self.verify = True
                    self.algorithm = algo
                break
        self.accept()
