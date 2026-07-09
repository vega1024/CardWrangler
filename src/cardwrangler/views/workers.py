"""后台工作线程：在子线程里跑转卡逻辑，避免界面卡死。

通过 Qt 的 Signal 把进度 / 完成事件抛回主线程更新 UI。
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ...models.card_job import CardJob
from ...models.item import Item
from ...services.offload_service import offload_item


class OffloadWorker(QThread):
    progress = Signal(object, int)   # (Item, percent)
    finished = Signal(object)        # (CardJob)
    errored = Signal(str)            # error message

    def __init__(self, job: CardJob) -> None:
        super().__init__()
        self.job = job

    def run(self) -> None:
        try:
            for item in self.job.items:
                offload_item(
                    item,
                    self.job.verify_after_copy,
                    self.job.checksum_algorithm,
                    on_progress=self._on_progress,
                )
            self.finished.emit(self.job)
        except Exception as exc:  # noqa: BLE001 - 顶层兜底，避免线程静默崩溃
            self.errored.emit(str(exc))

    def _on_progress(self, item: Item, percent: int) -> None:
        self.progress.emit(item, percent)
