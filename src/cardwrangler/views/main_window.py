"""主窗口：组合侧边栏 + 详情区，并把视图模型的变化映射到界面。"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QWidget,
)

from ..models.card_job import CardJob
from ..viewmodels.content_view_model import ContentViewModel
from .detail_view import DetailView
from .settings_view import SettingsView
from .sidebar_view import SidebarView
from .compare_view import CompareDialog
from .add_card_view import AddCardDialog
from .workers import OffloadWorker


class MainWindow(QMainWindow):
    def __init__(self, view_model: ContentViewModel) -> None:
        super().__init__()
        self.vm = view_model
        self.worker: OffloadWorker | None = None
        self.settings = QSettings("CardWrangler", "CardWrangler")

        self.setWindowTitle("CardWrangler")
        self.resize(1000, 680)

        self._build_ui()
        self._connect_vm()

        self.vm.load_sample()
        self._refresh_jobs()

    # ---------- 构建界面 ----------
    def _build_ui(self) -> None:
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        self.start_btn = QPushButton("▶ 开始转卡")
        self.start_btn.clicked.connect(self._start_offload)
        toolbar.addWidget(self.start_btn)

        spacer = QWidget()
        spacer.setFixedWidth(12)
        toolbar.addWidget(spacer)

        settings_action = toolbar.addAction("设置")
        settings_action.triggered.connect(self._open_settings)

        spacer2 = QWidget()
        spacer2.setFixedWidth(12)
        toolbar.addWidget(spacer2)

        compare_action = toolbar.addAction("比对路径")
        compare_action.triggered.connect(self._open_compare)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sidebar = SidebarView()
        self.detail = DetailView()
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        self.setCentralWidget(splitter)

    # ---------- 绑定视图模型 ----------
    def _connect_vm(self) -> None:
        self.vm.jobs_changed.connect(self._on_jobs_changed)
        self.vm.job_selected.connect(self._on_job_selected)
        self.vm.progress.connect(lambda item, pct: self.detail.update_progress(item, pct))
        self.vm.status_message.connect(self.statusBar().showMessage)

        self.sidebar.add_requested.connect(self._add_card)
        self.sidebar.job_selected.connect(self._on_sidebar_selected)
        self.sidebar.delete_requested.connect(self._remove_card)

    # ---------- 视图模型回调 ----------
    def _on_jobs_changed(self, jobs) -> None:
        self.sidebar.set_jobs(jobs)
        if self.vm.selected_job:
            self.detail.show_job(self.vm.selected_job)

    def _on_job_selected(self, job: CardJob | None) -> None:
        self.detail.show_job(job)

    def _on_sidebar_selected(self, job_id: str) -> None:
        job = self.vm.find_job(job_id)
        if job:
            self.vm.select_job(job)

    def _remove_card(self, job_id: str) -> None:
        job = self.vm.find_job(job_id)
        if job is None:
            return
        # 正在转卡的任务不允许删除，避免与后台线程竞争
        if self.vm.is_busy and self.vm.selected_job and self.vm.selected_job.id == job_id:
            QMessageBox.information(self, "提示", "该任务正在转卡中，请等待完成后再删除。")
            return
        reply = QMessageBox.question(
            self,
            "删除任务",
            f"确定删除「{job.label}」？该操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.vm.remove_job(job)

    def _refresh_jobs(self) -> None:
        self.sidebar.set_jobs(self.vm.jobs)

    # ---------- 交互 ----------
    def _add_card(self) -> None:
        default_dest = str(self.settings.value("default_dest", ""))
        try:
            default_count = int(self.settings.value("default_target_count", 1))
        except (TypeError, ValueError):
            default_count = 1
        dlg = AddCardDialog(
            self, default_dest=default_dest, default_target_count=default_count
        )
        if dlg.exec() != QDialog.Accepted:
            return

        source = dlg.source
        targets = dlg.targets
        label = source.rstrip("/").split("/")[-1] or "未命名卡"
        job = CardJob.new(label, source, targets)
        job.verify_after_copy = bool(self.settings.value("verify_after_copy", True, type=bool))
        job.checksum_algorithm = str(self.settings.value("checksum_algorithm", "sha256"))
        self.vm.add_job(job)
        self.vm.select_job(job)

    def _start_offload(self) -> None:
        job = self.vm.selected_job
        if job is None:
            QMessageBox.information(self, "提示", "请先在左侧选择一张存储卡。")
            return
        if self.vm.is_busy:
            return

        self.vm.mark_busy(True)
        self.worker = OffloadWorker(job)
        self.worker.progress.connect(lambda item, pct: self.vm.report_progress(item, pct))
        self.worker.finished.connect(self._on_offload_finished)
        self.worker.errored.connect(self._on_offload_error)
        self.worker.start()

    def _on_offload_finished(self, job: CardJob) -> None:
        self.vm.mark_busy(False)
        self.vm.finalize_job(job)
        self.detail.show_job(job)
        self.statusBar().showMessage(
            f"完成：{job.verified_count}/{len(job.items)} 个文件校验通过"
        )

    def _on_offload_error(self, message: str) -> None:
        self.vm.mark_busy(False)
        QMessageBox.critical(self, "转卡出错", message)

    def _open_settings(self) -> None:
        dlg = SettingsView(self)
        dlg.set_values(
            {
                "verify_after_copy": bool(self.settings.value("verify_after_copy", True, type=bool)),
                "checksum_algorithm": str(self.settings.value("checksum_algorithm", "sha256")),
                "default_dest": str(self.settings.value("default_dest", "")),
                "default_target_count": int(self.settings.value("default_target_count", 1)),
            }
        )
        if dlg.exec() == SettingsView.Accepted:
            v = dlg.values()
            self.settings.setValue("verify_after_copy", v["verify_after_copy"])
            self.settings.setValue("checksum_algorithm", v["checksum_algorithm"])
            self.settings.setValue("default_dest", v["default_dest"])
            self.settings.setValue("default_target_count", v["default_target_count"])

    def _open_compare(self) -> None:
        dlg = CompareDialog(self)
        dlg.exec()
