"""视图模型（ViewModel）：连接 Services / Persistence 与 Views。

设计要点：
- **不依赖 PySide6 / Qt**，因此可以在没有图形界面的环境里直接单测。
- 通过内置的轻量 Signal 通知界面层「数据变了 / 进度更新 / 状态消息」。
- 界面层（views/）订阅这些 Signal，把变化映射到 Qt 控件上。
"""
from __future__ import annotations

from typing import Callable, List, Optional

from ..models.card_job import CardJob
from ..models.item import Item, ItemStatus
from ..persistence.repository import JobRepository
from ..services.offload_service import scan_source


class Signal:
    """极简信号实现（类似 Qt 的 pyqtSignal，但零依赖）。

    用法：
        sig = Signal()
        sig.connect(lambda x: print(x))
        sig.emit(42)
    """

    def __init__(self) -> None:
        self._slots: List[Callable] = []

    def connect(self, fn: Callable) -> None:
        if fn not in self._slots:
            self._slots.append(fn)

    def disconnect(self, fn: Callable) -> None:
        if fn in self._slots:
            self._slots.remove(fn)

    def emit(self, *args, **kwargs) -> None:
        for fn in list(self._slots):
            fn(*args, **kwargs)


class ContentViewModel:
    def __init__(self, repository: Optional[JobRepository] = None):
        self.repository = repository or JobRepository.default()
        self.jobs: List[CardJob] = self.repository.load()
        self.selected_job: Optional[CardJob] = None
        self.is_busy: bool = False

        # 信号
        self.jobs_changed = Signal()      # -> (List[CardJob])
        self.job_selected = Signal()      # -> (Optional[CardJob])
        self.progress = Signal()          # -> (Item, int)
        self.status_message = Signal()    # -> (str)

    # ---- 任务管理 ----
    def add_job(self, job: CardJob) -> None:
        scan_source(job)
        self.jobs.append(job)
        self._persist()
        self.jobs_changed.emit(self.jobs)
        self.status_message.emit(f"已添加任务：{job.label}（{len(job.items)} 个文件）")

    def remove_job(self, job: CardJob) -> None:
        self.jobs = [j for j in self.jobs if j.id != job.id]
        if self.selected_job and self.selected_job.id == job.id:
            self.selected_job = None
            self.job_selected.emit(None)
        self._persist()
        self.jobs_changed.emit(self.jobs)

    def select_job(self, job: Optional[CardJob]) -> None:
        self.selected_job = job
        self.job_selected.emit(job)

    def find_job(self, job_id: str) -> Optional[CardJob]:
        return self.repository.find(job_id)

    # ---- 进度（由工作线程回调）----
    def report_progress(self, item: Item, percent: int) -> None:
        self.progress.emit(item, percent)

    def mark_busy(self, busy: bool) -> None:
        self.is_busy = busy
        self.status_message.emit("转卡中…" if busy else "就绪")

    def finalize_job(self, job: CardJob) -> None:
        """转卡结束后保存并刷新。"""
        self._persist()
        self.jobs_changed.emit(self.jobs)
        ok = job.verified_count
        self.status_message.emit(f"完成：{ok}/{len(job.items)} 个文件校验通过")

    # ---- 示例数据（首次打开界面用）----
    def load_sample(self) -> None:
        if self.jobs:
            return
        job = CardJob.new("示例：A002_C001（CFast）", "/Volumes/CARD/A002_C001", "/Volumes/BACKUP/A002_C001")
        job.items = [
            Item(id=f"{job.id}:0", name="CLIPS/0001.MXF", source_path="", size=1_200_000_000),
            Item(id=f"{job.id}:1", name="CLIPS/0002.MXF", source_path="", size=980_000_000),
            Item(id=f"{job.id}:2", name="SIDE/0001.RDC", source_path="", size=640_000_000),
        ]
        self.jobs.append(job)
        self.jobs_changed.emit(self.jobs)

    # ---- 内部 ----
    def _persist(self) -> None:
        self.repository.save(self.jobs)
