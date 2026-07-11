"""后台工作线程：在子线程里跑转卡逻辑，避免界面卡死。

通过 Qt 的 Signal 把进度 / 完成事件抛回主线程更新 UI。
"""
from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from ..models.card_job import CardJob
from ..models.item import Item
from ..models.compare_result import CompareEntry
from ..services.offload_service import offload_job
from ..services.compare_service import compare_paths


class OffloadWorker(QThread):
    progress = Signal(object, int)   # (Item, percent)
    finished = Signal(object)        # (CardJob)
    errored = Signal(str)            # error message

    def __init__(self, job: CardJob) -> None:
        super().__init__()
        self.job = job

    def run(self) -> None:
        try:
            # 用 offload_job（而非手动循环 offload_item）：它在拷贝/校验后会把每个
            # Item 的「每目标」耗时与完成时间聚合到任务级字段，并设置 job.status /
            # finished_at / duration_seconds，供详情区目标盘表格与头部直接展示。
            offload_job(self.job, on_progress=self._on_progress)
            self.finished.emit(self.job)
        except Exception as exc:  # noqa: BLE001 - 顶层兜底，避免线程静默崩溃
            self.errored.emit(str(exc))

    def _on_progress(self, item: Item, percent: int) -> None:
        self.progress.emit(item, percent)


class CompareWorker(QThread):
    """后台比对两个路径，避免界面卡死。"""

    progress = Signal(object, int)   # (CompareEntry, percent)
    finished = Signal(list)          # (List[CompareEntry])
    errored = Signal(str)            # error message

    def __init__(self, path_a: str, path_b: str, algorithm: str) -> None:
        super().__init__()
        self.path_a = path_a
        self.path_b = path_b
        self.algorithm = algorithm

    def run(self) -> None:
        try:
            results = compare_paths(
                self.path_a,
                self.path_b,
                self.algorithm,
                on_progress=self._on_progress,
            )
            self.finished.emit(results)
        except Exception as exc:  # noqa: BLE001 - 顶层兜底，避免线程静默崩溃
            self.errored.emit(str(exc))

    def _on_progress(self, entry: CompareEntry, percent: int) -> None:
        self.progress.emit(entry, percent)
